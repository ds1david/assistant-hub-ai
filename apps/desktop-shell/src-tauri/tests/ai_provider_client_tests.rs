//! Testes de integração (US3) contra um servidor HTTP fake local — sem session-core real, sem
//! rede externa (P10/SC-003). Exercita `AiProviderClient` de ponta a ponta sobre TCP real
//! (127.0.0.1), validando parsing/mapeamento dos tipos de
//! specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md.

use desktop_shell::ai_provider_client::AiProviderClient;
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

/// Servidor HTTP/1.1 mínimo, só para estes testes — mesmo padrão de session_core_client_tests.rs.
fn start_fake_server(routes: HashMap<(&'static str, &'static str), (u16, String)>) -> String {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind do servidor fake");
    let port = listener.local_addr().unwrap().port();

    thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(stream) = stream else { continue };
            handle_connection(stream, &routes);
        }
    });

    format!("http://127.0.0.1:{port}")
}

fn handle_connection(
    mut stream: TcpStream,
    routes: &HashMap<(&'static str, &'static str), (u16, String)>,
) {
    let mut reader = BufReader::new(stream.try_clone().expect("clone do socket"));
    let mut request_line = String::new();
    if reader.read_line(&mut request_line).unwrap_or(0) == 0 {
        return;
    }
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line).unwrap_or(0) == 0 || line == "\r\n" {
            break;
        }
    }

    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("");
    let path = parts.next().unwrap_or("");

    let (status, body) = routes
        .iter()
        .find(|((m, p), _)| *m == method && *p == path)
        .map(|(_, v)| v.clone())
        .unwrap_or((404, "{}".to_string()));

    let status_text = match status {
        200 => "200 OK",
        201 => "201 Created",
        204 => "204 No Content",
        404 => "404 Not Found",
        409 => "409 Conflict",
        _ => "500 Internal Server Error",
    };
    let response = format!(
        "HTTP/1.1 {status_text}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.len(),
        body
    );
    let _ = stream.write_all(response.as_bytes());
}

const PROVIDER_JSON: &str = r#"{"id":"real-1","label":"Real","type":"openai-compatible","enabled":true,"baseUrl":"http://fake.invalid","authentication":{"mode":"bearer","secretRef":"env:FAKE_VAR"},"defaults":{"model":"gpt-test","timeoutMs":3000},"capabilities":["chat"]}"#;

#[test]
fn list_providers_parses_the_full_shape() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/api/ai-providers"),
        (200, format!("[{PROVIDER_JSON}]")),
    );
    let client = AiProviderClient::new(start_fake_server(routes));

    let providers = client.list_providers().expect("list deve funcionar");

    assert_eq!(providers.len(), 1);
    assert_eq!(providers[0].id, "real-1");
    assert_eq!(providers[0].provider_type, "openai-compatible");
    assert_eq!(providers[0].authentication.secret_ref.as_deref(), Some("env:FAKE_VAR"));
}

#[test]
fn create_provider_sends_and_decodes() {
    let mut routes = HashMap::new();
    routes.insert(("POST", "/api/ai-providers"), (201, PROVIDER_JSON.to_string()));
    let client = AiProviderClient::new(start_fake_server(routes));
    let provider = serde_json::from_str(PROVIDER_JSON).expect("fixture válida");

    let created = client.create_provider(&provider).expect("create deve funcionar");

    assert_eq!(created.id, "real-1");
}

#[test]
fn test_connection_decodes_typed_error() {
    let mut routes = HashMap::new();
    routes.insert(
        ("POST", "/api/ai-providers/real-1/test"),
        (
            200,
            r#"{"providerId":"real-1","success":false,"errorType":"TIMEOUT","message":"timeout apos 3000ms"}"#
                .to_string(),
        ),
    );
    let client = AiProviderClient::new(start_fake_server(routes));

    let result = client.test_connection("real-1").expect("test deve funcionar");

    assert!(!result.success);
    assert_eq!(result.error_type.as_deref(), Some("TIMEOUT"));
}

#[test]
fn invoke_decodes_provenance_metadata() {
    let mut routes = HashMap::new();
    routes.insert(
        ("POST", "/api/ai-providers/invoke"),
        (
            200,
            r#"{"providerId":"real-1","model":"gpt-test","capability":"chat","sessionId":"s1","channelId":"mic-1","success":true,"output":"ola de volta","latencyMs":120,"occurredAt":"2026-01-01T00:00:00Z"}"#
                .to_string(),
        ),
    );
    let client = AiProviderClient::new(start_fake_server(routes));

    let result = client
        .invoke("s1", Some("mic-1"), "chat-route", "chat", "ola")
        .expect("invoke deve funcionar");

    assert!(result.success);
    assert_eq!(result.provider_id, "real-1");
    assert_eq!(result.output.as_deref(), Some("ola de volta"));
    assert_eq!(result.latency_ms, 120);
}

#[test]
fn secret_preview_never_carries_the_full_secret() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/api/ai-providers/real-1/secret-preview"),
        (
            200,
            r#"{"providerId":"real-1","maskedValue":"sk-...aB3f"}"#.to_string(),
        ),
    );
    let client = AiProviderClient::new(start_fake_server(routes));

    let preview = client.secret_preview("real-1").expect("secret-preview deve funcionar");

    assert_eq!(preview.masked_value.as_deref(), Some("sk-...aB3f"));
}

#[test]
fn save_provider_falls_back_to_create_when_update_reports_not_found() {
    let mut routes = HashMap::new();
    // Nenhuma rota PUT registrada -> 404 default, forçando o fallback para POST.
    routes.insert(("POST", "/api/ai-providers"), (201, PROVIDER_JSON.to_string()));
    let client = AiProviderClient::new(start_fake_server(routes));
    let provider = serde_json::from_str(PROVIDER_JSON).expect("fixture válida");

    let saved = client.save_provider(&provider).expect("save deve funcionar via fallback");

    assert_eq!(saved.id, "real-1");
}

#[test]
fn delete_provider_reports_not_found() {
    let routes = HashMap::new(); // nenhuma rota -> 404 default do servidor fake
    let client = AiProviderClient::new(start_fake_server(routes));

    let result = client.delete_provider("does-not-exist");

    assert!(result.is_err());
}
