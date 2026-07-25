// Bootstrap Tauri do shell desktop (feature "gui"). Este binário depende do crate `tauri`
// (WebView2 no Windows / webkit2gtk no Linux) e por isso NÃO compila neste WSL de
// desenvolvimento (sem GTK instalado — ver research.md, Decisão 7). A lógica de negócio que
// ele expõe como comandos vive inteiramente em `desktop_shell::{config, session_core_client,
// agent_control}`, testada via `cargo test` (sem a feature "gui") independentemente deste
// arquivo. Build/execução reais deste binário ocorrem na máquina Windows de referência
// (docs/desktop-shell/packaging.md).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use desktop_shell::agent_control::{self, AgentStatus, ControlMode, ManagedAgentProcess};
use desktop_shell::ai_provider_client::{
    AiProviderClient, ConnectionTestResult, InvocationResult, Provider, SecretPreview,
};
use desktop_shell::assistant_prefs::{self, AssistantSessionPreferences};
use desktop_shell::config::{self, ShellConfig};
use desktop_shell::session_core_client::{
    channel_status_views, session_status_view, transcript_feed_entries, ChannelStatusView,
    SessionCoreClient, SessionStatusView, TranscriptFeedEntry,
};
use serde::Serialize;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;
use tauri::{Manager, State};

struct AppState {
    config: Mutex<ShellConfig>,
    managed_agent: Mutex<Option<ManagedAgentProcess>>,
    /// Diretório de config do app (prefs do Assistente).
    config_dir: PathBuf,
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
fn get_transcript_feed(state: State<AppState>, session_id: String) -> Vec<TranscriptFeedEntry> {
    let base_url = state.config.lock().unwrap().session_core_base_url.clone();
    let client = SessionCoreClient::new(base_url);
    match client.get_events(&session_id) {
        Ok(events) => transcript_feed_entries(&events),
        Err(_) => Vec::new(),
    }
}

#[tauri::command]
fn get_agent_status(state: State<AppState>) -> AgentStatus {
    let running = agent_control::detect_running();
    let has_handle = state.managed_agent.lock().unwrap().is_some();
    AgentStatus {
        running,
        control_mode: if has_handle {
            ControlMode::Direct
        } else {
            ControlMode::Guided
        },
        guidance_command: String::new(), // preenchido pelo chamador (session_id/perfil só são
        // conhecidos no frontend); ver agent_control::guidance_command
        last_error: None,
    }
}

#[tauri::command]
fn start_agent(
    state: State<AppState>,
    session_id: String,
    profile_path: String,
) -> Result<AgentStatus, String> {
    let mut command = Command::new("assistant-hub-audio");
    command
        .arg("run")
        .arg("--session")
        .arg(&session_id)
        .arg("--profile")
        .arg(&profile_path);

    match agent_control::start(command) {
        Ok(managed) => {
            *state.managed_agent.lock().unwrap() = Some(managed);
            Ok(AgentStatus {
                running: true,
                control_mode: ControlMode::Direct,
                guidance_command: agent_control::guidance_command(&session_id, &profile_path),
                last_error: None,
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
            })
            .map_err(|e| e.to_string()),
        None => Err(
            "o shell não tem o handle deste processo (foi iniciado fora do shell) — pare manualmente"
                .to_string(),
        ),
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
    ai_provider_client(&state)
        .delete_provider(&provider_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_ai_provider_secret_preview(
    state: State<AppState>,
    provider_id: String,
) -> Result<SecretPreview, String> {
    ai_provider_client(&state)
        .secret_preview(&provider_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn test_ai_provider_connection(
    state: State<AppState>,
    provider_id: String,
) -> Result<ConnectionTestResult, String> {
    ai_provider_client(&state)
        .test_connection(&provider_id)
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
    ai_provider_client(&state)
        .invoke(
            &session_id,
            channel_id.as_deref(),
            &route,
            &capability,
            &input,
        )
        .map_err(|e| e.to_string())
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
            app.manage(AppState {
                config: Mutex::new(loaded),
                managed_agent: Mutex::new(None),
                config_dir,
            });
            Ok(())
        })
        // Fechar a janela NÃO encerra session-core nem o agent Windows por padrão — nenhum
        // hook de "on_window_event"/"exit" mata processos auxiliares aqui (edge case da spec).
        .invoke_handler(tauri::generate_handler![
            get_session_status,
            create_session,
            list_sessions,
            get_transcript_feed,
            get_agent_status,
            start_agent,
            stop_agent,
            get_shell_config,
            get_assistant_prefs,
            set_assistant_prefs,
            list_ai_providers,
            save_ai_provider,
            set_ai_provider_enabled,
            delete_ai_provider,
            get_ai_provider_secret_preview,
            test_ai_provider_connection,
            invoke_ai_provider,
        ])
        .run(tauri::generate_context!())
        .expect("erro ao iniciar o shell desktop");
}
