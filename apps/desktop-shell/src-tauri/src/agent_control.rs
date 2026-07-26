//! Detecção e controle do agent Windows (`assistant-hub-audio`).
//! Resolução de sessionId do agent: cmdline `--session` → último start gerenciado → desconhecida
//! (specs/020-issue-47-sessionid-align).

use crate::sidecar::{BinaryResolution, BinarySource};
use serde::Serialize;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::Child;
use sysinfo::System;

/// Nome do binário/processo do agent Windows, usado para casar na enumeração de processos.
const AGENT_PROCESS_NAMES: [&str; 2] = ["assistant-hub-audio", "assistant-hub-audio.exe"];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum ControlMode {
    /// O shell pode iniciar (parado) ou parar (handle) diretamente.
    Direct,
    /// Processo em execução fora do shell — só orientação manual.
    Guided,
}

/// Como `agent_session_id` foi resolvido (FR-005).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum AgentSessionSource {
    Cmdline,
    Managed,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentStatus {
    pub running: bool,
    pub control_mode: ControlMode,
    /// Comando exato e reproduzível para o operador rodar manualmente.
    pub guidance_command: String,
    pub last_error: Option<String>,
    /// Sessão resolvida do agent; None se desconhecida ou N/A.
    pub agent_session_id: Option<String>,
    pub agent_session_source: AgentSessionSource,
    /// 025 — caminho resolvido do binário (sidecar/config/PATH).
    pub binary_path: Option<String>,
    pub binary_source: BinarySource,
    pub agent_version: Option<String>,
    /// Processo em execução e (se gerenciado) child ainda vivo.
    pub healthy: bool,
}

/// Constrói o comando exato que o operador rodaria manualmente.
pub fn guidance_command(session_id: &str, profile_path: &str) -> String {
    format!("assistant-hub-audio run --session {session_id} --profile {profile_path}")
}

/// Extrai `--session <id>` ou `--session=<id>` da linha de comando (último vence).
pub fn parse_session_from_cmd(args: &[OsString]) -> Option<String> {
    let mut found: Option<String> = None;
    let mut i = 0;
    while i < args.len() {
        let arg = args[i].to_string_lossy();
        if arg == "--session" {
            if let Some(next) = args.get(i + 1) {
                let id = next.to_string_lossy().trim().to_string();
                if !id.is_empty() && !id.starts_with('-') {
                    found = Some(id);
                }
                i += 2;
                continue;
            }
        } else if let Some(rest) = arg.strip_prefix("--session=") {
            let id = rest.trim();
            if !id.is_empty() {
                found = Some(id.to_string());
            }
        }
        i += 1;
    }
    found
}

/// Prioridade: cmdline → managed (com handle) → unknown. Nunca inventa id.
pub fn resolve_agent_session(
    running: bool,
    cmdline_id: Option<&str>,
    last_managed_id: Option<&str>,
    has_managed_handle: bool,
) -> (Option<String>, AgentSessionSource) {
    if !running {
        return (None, AgentSessionSource::Unknown);
    }
    if let Some(id) = cmdline_id.map(str::trim).filter(|s| !s.is_empty()) {
        return (Some(id.to_string()), AgentSessionSource::Cmdline);
    }
    if has_managed_handle {
        if let Some(id) = last_managed_id.map(str::trim).filter(|s| !s.is_empty()) {
            return (Some(id.to_string()), AgentSessionSource::Managed);
        }
    }
    (None, AgentSessionSource::Unknown)
}

/// I1: parado → Direct; running+handle → Direct; running sem handle → Guided.
pub fn resolve_control_mode(running: bool, has_managed_handle: bool) -> ControlMode {
    if !running {
        ControlMode::Direct
    } else if has_managed_handle {
        ControlMode::Direct
    } else {
        ControlMode::Guided
    }
}

/// Detecta se o agent está rodando enumerando processos.
pub fn detect_running() -> bool {
    let mut system = System::new();
    system.refresh_processes(sysinfo::ProcessesToUpdate::All, true);
    system.processes().values().any(process_matches_agent)
}

/// Tenta obter `--session` da cmdline do primeiro processo agent com parse válido.
pub fn detect_agent_cmdline_session() -> Option<String> {
    let mut system = System::new();
    system.refresh_processes(sysinfo::ProcessesToUpdate::All, true);
    for process in system.processes().values() {
        if !process_matches_agent(process) {
            continue;
        }
        if let Some(id) = parse_session_from_cmd(process.cmd()) {
            return Some(id);
        }
    }
    None
}

/// Monta status completo a partir de sinais de runtime.
pub fn build_status(
    running: bool,
    has_managed_handle: bool,
    last_managed_session_id: Option<&str>,
    guidance_command: String,
    last_error: Option<String>,
    binary: &BinaryResolution,
    managed_child_alive: bool,
) -> AgentStatus {
    let cmdline_id = if running {
        detect_agent_cmdline_session()
    } else {
        None
    };
    let (agent_session_id, agent_session_source) = resolve_agent_session(
        running,
        cmdline_id.as_deref(),
        last_managed_session_id,
        has_managed_handle,
    );
    let healthy = if has_managed_handle {
        running && managed_child_alive
    } else {
        running
    };
    AgentStatus {
        running,
        control_mode: resolve_control_mode(running, has_managed_handle),
        guidance_command,
        last_error,
        agent_session_id,
        agent_session_source,
        binary_path: binary.path.as_ref().map(|p| p.display().to_string()),
        binary_source: binary.source,
        agent_version: binary.version.clone(),
        healthy,
    }
}

/// Encerra o agent gerenciado se houver handle (shutdown coordenado 025 / FR-006).
pub fn shutdown_managed(managed: &mut Option<ManagedAgentProcess>) {
    if let Some(mut process) = managed.take() {
        let _ = stop(&mut process);
    }
}

/// Child ainda em execução (try_wait None).
pub fn managed_is_alive(managed: &mut ManagedAgentProcess) -> bool {
    match managed.child.try_wait() {
        Ok(None) => true,
        _ => false,
    }
}

/// Display path for Command::new — falls back to bare name when missing.
pub fn command_program(binary: &BinaryResolution) -> PathBuf {
    binary
        .path
        .clone()
        .unwrap_or_else(|| PathBuf::from("assistant-hub-audio"))
}

fn process_matches_agent(process: &sysinfo::Process) -> bool {
    let name = process.name().to_string_lossy().to_lowercase();
    let exe_file_name = process
        .exe()
        .and_then(|p| p.file_name())
        .map(|n| n.to_string_lossy().to_lowercase());

    AGENT_PROCESS_NAMES.iter().any(|candidate| {
        let candidate = candidate.to_lowercase();
        name == candidate
            || (name.len() == 15 && candidate.starts_with(&name))
            || exe_file_name.as_deref() == Some(candidate.as_str())
    })
}

/// Handle de um processo do agent que o próprio shell iniciou.
#[derive(Debug)]
pub struct ManagedAgentProcess {
    child: Child,
}

#[derive(Debug)]
pub enum StartError {
    BinaryNotFound,
    AlreadyRunning,
    ExitedImmediately(Option<i32>),
    Os(String),
}

impl std::fmt::Display for StartError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StartError::BinaryNotFound => write!(f, "binário assistant-hub-audio não encontrado"),
            StartError::AlreadyRunning => write!(f, "o agent já está em execução"),
            StartError::ExitedImmediately(code) => {
                write!(
                    f,
                    "o processo encerrou imediatamente após iniciar (código {code:?})"
                )
            }
            StartError::Os(msg) => write!(f, "falha do sistema operacional ao iniciar: {msg}"),
        }
    }
}

impl std::error::Error for StartError {}

/// Inicia o agent diretamente. Não inicia se já houver processo agent rodando.
pub fn start(mut command: std::process::Command) -> Result<ManagedAgentProcess, StartError> {
    if detect_running() {
        return Err(StartError::AlreadyRunning);
    }

    let mut child = command.spawn().map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            StartError::BinaryNotFound
        } else {
            StartError::Os(e.to_string())
        }
    })?;

    std::thread::sleep(std::time::Duration::from_millis(50));
    if let Ok(Some(status)) = child.try_wait() {
        return Err(StartError::ExitedImmediately(status.code()));
    }

    Ok(ManagedAgentProcess { child })
}

/// Encerra um processo que o shell iniciou diretamente.
pub fn stop(managed: &mut ManagedAgentProcess) -> Result<(), StartError> {
    managed
        .child
        .kill()
        .map_err(|e| StartError::Os(e.to_string()))?;
    let _ = managed.child.wait();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    fn os(s: &str) -> OsString {
        OsString::from(s)
    }

    #[test]
    fn guidance_command_is_exact_and_reproducible() {
        let cmd = guidance_command("11111111-1111-1111-1111-111111111111", "perfil.yaml");
        assert_eq!(
            cmd,
            "assistant-hub-audio run --session 11111111-1111-1111-1111-111111111111 --profile perfil.yaml"
        );
    }

    #[test]
    fn parse_session_from_cmd_separated_form() {
        let args = vec![
            os("assistant-hub-audio"),
            os("run"),
            os("--session"),
            os("sess-a"),
            os("--profile"),
            os("p.yaml"),
        ];
        assert_eq!(parse_session_from_cmd(&args).as_deref(), Some("sess-a"));
    }

    #[test]
    fn parse_session_from_cmd_equals_form_and_last_wins() {
        let args = vec![
            os("assistant-hub-audio"),
            os("--session=first"),
            os("--session"),
            os("second"),
        ];
        assert_eq!(parse_session_from_cmd(&args).as_deref(), Some("second"));
    }

    #[test]
    fn parse_session_from_cmd_missing_returns_none() {
        let args = vec![os("assistant-hub-audio"), os("run"), os("--profile"), os("p.yaml")];
        assert_eq!(parse_session_from_cmd(&args), None);
    }

    #[test]
    fn resolve_agent_session_priority_cmdline_over_managed() {
        let (id, src) = resolve_agent_session(true, Some("from-cmd"), Some("from-managed"), true);
        assert_eq!(id.as_deref(), Some("from-cmd"));
        assert_eq!(src, AgentSessionSource::Cmdline);
    }

    #[test]
    fn resolve_agent_session_managed_when_no_cmdline() {
        let (id, src) = resolve_agent_session(true, None, Some("managed-id"), true);
        assert_eq!(id.as_deref(), Some("managed-id"));
        assert_eq!(src, AgentSessionSource::Managed);
    }

    #[test]
    fn resolve_agent_session_unknown_when_no_sources() {
        let (id, src) = resolve_agent_session(true, None, None, false);
        assert_eq!(id, None);
        assert_eq!(src, AgentSessionSource::Unknown);
    }

    #[test]
    fn resolve_agent_session_not_running_clears_id() {
        let (id, src) = resolve_agent_session(false, Some("x"), Some("y"), true);
        assert_eq!(id, None);
        assert_eq!(src, AgentSessionSource::Unknown);
    }

    #[test]
    fn resolve_control_mode_stopped_is_direct_i1() {
        assert_eq!(resolve_control_mode(false, false), ControlMode::Direct);
        assert_eq!(resolve_control_mode(false, true), ControlMode::Direct);
    }

    #[test]
    fn resolve_control_mode_running_external_is_guided() {
        assert_eq!(resolve_control_mode(true, false), ControlMode::Guided);
        assert_eq!(resolve_control_mode(true, true), ControlMode::Direct);
    }

    #[test]
    fn start_with_missing_binary_reports_specific_error() {
        let command = Command::new("um-binario-que-nao-existe-de-verdade-12345");
        let result = start(command);
        match result {
            Err(StartError::BinaryNotFound) => {}
            other => panic!("esperado StartError::BinaryNotFound, obtido {other:?}"),
        }
    }

    #[test]
    fn start_with_process_that_exits_immediately_reports_specific_error() {
        let mut command = Command::new("true");
        command.args::<[&str; 0], &str>([]);
        let result = start(command);
        match result {
            Err(StartError::ExitedImmediately(_)) => {}
            other => panic!("esperado StartError::ExitedImmediately, obtido {other:?}"),
        }
    }

    #[test]
    fn start_and_stop_a_fake_long_running_process_direct_control() {
        let mut command = Command::new("sleep");
        command.arg("5");
        let mut managed = start(command).expect("start deve funcionar com processo fake");
        assert!(stop(&mut managed).is_ok());
    }

    #[test]
    fn shutdown_managed_kills_child_and_clears_slot() {
        let mut command = Command::new("sleep");
        command.arg("30");
        let managed = start(command).expect("start sleep");
        let mut slot = Some(managed);
        shutdown_managed(&mut slot);
        assert!(slot.is_none());
    }

    #[test]
    fn build_status_includes_binary_resolution_fields() {
        let binary = BinaryResolution {
            path: Some(PathBuf::from("/tmp/assistant-hub-audio")),
            source: BinarySource::Sidecar,
            version: Some("0.2.0".into()),
        };
        let status = build_status(
            true,
            true,
            Some("sess-1"),
            guidance_command("sess-1", "p.yaml"),
            None,
            &binary,
            true,
        );
        assert_eq!(status.binary_source, BinarySource::Sidecar);
        assert_eq!(status.agent_version.as_deref(), Some("0.2.0"));
        assert!(status.healthy);
        assert_eq!(
            status.binary_path.as_deref(),
            Some("/tmp/assistant-hub-audio")
        );
    }
}
