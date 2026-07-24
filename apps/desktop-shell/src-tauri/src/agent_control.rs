//! Detecção e controle do agent Windows (`assistant-hub-audio`) — US3 (FR-006/FR-007/FR-008).
//! O agent não expõe nenhuma API de health/status hoje (research.md, Decisão 5); a detecção é
//! feita por enumeração de processo (`sysinfo`), casando pelo nome do executável/linha de
//! comando conhecidos.

use serde::Serialize;
use std::process::Child;
use sysinfo::System;

/// Nome do binário/processo do agent Windows, usado para casar na enumeração de processos.
/// Em Windows real o executável é `assistant-hub-audio.exe`; mantemos os dois nomes possíveis
/// (com e sem extensão) para tolerar diferenças de empacotamento.
const AGENT_PROCESS_NAMES: [&str; 2] = ["assistant-hub-audio", "assistant-hub-audio.exe"];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum ControlMode {
    /// O shell iniciou o processo e detém o handle — pode parar diretamente.
    Direct,
    /// O processo foi encontrado rodando fora do shell (ou o handle não está disponível) —
    /// só é possível orientar o operador.
    Guided,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentStatus {
    pub running: bool,
    pub control_mode: ControlMode,
    /// Comando exato e reproduzível para o operador rodar manualmente (FR-007), sempre
    /// preenchido — mesmo quando `control_mode = Direct`, serve como fallback textual.
    pub guidance_command: String,
    pub last_error: Option<String>,
}

/// Constrói o comando exato que o operador rodaria manualmente (FR-007), no mesmo formato
/// documentado em AGENTS.md § "Comandos Windows".
pub fn guidance_command(session_id: &str, profile_path: &str) -> String {
    format!("assistant-hub-audio run --session {session_id} --profile {profile_path}")
}

/// Detecta se o agent está rodando enumerando processos do sistema operacional — único sinal
/// disponível hoje, já que o agent não expõe status/PID/health (ver research.md, Decisão 5).
/// Não requer que o shell tenha iniciado o processo.
///
/// Checa tanto `Process::name()` quanto o nome de arquivo de `Process::exe()`: no Linux, o
/// `comm` do kernel (usado por `name()`) trunca em 15 caracteres (`TASK_COMM_LEN`), cortando
/// "assistant-hub-audio" para "assistant-hub-a" — achado real ao testar a detecção neste WSL
/// (o Windows, alvo de produção, não tem essa limitação). Checar `exe()` também evita esse
/// falso negativo em qualquer plataforma.
pub fn detect_running() -> bool {
    let mut system = System::new();
    system.refresh_processes(sysinfo::ProcessesToUpdate::All, true);
    system.processes().values().any(process_matches_agent)
}

fn process_matches_agent(process: &sysinfo::Process) -> bool {
    let name = process.name().to_string_lossy().to_lowercase();
    let exe_file_name = process
        .exe()
        .and_then(|p| p.file_name())
        .map(|n| n.to_string_lossy().to_lowercase());

    AGENT_PROCESS_NAMES.iter().any(|candidate| {
        let candidate = candidate.to_lowercase();
        // Igual, ou "name" é exatamente o comm truncado do Linux (15 chars, TASK_COMM_LEN-1)
        // e é prefixo de "candidate" (evita falso positivo com nomes curtos não relacionados),
        // ou o nome de arquivo do executável bate exatamente (não sofre truncamento).
        name == candidate
            || (name.len() == 15 && candidate.starts_with(&name))
            || exe_file_name.as_deref() == Some(candidate.as_str())
    })
}

/// Handle de um processo do agent que o próprio shell iniciou — permite parada direta
/// (`ControlMode::Direct`). Nenhuma instância de PyAudio/WASAPI é tocada aqui; o shell só
/// gerencia o processo do agent como um todo (isolamento por endpoint continua no agent,
/// ADR-0007).
#[derive(Debug)]
pub struct ManagedAgentProcess {
    child: Child,
}

#[derive(Debug)]
pub enum StartError {
    /// Binário `assistant-hub-audio` não encontrado no PATH.
    BinaryNotFound,
    /// O processo já está em execução (fora do shell) — não faz sentido iniciar de novo.
    AlreadyRunning,
    /// O processo iniciou mas encerrou imediatamente (falha parcial) — código de saída, se
    /// disponível.
    ExitedImmediately(Option<i32>),
    /// Falha de sistema operacional ao tentar spawnar (ex.: permissão negada).
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

/// Inicia o agent diretamente (`ControlMode::Direct`) usando o `command` fornecido pelo
/// chamador (em produção, o comando resolvido a partir de PATH; em teste, um executável fake).
/// Não inicia se um processo com o mesmo nome já for detectado rodando fora do shell
/// (FR-008 — evita duas instâncias concorrentes sem diagnóstico claro).
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

    // Falha parcial: o processo spawnou mas encerrou antes de estabilizar.
    std::thread::sleep(std::time::Duration::from_millis(50));
    if let Ok(Some(status)) = child.try_wait() {
        return Err(StartError::ExitedImmediately(status.code()));
    }

    Ok(ManagedAgentProcess { child })
}

/// Encerra um processo que o shell iniciou diretamente (`ControlMode::Direct`).
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

    #[test]
    fn guidance_command_is_exact_and_reproducible() {
        let cmd = guidance_command("11111111-1111-1111-1111-111111111111", "perfil.yaml");
        assert_eq!(
            cmd,
            "assistant-hub-audio run --session 11111111-1111-1111-1111-111111111111 --profile perfil.yaml"
        );
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
        // Executável fake: roda `true` (encerra imediatamente com sucesso), simulando uma
        // falha parcial de start (FR-008) sem depender do binário real do agent.
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
        // Executável fake de longa duração: simula o agent real rodando em foreground.
        let mut command = Command::new("sleep");
        command.arg("5");

        let mut managed = start(command).expect("start deve funcionar com processo fake");
        assert!(stop(&mut managed).is_ok());
    }
}
