//! Testes de integração (US3) — usam um executável fake no lugar de `assistant-hub-audio`,
//! sem hardware de áudio real (P10/SC-006). Cobrem FR-006/FR-007/FR-008.

use desktop_shell::agent_control::{self, StartError};
use std::os::unix::fs::PermissionsExt;
use std::process::Command;
use std::sync::Mutex;
use std::time::{Duration, Instant};

/// `detect_running()` enumera TODOS os processos do sistema operacional — estado global. Os
/// testes deste arquivo precisam rodar de forma serializada entre si (mesmo com o executor
/// paralelo padrão do `cargo test`), senão um processo fake "assistant-hub-audio" ainda vivo
/// de um teste vaza para outro em execução simultânea. Não afeta outros arquivos de teste.
static AGENT_PROCESS_TABLE_LOCK: Mutex<()> = Mutex::new(());

/// Cria, em um diretório temporário, um binário fake chamado exatamente `assistant-hub-audio`
/// (cópia do `sleep` do sistema) — necessário porque `detect_running()` casa por nome de
/// processo, e um `sleep` comum nunca seria confundido com o agent real.
fn fake_agent_binary_path() -> std::path::PathBuf {
    let sleep_path = which_sleep();
    let mut dir = std::env::temp_dir();
    dir.push(format!("desktop-shell-agent-fake-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let target = dir.join("assistant-hub-audio");
    std::fs::copy(&sleep_path, &target).expect("copiar binário fake do agent");
    let mut perms = std::fs::metadata(&target).unwrap().permissions();
    perms.set_mode(0o755);
    std::fs::set_permissions(&target, perms).unwrap();
    target
}

fn which_sleep() -> std::path::PathBuf {
    for candidate in ["/bin/sleep", "/usr/bin/sleep"] {
        if std::path::Path::new(candidate).exists() {
            return std::path::PathBuf::from(candidate);
        }
    }
    panic!("binário `sleep` não encontrado neste ambiente — necessário para simular o agent");
}

fn wait_until<F: Fn() -> bool>(timeout: Duration, check: F) -> bool {
    let start = Instant::now();
    while start.elapsed() < timeout {
        if check() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    false
}

#[test]
fn detect_running_finds_agent_started_outside_the_shell() {
    let _guard = AGENT_PROCESS_TABLE_LOCK
        .lock()
        .unwrap_or_else(|e| e.into_inner());
    let binary = fake_agent_binary_path();
    let mut external = Command::new(&binary)
        .arg("5")
        .spawn()
        .expect("spawnar o agent fake externamente");

    let detected = wait_until(Duration::from_secs(2), agent_control::detect_running);
    assert!(
        detected,
        "detect_running() deveria encontrar um processo assistant-hub-audio iniciado fora do shell (FR-006)"
    );

    let _ = external.kill();
    let _ = external.wait();
}

#[test]
fn start_returns_already_running_when_external_process_detected() {
    let _guard = AGENT_PROCESS_TABLE_LOCK
        .lock()
        .unwrap_or_else(|e| e.into_inner());
    let binary = fake_agent_binary_path();
    let mut external = Command::new(&binary)
        .arg("5")
        .spawn()
        .expect("spawnar o agent fake externamente");

    wait_until(Duration::from_secs(2), agent_control::detect_running);

    // Tentar iniciar pelo shell enquanto já há um processo externo em execução deve falhar
    // com um motivo específico (FR-008), não uma mensagem genérica.
    let result = agent_control::start(Command::new("true"));

    match result {
        Err(StartError::AlreadyRunning) => {}
        other => panic!("esperado StartError::AlreadyRunning, obtido {other:?}"),
    }

    let _ = external.kill();
    let _ = external.wait();
}

#[test]
fn start_with_missing_binary_reports_specific_error_not_generic() {
    let _guard = AGENT_PROCESS_TABLE_LOCK
        .lock()
        .unwrap_or_else(|e| e.into_inner());
    let result = agent_control::start(Command::new("binario-inexistente-assistant-hub-audio-fake"));

    let message = match result {
        Err(err) => err.to_string(),
        Ok(_) => panic!("start com binário ausente não deveria ter sucesso"),
    };

    assert!(
        message.contains("não encontrado"),
        "mensagem deve ser específica sobre o binário ausente, obtido: {message}"
    );
}
