//! Preferências do Assistente por sessão (JSON local, FR-025). Sem segredos.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct AssistantSessionPreferences {
    pub auto_enabled: bool,
    pub enabled_source_types: Vec<String>,
    pub input_mode: String,
}

impl Default for AssistantSessionPreferences {
    fn default() -> Self {
        Self {
            auto_enabled: false,
            enabled_source_types: vec!["system".to_string()],
            input_mode: "question-plus-recent-context".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct AssistantPrefsFile {
    #[serde(default)]
    pub by_session_id: HashMap<String, AssistantSessionPreferences>,
}

pub fn prefs_path(config_dir: &Path) -> PathBuf {
    config_dir.join("assistant-prefs.json")
}

pub fn load_store(path: &Path) -> AssistantPrefsFile {
    match fs::read_to_string(path) {
        Ok(contents) => serde_json::from_str(&contents).unwrap_or_default(),
        Err(_) => AssistantPrefsFile::default(),
    }
}

pub fn save_store(path: &Path, store: &AssistantPrefsFile) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let contents = serde_json::to_string_pretty(store)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    fs::write(path, contents)
}

pub fn get_prefs(path: &Path, session_id: &str) -> AssistantSessionPreferences {
    let store = load_store(path);
    store
        .by_session_id
        .get(session_id)
        .cloned()
        .unwrap_or_default()
}

pub fn set_prefs(
    path: &Path,
    session_id: &str,
    prefs: AssistantSessionPreferences,
) -> std::io::Result<()> {
    let mut store = load_store(path);
    store.by_session_id.insert(session_id.to_string(), prefs);
    save_store(path, &store)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    fn temp_path(name: &str) -> PathBuf {
        let mut p = env::temp_dir();
        p.push(format!(
            "assistant-prefs-test-{}-{}",
            std::process::id(),
            name
        ));
        p
    }

    #[test]
    fn defaults_when_missing() {
        let path = temp_path("missing.json");
        let _ = fs::remove_file(&path);
        let prefs = get_prefs(&path, "s1");
        assert!(!prefs.auto_enabled);
        assert_eq!(prefs.enabled_source_types, vec!["system".to_string()]);
        assert_eq!(prefs.input_mode, "question-plus-recent-context");
    }

    #[test]
    fn save_and_load_isolation() {
        let path = temp_path("iso.json");
        let _ = fs::remove_file(&path);

        set_prefs(
            &path,
            "S",
            AssistantSessionPreferences {
                auto_enabled: true,
                enabled_source_types: vec!["system".to_string(), "microphone".to_string()],
                input_mode: "question-only".to_string(),
            },
        )
        .unwrap();
        set_prefs(
            &path,
            "T",
            AssistantSessionPreferences {
                auto_enabled: false,
                enabled_source_types: vec!["microphone".to_string()],
                input_mode: "question-plus-recent-context".to_string(),
            },
        )
        .unwrap();

        let s = get_prefs(&path, "S");
        let t = get_prefs(&path, "T");
        assert!(s.auto_enabled);
        assert_eq!(s.input_mode, "question-only");
        assert!(!t.auto_enabled);
        assert_eq!(t.enabled_source_types, vec!["microphone".to_string()]);

        let _ = fs::remove_file(&path);
    }
}
