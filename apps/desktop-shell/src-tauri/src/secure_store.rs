//! Secure secret store for provider API keys (issue #64 / specs/029).
//! Values never appear in provider YAML or Tauri command return types exposed to JS
//! except via explicit put from the form (one-way).

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

pub const OS_REF_PREFIX: &str = "os:";
pub const PROVIDER_ID_PREFIX: &str = "assistant-hub/providers/";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StoreError {
    Unavailable(String),
    Io(String),
}

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StoreError::Unavailable(m) | StoreError::Io(m) => write!(f, "{m}"),
        }
    }
}

pub trait SecureSecretStore: Send + Sync {
    fn put(&self, logical_id: &str, value: &str) -> Result<(), StoreError>;
    fn get(&self, logical_id: &str) -> Result<Option<String>, StoreError>;
    fn delete(&self, logical_id: &str) -> Result<(), StoreError>;
    fn list_ids(&self) -> Result<Vec<String>, StoreError>;
    fn has(&self, logical_id: &str) -> Result<bool, StoreError> {
        Ok(self.get(logical_id)?.is_some())
    }
}

/// In-memory store for tests and CI (no OS keyring).
pub struct MemorySecureSecretStore {
    map: Mutex<HashMap<String, String>>,
}

impl MemorySecureSecretStore {
    pub fn new() -> Self {
        Self {
            map: Mutex::new(HashMap::new()),
        }
    }
}

impl Default for MemorySecureSecretStore {
    fn default() -> Self {
        Self::new()
    }
}

impl SecureSecretStore for MemorySecureSecretStore {
    fn put(&self, logical_id: &str, value: &str) -> Result<(), StoreError> {
        self.map
            .lock()
            .map_err(|e| StoreError::Unavailable(e.to_string()))?
            .insert(logical_id.to_string(), value.to_string());
        Ok(())
    }

    fn get(&self, logical_id: &str) -> Result<Option<String>, StoreError> {
        Ok(self
            .map
            .lock()
            .map_err(|e| StoreError::Unavailable(e.to_string()))?
            .get(logical_id)
            .cloned())
    }

    fn delete(&self, logical_id: &str) -> Result<(), StoreError> {
        self.map
            .lock()
            .map_err(|e| StoreError::Unavailable(e.to_string()))?
            .remove(logical_id);
        Ok(())
    }

    fn list_ids(&self) -> Result<Vec<String>, StoreError> {
        let mut ids: Vec<String> = self
            .map
            .lock()
            .map_err(|e| StoreError::Unavailable(e.to_string()))?
            .keys()
            .cloned()
            .collect();
        ids.sort();
        Ok(ids)
    }
}

/// OS-backed store via `keyring` + id index file (keyring has no list API).
pub struct OsSecureSecretStore {
    service: String,
    index_path: PathBuf,
}

impl OsSecureSecretStore {
    pub fn new(config_dir: &Path) -> Self {
        Self {
            service: "assistant-hub-ai".to_string(),
            index_path: config_dir.join("secret-ids.json"),
        }
    }

    fn load_index(&self) -> Result<Vec<String>, StoreError> {
        if !self.index_path.exists() {
            return Ok(Vec::new());
        }
        let raw = fs::read_to_string(&self.index_path).map_err(|e| StoreError::Io(e.to_string()))?;
        let ids: Vec<String> =
            serde_json::from_str(&raw).map_err(|e| StoreError::Io(e.to_string()))?;
        Ok(ids)
    }

    fn save_index(&self, ids: &[String]) -> Result<(), StoreError> {
        if let Some(parent) = self.index_path.parent() {
            fs::create_dir_all(parent).map_err(|e| StoreError::Io(e.to_string()))?;
        }
        let raw = serde_json::to_string_pretty(ids).map_err(|e| StoreError::Io(e.to_string()))?;
        fs::write(&self.index_path, raw).map_err(|e| StoreError::Io(e.to_string()))
    }

    fn add_to_index(&self, logical_id: &str) -> Result<(), StoreError> {
        let mut ids = self.load_index()?;
        if !ids.iter().any(|i| i == logical_id) {
            ids.push(logical_id.to_string());
            ids.sort();
            self.save_index(&ids)?;
        }
        Ok(())
    }

    fn remove_from_index(&self, logical_id: &str) -> Result<(), StoreError> {
        let mut ids = self.load_index()?;
        ids.retain(|i| i != logical_id);
        self.save_index(&ids)
    }
}

impl SecureSecretStore for OsSecureSecretStore {
    fn put(&self, logical_id: &str, value: &str) -> Result<(), StoreError> {
        let entry = keyring::Entry::new(&self.service, logical_id)
            .map_err(|e| StoreError::Unavailable(e.to_string()))?;
        entry
            .set_password(value)
            .map_err(|e| StoreError::Unavailable(e.to_string()))?;
        self.add_to_index(logical_id)
    }

    fn get(&self, logical_id: &str) -> Result<Option<String>, StoreError> {
        let entry = keyring::Entry::new(&self.service, logical_id)
            .map_err(|e| StoreError::Unavailable(e.to_string()))?;
        match entry.get_password() {
            Ok(v) => Ok(Some(v)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(StoreError::Unavailable(e.to_string())),
        }
    }

    fn delete(&self, logical_id: &str) -> Result<(), StoreError> {
        let entry = keyring::Entry::new(&self.service, logical_id)
            .map_err(|e| StoreError::Unavailable(e.to_string()))?;
        match entry.delete_credential() {
            Ok(()) => {}
            Err(keyring::Error::NoEntry) => {}
            Err(e) => return Err(StoreError::Unavailable(e.to_string())),
        }
        self.remove_from_index(logical_id)
    }

    fn list_ids(&self) -> Result<Vec<String>, StoreError> {
        self.load_index()
    }
}

/// Build `os:assistant-hub/providers/{providerId}` secretRef.
pub fn provider_secret_ref(provider_id: &str) -> String {
    format!("{OS_REF_PREFIX}{PROVIDER_ID_PREFIX}{provider_id}")
}

pub fn provider_logical_id(provider_id: &str) -> String {
    format!("{PROVIDER_ID_PREFIX}{provider_id}")
}

/// Parse `os:…` → logical id; otherwise None.
pub fn logical_id_from_secret_ref(secret_ref: &str) -> Option<&str> {
    secret_ref.strip_prefix(OS_REF_PREFIX)
}

/// Mask secret for local preview (never full value). Same spirit as Java mask.
pub fn mask_secret(value: &str) -> String {
    let chars: Vec<char> = value.chars().collect();
    if chars.len() <= 8 {
        return "••••".to_string();
    }
    let prefix: String = chars.iter().take(3).collect();
    let suffix: String = chars.iter().rev().take(4).cloned().rev().collect();
    format!("{prefix}…{suffix}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_put_get_delete_list() {
        let store = MemorySecureSecretStore::new();
        store.put("assistant-hub/providers/p1", "sk-secret-value").unwrap();
        assert!(store.has("assistant-hub/providers/p1").unwrap());
        assert_eq!(
            store.get("assistant-hub/providers/p1").unwrap().as_deref(),
            Some("sk-secret-value")
        );
        assert_eq!(store.list_ids().unwrap(), vec!["assistant-hub/providers/p1".to_string()]);
        store.delete("assistant-hub/providers/p1").unwrap();
        assert!(!store.has("assistant-hub/providers/p1").unwrap());
    }

    #[test]
    fn secret_ref_helpers() {
        assert_eq!(
            provider_secret_ref("openai-main"),
            "os:assistant-hub/providers/openai-main"
        );
        assert_eq!(
            logical_id_from_secret_ref("os:assistant-hub/providers/x"),
            Some("assistant-hub/providers/x")
        );
        assert_eq!(logical_id_from_secret_ref("env:FOO"), None);
    }

    #[test]
    fn mask_does_not_echo_full_secret() {
        let m = mask_secret("sk-abcdefghijklmnopqrstuvwxyz");
        assert!(!m.contains("abcdefghijklmnop"));
        assert!(m.contains('…') || m.contains("••••"));
    }
}
