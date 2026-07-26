//! Preferências locais do shell (data-model.md § ShellConfig). Nenhum segredo é lido ou
//! gravado aqui — AI Provider Hub está fora de escopo desta feature (FR-013).

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WindowState {
    pub width: f64,
    pub height: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub x: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub y: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShellConfig {
    #[serde(rename = "sessionCoreBaseUrl")]
    pub session_core_base_url: String,
    #[serde(rename = "windowState", skip_serializing_if = "Option::is_none")]
    pub window_state: Option<WindowState>,
    /// Override local do binário do agent (025 sidecar). Env `ASSISTANT_HUB_AUDIO_BIN` vence este campo.
    #[serde(
        rename = "audioAgentBin",
        default,
        skip_serializing_if = "Option::is_none"
    )]
    pub audio_agent_bin: Option<String>,
}

impl Default for ShellConfig {
    fn default() -> Self {
        Self {
            session_core_base_url: "http://localhost:8080".to_string(),
            window_state: None,
            audio_agent_bin: None,
        }
    }
}

/// Carrega a config de `path`; se o arquivo não existir ou estiver corrompido, devolve o
/// default sem falhar e sem sobrescrever o arquivo existente.
pub fn load(path: &Path) -> ShellConfig {
    match fs::read_to_string(path) {
        Ok(contents) => serde_json::from_str(&contents).unwrap_or_default(),
        Err(_) => ShellConfig::default(),
    }
}

/// Grava a config em `path`, criando o diretório pai se necessário.
pub fn save(path: &Path, config: &ShellConfig) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let contents = serde_json::to_string_pretty(config)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    fs::write(path, contents)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::fs;

    fn temp_path(name: &str) -> std::path::PathBuf {
        let mut p = env::temp_dir();
        p.push(format!(
            "desktop-shell-config-test-{}-{}",
            std::process::id(),
            name
        ));
        p
    }

    #[test]
    fn load_returns_default_when_file_missing() {
        let path = temp_path("missing.json");
        let _ = fs::remove_file(&path);

        let config = load(&path);

        assert_eq!(config, ShellConfig::default());
        assert_eq!(config.session_core_base_url, "http://localhost:8080");
    }

    #[test]
    fn save_then_load_roundtrips() {
        let path = temp_path("roundtrip.json");
        let original = ShellConfig {
            session_core_base_url: "http://localhost:9090".to_string(),
            window_state: Some(WindowState {
                width: 1024.0,
                height: 768.0,
                x: Some(10.0),
                y: None,
            }),
            audio_agent_bin: Some(r"C:\tools\assistant-hub-audio.exe".to_string()),
        };

        save(&path, &original).expect("save deve funcionar");
        let loaded = load(&path);

        assert_eq!(loaded, original);
        let _ = fs::remove_file(&path);
    }

    #[test]
    fn load_returns_default_when_file_corrupted() {
        let path = temp_path("corrupted.json");
        fs::write(&path, "isto nao e json valido").unwrap();

        let config = load(&path);

        assert_eq!(config, ShellConfig::default());
        let _ = fs::remove_file(&path);
    }

    #[test]
    fn config_never_serializes_a_secret_like_field() {
        // Trava de regressão para FR-013: ShellConfig não tem (e não deve ganhar) campo de
        // segredo/API key — só sessionCoreBaseUrl e windowState.
        let json = serde_json::to_string(&ShellConfig::default()).unwrap();
        assert!(!json.to_lowercase().contains("secret"));
        assert!(!json.to_lowercase().contains("token"));
        assert!(!json.to_lowercase().contains("apikey"));
    }
}
