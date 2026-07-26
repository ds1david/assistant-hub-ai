//! Resolução do binário do agent de áudio (sidecar → config/env → PATH) e probe de versão.
//! Specs/025-r5-audio-agent-sidecar — FR-001/004, contracts/agent-sidecar-shell.md.

use serde::Serialize;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

/// Origem da resolução do binário (JSON camelCase no AgentStatus).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum BinarySource {
    Sidecar,
    Config,
    Path,
    Missing,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BinaryResolution {
    pub path: Option<PathBuf>,
    pub source: BinarySource,
    pub version: Option<String>,
}

impl BinaryResolution {
    pub fn missing() -> Self {
        Self {
            path: None,
            source: BinarySource::Missing,
            version: None,
        }
    }

    pub fn with_version(mut self, version: Option<String>) -> Self {
        self.version = version;
        self
    }
}

/// Ordem: sidecar candidates → env override → config override → PATH → missing.
pub fn resolve_audio_agent_binary(
    sidecar_candidates: &[PathBuf],
    env_override: Option<&str>,
    config_override: Option<&str>,
) -> BinaryResolution {
    for candidate in sidecar_candidates {
        if is_usable_binary(candidate) {
            return BinaryResolution {
                path: Some(candidate.clone()),
                source: BinarySource::Sidecar,
                version: None,
            };
        }
    }

    if let Some(raw) = env_override.map(str::trim).filter(|s| !s.is_empty()) {
        let path = PathBuf::from(raw);
        if is_usable_binary(&path) {
            return BinaryResolution {
                path: Some(path),
                source: BinarySource::Config,
                version: None,
            };
        }
    }

    if let Some(raw) = config_override.map(str::trim).filter(|s| !s.is_empty()) {
        let path = PathBuf::from(raw);
        if is_usable_binary(&path) {
            return BinaryResolution {
                path: Some(path),
                source: BinarySource::Config,
                version: None,
            };
        }
    }

    if let Some(path) = find_on_path("assistant-hub-audio") {
        return BinaryResolution {
            path: Some(path),
            source: BinarySource::Path,
            version: None,
        };
    }

    BinaryResolution::missing()
}

/// Candidatos típicos ao lado do executável do shell (Tauri externalBin).
pub fn default_sidecar_candidates(resource_dir: Option<&Path>) -> Vec<PathBuf> {
    let mut out = Vec::new();
    if let Some(dir) = resource_dir {
        push_agent_names(dir, &mut out);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            push_agent_names(dir, &mut out);
        }
    }
    out
}

fn push_agent_names(dir: &Path, out: &mut Vec<PathBuf>) {
    out.push(dir.join("assistant-hub-audio"));
    out.push(dir.join("assistant-hub-audio.exe"));
}

fn is_usable_binary(path: &Path) -> bool {
    path.is_file()
}

fn find_on_path(name: &str) -> Option<PathBuf> {
    let path_var = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join(name);
        if is_usable_binary(&candidate) {
            return Some(candidate);
        }
        let with_exe = dir.join(format!("{name}.exe"));
        if is_usable_binary(&with_exe) {
            return Some(with_exe);
        }
    }
    None
}

/// Executa `<bin> --version` com timeout curto; nunca inventa versão.
pub fn probe_agent_version(bin: &Path) -> Option<String> {
    use std::io::Read;

    let mut child = Command::new(bin)
        .arg("--version")
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;

    let timeout = Duration::from_millis(800);
    let start = std::time::Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let mut buf = String::new();
                if let Some(mut out) = child.stdout.take() {
                    let _ = out.read_to_string(&mut buf);
                }
                if status.success() {
                    return parse_version_stdout(&buf);
                }
                return None;
            }
            Ok(None) if start.elapsed() > timeout => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
            Ok(None) => std::thread::sleep(Duration::from_millis(20)),
            Err(_) => return None,
        }
    }
}

fn parse_version_stdout(stdout: &str) -> Option<String> {
    let line = stdout.lines().next()?.trim();
    if line.is_empty() {
        return None;
    }
    // "assistant-hub-audio 0.2.0" ou só "0.2.0"
    let version = line
        .split_whitespace()
        .last()
        .filter(|s| !s.is_empty())?
        .to_string();
    Some(version)
}

/// Resolve e preenche versão quando o path existe.
pub fn resolve_with_version(
    sidecar_candidates: &[PathBuf],
    env_override: Option<&str>,
    config_override: Option<&str>,
) -> BinaryResolution {
    let mut resolved = resolve_audio_agent_binary(sidecar_candidates, env_override, config_override);
    if let Some(path) = resolved.path.clone() {
        resolved.version = probe_agent_version(&path);
    }
    resolved
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    fn temp_dir(name: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!(
            "desktop-shell-sidecar-{}-{}-{}",
            std::process::id(),
            name,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&p).unwrap();
        p
    }

    fn write_executable(path: &Path, body: &str) {
        fs::write(path, body).unwrap();
        let mut perms = fs::metadata(path).unwrap().permissions();
        perms.set_mode(0o755);
        fs::set_permissions(path, perms).unwrap();
    }

    #[test]
    fn resolve_prefers_sidecar_over_path() {
        let dir = temp_dir("sidecar-first");
        let sidecar = dir.join("assistant-hub-audio");
        write_executable(&sidecar, "#!/bin/sh\necho sidecar\n");

        // PATH entry would also match name; sidecar list wins.
        let got = resolve_audio_agent_binary(&[sidecar.clone()], None, None);
        assert_eq!(got.source, BinarySource::Sidecar);
        assert_eq!(got.path.as_deref(), Some(sidecar.as_path()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn resolve_env_override_is_config_source() {
        let dir = temp_dir("env");
        let bin = dir.join("custom-agent");
        write_executable(&bin, "#!/bin/sh\necho hi\n");

        let got = resolve_audio_agent_binary(&[], Some(bin.to_str().unwrap()), None);
        assert_eq!(got.source, BinarySource::Config);
        assert_eq!(got.path.as_deref(), Some(bin.as_path()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn resolve_missing_when_nothing_usable() {
        // PATH real do host pode ter o agent (Developer); isola o lookup.
        let original = std::env::var_os("PATH");
        std::env::set_var("PATH", "/no/such/path-for-sidecar-test-025");
        let got = resolve_audio_agent_binary(
            &[PathBuf::from("/no/such/sidecar-agent-025")],
            Some("/no/such/env-agent-025"),
            Some("/no/such/config-agent-025"),
        );
        match original {
            Some(p) => std::env::set_var("PATH", p),
            None => std::env::remove_var("PATH"),
        }
        assert_eq!(got, BinaryResolution::missing());
    }

    #[test]
    fn probe_version_parses_cli_output() {
        let dir = temp_dir("version");
        let bin = dir.join("assistant-hub-audio");
        write_executable(
            &bin,
            "#!/bin/sh\necho 'assistant-hub-audio 0.2.0'\n",
        );
        assert_eq!(probe_agent_version(&bin).as_deref(), Some("0.2.0"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn probe_version_none_on_failure() {
        let dir = temp_dir("ver-fail");
        let bin = dir.join("bad");
        write_executable(&bin, "#!/bin/sh\nexit 1\n");
        assert_eq!(probe_agent_version(&bin), None);
        let _ = fs::remove_dir_all(&dir);
    }
}
