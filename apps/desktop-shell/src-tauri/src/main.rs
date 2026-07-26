// Bootstrap Tauri do shell desktop (feature "gui"). Este binário depende do crate `tauri`
// (WebView2 no Windows / webkit2gtk no Linux) e por isso NÃO compila neste WSL de
// desenvolvimento (sem GTK instalado — ver research.md, Decisão 7). A lógica de negócio que
// ele expõe como comandos vive inteiramente em `desktop_shell::{config, session_core_client,
// agent_control}`, testada via `cargo test` (sem a feature "gui") independentemente deste
// arquivo. Build/execução reais deste binário ocorrem na máquina Windows de referência
// (docs/desktop-shell/packaging.md).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use desktop_shell::agent_control::{
    self, AgentSessionSource, AgentStatus, ControlMode, ManagedAgentProcess,
};
use desktop_shell::ai_provider_client::{
    AiProviderClient, ConnectionTestResult, InvocationResult, Provider, SecretPreview,
};
use desktop_shell::assistant_prefs::{self, AssistantSessionPreferences};
use desktop_shell::config::{self, ShellConfig};
use desktop_shell::session_core_client::{
    channel_status_views, session_status_view, transcript_feed_entries, ChannelStatusView,
    MemoryItem, MemorySearchHit, SessionCoreClient, SessionStatusView, TranscriptFeedEntry,
};
#[allow(unused_imports)]
use desktop_shell::secure_store::{
    self, mask_secret, provider_logical_id, provider_secret_ref, logical_id_from_secret_ref,
    MemorySecureSecretStore, OsSecureSecretStore, SecureSecretStore,
};
use desktop_shell::sidecar::{self, BinaryResolution, BinarySource};
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;
use std::sync::{Arc, Mutex};
use tauri::{Manager, RunEvent, State};

struct AppState {
    config: Mutex<ShellConfig>,
    managed_agent: Mutex<Option<ManagedAgentProcess>>,
    /// Último sessionId passado a um start bem-sucedido gerenciado pelo shell (020 / FR-005).
    last_managed_session_id: Mutex<Option<String>>,
    /// Diretório de config do app (prefs do Assistente).
    config_dir: PathBuf,
    /// Provider secrets (os:); never exposed fully to the webview.
    secret_store: Arc<dyn SecureSecretStore>,
}

#[derive(Serialize)]
struct SessionStatusResponse {
    status: SessionStatusView,
    channels: Vec<ChannelStatusView>,
}

#[tauri::command]
fn get_session_status(state: State<AppState>, session_id: String) -> SessionStatusResponse {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    let status = session_status_view(&client, &session_id);

    let channels = match client.get_events(&session_id) {
        Ok(events) => channel_status_views(&events),
        Err(_) => Vec::new(),
    };

    SessionStatusResponse { status, channels }
}

#[tauri::command]
fn create_session(
    state: State<AppState>,
    title: String,
    profile_id: String,
) -> Result<desktop_shell::session_core_client::ConversationSession, String> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    client
        .create_session(&title, &profile_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn list_sessions(
    state: State<AppState>,
) -> Result<Vec<desktop_shell::session_core_client::ConversationSession>, String> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    client.list_sessions().map_err(|e| e.to_string())
}

#[tauri::command]
fn get_assistant_prefs(
    state: State<AppState>,
    session_id: String,
) -> AssistantSessionPreferences {
    let path = assistant_prefs::prefs_path(&state.config_dir);
    assistant_prefs::get_prefs(&path, &session_id)
}

#[tauri::command]
fn set_assistant_prefs(
    state: State<AppState>,
    session_id: String,
    prefs: AssistantSessionPreferences,
) -> Result<(), String> {
    let path = assistant_prefs::prefs_path(&state.config_dir);
    assistant_prefs::set_prefs(&path, &session_id, prefs).map_err(|e| e.to_string())
}

#[tauri::command]
fn search_session_memory(
    state: State<AppState>,
    session_id: String,
    q: Option<String>,
    source_type: Option<String>,
    limit: Option<u32>,
) -> Result<Vec<MemorySearchHit>, String> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    client
        .search_session(
            &session_id,
            q.as_deref(),
            source_type.as_deref(),
            limit,
        )
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_session_memory_items(
    state: State<AppState>,
    session_id: String,
) -> Result<Vec<MemoryItem>, String> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    client
        .memory_items(&session_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_transcript_feed(state: State<AppState>, session_id: String) -> Vec<TranscriptFeedEntry> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    match client.get_events(&session_id) {
        Ok(events) => transcript_feed_entries(&events),
        Err(_) => Vec::new(),
    }
}

fn resolve_binary_for_state(state: &AppState) -> BinaryResolution {
    let config = state.config.lock().unwrap();
    let env_override = std::env::var("ASSISTANT_HUB_AUDIO_BIN").ok();
    let candidates = sidecar::default_sidecar_candidates(None);
    sidecar::resolve_with_version(
        &candidates,
        env_override.as_deref(),
        config.audio_agent_bin.as_deref(),
    )
}

#[tauri::command]
fn get_agent_status(state: State<AppState>) -> AgentStatus {
    let binary = resolve_binary_for_state(&state);
    let running = agent_control::detect_running();
    let mut managed_guard = state.managed_agent.lock().unwrap();
    let mut has_handle = managed_guard.is_some();
    let mut managed_alive = false;
    if has_handle {
        if let Some(managed) = managed_guard.as_mut() {
            managed_alive = agent_control::managed_is_alive(managed);
        }
        // Processo morreu (enumeração ou child): limpa handle órfão.
        if !running || !managed_alive {
            *managed_guard = None;
            *state.last_managed_session_id.lock().unwrap() = None;
            has_handle = false;
            managed_alive = false;
        }
    }
    drop(managed_guard);
    let last_managed = state.last_managed_session_id.lock().unwrap().clone();
    agent_control::build_status(
        running,
        has_handle,
        last_managed.as_deref(),
        String::new(), // guidance preenchido no webview com sessão ativa
        None,
        &binary,
        managed_alive,
    )
}

#[tauri::command]
fn start_agent(
    state: State<AppState>,
    session_id: String,
    profile_path: String,
) -> Result<AgentStatus, String> {
    let binary = resolve_binary_for_state(&state);
    if binary.source == BinarySource::Missing || binary.path.is_none() {
        return Err(
            "binário assistant-hub-audio não encontrado (sidecar ausente, sem ASSISTANT_HUB_AUDIO_BIN/config e fora do PATH) — veja docs/desktop-shell/packaging.md"
                .to_string(),
        );
    }
    let program = agent_control::command_program(&binary);
    let mut command = Command::new(&program);
    command
        .arg("run")
        .arg("--session")
        .arg(&session_id)
        .arg("--profile")
        .arg(&profile_path);

    match agent_control::start(command) {
        Ok(managed) => {
            *state.managed_agent.lock().unwrap() = Some(managed);
            *state.last_managed_session_id.lock().unwrap() = Some(session_id.clone());
            Ok(AgentStatus {
                running: true,
                control_mode: ControlMode::Direct,
                guidance_command: agent_control::guidance_command(&session_id, &profile_path),
                last_error: None,
                agent_session_id: Some(session_id),
                agent_session_source: AgentSessionSource::Managed,
                binary_path: binary.path.as_ref().map(|p| p.display().to_string()),
                binary_source: binary.source,
                agent_version: binary.version.clone(),
                healthy: true,
            })
        }
        Err(err) => Err(err.to_string()),
    }
}

#[tauri::command]
fn stop_agent(state: State<AppState>) -> Result<(), String> {
    let mut guard = state.managed_agent.lock().unwrap();
    match guard.as_mut() {
        Some(managed) => agent_control::stop(managed)
            .map(|_| {
                *guard = None;
                *state.last_managed_session_id.lock().unwrap() = None;
            })
            .map_err(|e| e.to_string()),
        None => Err(
            "o shell não tem o handle deste processo (foi iniciado fora do shell) — pare manualmente"
                .to_string(),
        ),
    }
}

/// Lightweight HTTP health probe for diagnostics (#67). Never returns bodies with secrets
/// (only status line + a few known-safe JSON keys).
#[tauri::command]
fn probe_http_health(url: String) -> Result<serde_json::Value, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;
    match client.get(&url).send() {
        Ok(resp) => {
            let code = resp.status().as_u16();
            let ok = resp.status().is_success();
            let body = resp.text().unwrap_or_default();
            let summary = summarize_health_body(&body);
            Ok(serde_json::json!({
                "ok": ok,
                "statusCode": code,
                "detail": summary,
            }))
        }
        Err(e) => Ok(serde_json::json!({
            "ok": false,
            "statusCode": null,
            "detail": format!("error: {e}"),
        })),
    }
}

fn summarize_health_body(body: &str) -> String {
    // Prefer compact JSON fields; never dump large blobs.
    if let Ok(v) = serde_json::from_str::<serde_json::Value>(body) {
        let mut parts = Vec::new();
        if let Some(s) = v.get("status").and_then(|x| x.as_str()) {
            parts.push(format!("status={s}"));
        }
        if let Some(s) = v.get("model").and_then(|x| x.as_str()) {
            parts.push(format!("model={s}"));
        }
        if let Some(s) = v.get("device").and_then(|x| x.as_str()) {
            parts.push(format!("device={s}"));
        }
        if let Some(b) = v.get("modelLoaded").and_then(|x| x.as_bool()) {
            parts.push(format!("modelLoaded={b}"));
        }
        if parts.is_empty() {
            return "ok".to_string();
        }
        return parts.join(" ");
    }
    let t = body.trim();
    if t.is_empty() {
        return "empty body".to_string();
    }
    if t.len() > 120 {
        format!("{}…", &t[..120])
    } else {
        t.to_string()
    }
}

#[tauri::command]
fn get_shell_config(state: State<AppState>) -> ShellConfig {
    state.config.lock().unwrap().clone()
}

// -----------------------------------------------------------------------------------------
// AI Provider Hub (R6, issue #37, US3) — todo acesso de rede fica aqui, nunca no webview,
// mesmo padrão já usado acima para o session-core (specs/015-issue-37-ai-provider-hub).
// -----------------------------------------------------------------------------------------

fn ai_provider_client(state: &State<'_, AppState>) -> AiProviderClient {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    AiProviderClient::new(base_url)
}

#[tauri::command]
fn list_ai_providers(state: State<AppState>) -> Result<Vec<Provider>, String> {
    ai_provider_client(&state)
        .list_providers()
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn save_ai_provider(state: State<AppState>, provider: Provider) -> Result<Provider, String> {
    ai_provider_client(&state)
        .save_provider(&provider)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn set_ai_provider_enabled(
    state: State<AppState>,
    provider_id: String,
    enabled: bool,
) -> Result<Provider, String> {
    ai_provider_client(&state)
        .set_enabled(&provider_id, enabled)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn delete_ai_provider(state: State<AppState>, provider_id: String) -> Result<(), String> {
    let _ = state.secret_store.delete(&provider_logical_id(&provider_id));
    ai_provider_client(&state)
        .delete_provider(&provider_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_ai_provider_secret_preview(
    state: State<AppState>,
    provider_id: String,
) -> Result<SecretPreview, String> {
    // Prefer local os: mask when store has the key; else ask session-core (env:).
    let client = ai_provider_client(&state);
    if let Ok(providers) = client.list_providers() {
        if let Some(p) = providers.iter().find(|p| p.id == provider_id) {
            if let Some(ref_str) = p.authentication.secret_ref.as_deref() {
                if let Some(logical) = logical_id_from_secret_ref(ref_str) {
                    match state.secret_store.get(logical) {
                        Ok(Some(value)) => {
                            return Ok(SecretPreview {
                                provider_id,
                                masked_value: Some(mask_secret(&value)),
                            });
                        }
                        Ok(None) => {
                            return Ok(SecretPreview {
                                provider_id,
                                masked_value: None,
                            });
                        }
                        Err(e) => return Err(e.to_string()),
                    }
                }
            }
        }
    }
    client
        .secret_preview(&provider_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn test_ai_provider_connection(
    state: State<AppState>,
    provider_id: String,
) -> Result<ConnectionTestResult, String> {
    let overrides = collect_secret_overrides(&state).map_err(|e| e.to_string())?;
    ai_provider_client(&state)
        .test_connection_with_secrets(&provider_id, Some(&overrides))
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn invoke_ai_provider(
    state: State<AppState>,
    session_id: String,
    channel_id: Option<String>,
    route: String,
    capability: String,
    input: String,
) -> Result<InvocationResult, String> {
    let overrides = collect_secret_overrides(&state).map_err(|e| e.to_string())?;
    ai_provider_client(&state)
        .invoke_with_secrets(
            &session_id,
            channel_id.as_deref(),
            &route,
            &capability,
            &input,
            Some(&overrides),
        )
        .map_err(|e| e.to_string())
}

/// Put secret in store; returns the secretRef to store on the provider (os:…).
#[tauri::command]
fn secret_store_put(
    state: State<AppState>,
    provider_id: String,
    value: String,
) -> Result<String, String> {
    let logical = provider_logical_id(&provider_id);
    state
        .secret_store
        .put(&logical, &value)
        .map_err(|e| e.to_string())?;
    Ok(provider_secret_ref(&provider_id))
}

#[tauri::command]
fn secret_store_delete(state: State<AppState>, provider_id: String) -> Result<(), String> {
    let logical = provider_logical_id(&provider_id);
    state
        .secret_store
        .delete(&logical)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn secret_store_list_ids(state: State<AppState>) -> Result<Vec<String>, String> {
    state.secret_store.list_ids().map_err(|e| e.to_string())
}

#[tauri::command]
fn secret_store_has(state: State<AppState>, provider_id: String) -> Result<bool, String> {
    let logical = provider_logical_id(&provider_id);
    state.secret_store.has(&logical).map_err(|e| e.to_string())
}

fn collect_secret_overrides(
    state: &State<AppState>,
) -> Result<HashMap<String, String>, secure_store::StoreError> {
    let mut map = HashMap::new();
    let client = ai_provider_client(state);
    let providers = match client.list_providers() {
        Ok(p) => p,
        Err(_) => return Ok(map),
    };
    for p in providers {
        let Some(ref_str) = p.authentication.secret_ref.as_deref() else {
            continue;
        };
        let Some(logical) = logical_id_from_secret_ref(ref_str) else {
            continue;
        };
        if let Some(value) = state.secret_store.get(logical)? {
            map.insert(ref_str.to_string(), value);
        }
    }
    Ok(map)
}

fn default_secret_store(config_dir: &std::path::Path) -> Arc<dyn SecureSecretStore> {
    #[cfg(target_os = "windows")]
    {
        let _ = config_dir;
        Arc::new(OsSecureSecretStore::new(config_dir))
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = config_dir;
        Arc::new(MemorySecureSecretStore::new())
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let config_dir = app
                .path()
                .app_config_dir()
                .expect("diretório de config do app");
            let config_path = config_dir.join("shell-config.json");
            let loaded = config::load(&config_path);
            // Windows: OS keyring. Other platforms: in-memory (use env: for durable WSL/dev secrets).
            let secret_store: Arc<dyn SecureSecretStore> = default_secret_store(&config_dir);
            app.manage(AppState {
                config: Mutex::new(loaded),
                managed_agent: Mutex::new(None),
                last_managed_session_id: Mutex::new(None),
                config_dir,
                secret_store,
            });
            Ok(())
        })
        // 025: encerra agent **gerenciado** no Exit; session-core e agents Guided/externos
        // não são tocados (FR-006).
        .invoke_handler(tauri::generate_handler![
            get_session_status,
            create_session,
            list_sessions,
            search_session_memory,
            get_session_memory_items,
            get_transcript_feed,
            get_agent_status,
            start_agent,
            stop_agent,
            get_shell_config,
            probe_http_health,
            get_assistant_prefs,
            set_assistant_prefs,
            list_ai_providers,
            save_ai_provider,
            set_ai_provider_enabled,
            delete_ai_provider,
            get_ai_provider_secret_preview,
            test_ai_provider_connection,
            invoke_ai_provider,
            secret_store_put,
            secret_store_delete,
            secret_store_list_ids,
            secret_store_has,
        ])
        .build(tauri::generate_context!())
        .expect("erro ao construir o shell desktop")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
                if let Some(state) = app_handle.try_state::<AppState>() {
                    let mut guard = state.managed_agent.lock().unwrap();
                    agent_control::shutdown_managed(&mut guard);
                    *state.last_managed_session_id.lock().unwrap() = None;
                }
            }
        });
}
