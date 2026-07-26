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
    /// 023 FR-004: every Final system ≥8 is a candidate when true.
    #[serde(default)]
    pub interview_mode: bool,
    /// 023 FR-006: use optional prosody.questionScore on Final events.
    #[serde(default)]
    pub use_prosody: bool,
    /// [0.0, 1.0]; default 0.65 (no dedicated UI control in v1).
    #[serde(default = "default_prosody_threshold")]
    pub prosody_threshold: f64,
}

fn default_prosody_threshold() -> f64 {
    0.65
}

impl Default for AssistantSessionPreferences {
    fn default() -> Self {
        Self {
            auto_enabled: false,
            enabled_source_types: vec!["system".to_string()],
            input_mode: "question-plus-recent-context".to_string(),
            interview_mode: false,
            use_prosody: false,
            prosody_threshold: default_prosody_threshold(),
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
                interview_mode: true,
                use_prosody: false,
                prosody_threshold: 0.65,
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
                interview_mode: false,
                use_prosody: true,
                prosody_threshold: 0.8,
            },
        )
        .unwrap();

        let s = get_prefs(&path, "S");
        let t = get_prefs(&path, "T");
        assert!(s.auto_enabled);
        assert_eq!(s.input_mode, "question-only");
        assert!(s.interview_mode);
        assert!(!t.auto_enabled);
        assert_eq!(t.enabled_source_types, vec!["microphone".to_string()]);
        assert!(t.use_prosody);
        assert!((t.prosody_threshold - 0.8).abs() < f64::EPSILON);

        let _ = fs::remove_file(&path);
    }

    #[test]
    fn legacy_json_without_new_fields_deserializes_defaults() {
        let path = temp_path("legacy.json");
        let _ = fs::remove_file(&path);
        let raw = r#"{
          "bySessionId": {
            "S": {
              "autoEnabled": true,
              "enabledSourceTypes": ["system"],
              "inputMode": "question-only"
            }
          }
        }"#;
        fs::write(&path, raw).unwrap();
        let prefs = get_prefs(&path, "S");
        assert!(prefs.auto_enabled);
        assert!(!prefs.interview_mode);
        assert!(!prefs.use_prosody);
        assert!((prefs.prosody_threshold - 0.65).abs() < f64::EPSILON);
        let _ = fs::remove_file(&path);
    }
}
