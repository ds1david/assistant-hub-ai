//! Testes de integração (US1/US2) contra um servidor HTTP fake local — sem session-core real,
//! sem rede externa, sem GPU/hardware (P10/SC-006). Exercita `SessionCoreClient` de ponta a
//! ponta sobre TCP real (127.0.0.1), validando FR-001/FR-002/FR-004/FR-005/FR-009.

use desktop_shell::session_core_client::{
    channel_status_views, session_status_view, transcript_feed_entries, Connectivity,
    SessionCoreClient,
};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

/// Servidor HTTP/1.1 mínimo, só para estes testes: responde a um conjunto fixo de rotas
/// `(method, path) -> (status, body)`, uma request por conexão (`Connection: close`).
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
        404 => "404 Not Found",
        503 => "503 Service Unavailable",
        _ => "500 Internal Server Error",
    };
    let response = format!(
        "HTTP/1.1 {status_text}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.len(),
        body
    );
    let _ = stream.write_all(response.as_bytes());
}

const SESSION_JSON: &str = r#"{"id":"11111111-1111-1111-1111-111111111111","title":"quickstart","profileId":"demo","status":"ACTIVE","createdAt":"2026-01-01T00:00:00Z","startedAt":"2026-01-01T00:00:01Z","endedAt":null}"#;

const EVENTS_JSON: &str = r#"[
  {"id":"e1","sessionId":"s1","type":"transcript.final.v2","source":"transcription-service","occurredAt":"2026-01-01T00:00:02Z","payload":{"text":"ola do microfone"},"correlation":{"channelId":"mic-1","sourceType":"microphone","label":"Microfone"}},
  {"id":"e2","sessionId":"s1","type":"transcript.final.v2","source":"transcription-service","occurredAt":"2026-01-01T00:00:03Z","payload":{"text":"ola do sistema"},"correlation":{"channelId":"sys-1","sourceType":"system_audio","label":"Audio do sistema"}}
]"#;

#[test]
fn session_status_view_reports_connected_when_session_found() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/actuator/health"),
        (200, r#"{"status":"UP"}"#.to_string()),
    );
    routes.insert(
        ("GET", "/api/sessions/11111111-1111-1111-1111-111111111111"),
        (200, SESSION_JSON.to_string()),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let view = session_status_view(&client, "11111111-1111-1111-1111-111111111111");

    assert_eq!(view.connectivity, Connectivity::Connected);
    let session = view.session.expect("sessão deveria estar presente");
    assert_eq!(session.title, "quickstart");
    assert_eq!(session.status, "ACTIVE");
}

#[test]
fn session_status_view_reports_connected_with_no_session_when_not_found() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/actuator/health"),
        (200, r#"{"status":"UP"}"#.to_string()),
    );
    // Nenhuma rota para /api/sessions/{id} -> cai no default 404 do servidor fake.
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let view = session_status_view(&client, "id-inexistente");

    assert_eq!(view.connectivity, Connectivity::Connected);
    assert!(
        view.session.is_none(),
        "sessão inexistente não é erro de conectividade (FR-009)"
    );
}

#[test]
fn session_status_view_reports_disconnected_when_health_is_down() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/actuator/health"),
        (503, r#"{"status":"DOWN"}"#.to_string()),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let view = session_status_view(&client, "qualquer-id");

    assert_eq!(view.connectivity, Connectivity::Disconnected);
    assert!(
        view.session.is_none(),
        "session-core indisponível nunca deve expor dado desatualizado como corrente (FR-009)"
    );
}

#[test]
fn session_status_view_reports_disconnected_when_server_unreachable() {
    // Nenhum servidor fake sobe nesta porta — simula session-core totalmente fora do ar.
    let client = SessionCoreClient::new("http://127.0.0.1:1".to_string());

    let view = session_status_view(&client, "qualquer-id");

    assert_eq!(view.connectivity, Connectivity::Disconnected);
}

#[test]
fn channel_status_views_over_http_preserves_channel_metadata() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/api/sessions/s1/events"),
        (200, EVENTS_JSON.to_string()),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let events = client.get_events("s1").expect("get_events deve funcionar");
    let channels = channel_status_views(&events);

    assert_eq!(channels.len(), 2);
    assert!(channels
        .iter()
        .any(|c| c.channel_id == "mic-1" && c.source_type.as_deref() == Some("microphone")));
    assert!(channels
        .iter()
        .any(|c| c.channel_id == "sys-1" && c.source_type.as_deref() == Some("system_audio")));
}

#[test]
fn transcript_feed_entries_over_http_preserves_order_and_channel_identity() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/api/sessions/s1/events"),
        (200, EVENTS_JSON.to_string()),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let events = client.get_events("s1").expect("get_events deve funcionar");
    let feed = transcript_feed_entries(&events);

    assert_eq!(feed.len(), 2);
    assert_eq!(feed[0].channel_id.as_deref(), Some("mic-1"));
    assert_eq!(feed[0].text, "ola do microfone");
    assert_eq!(feed[1].channel_id.as_deref(), Some("sys-1"));
    assert_eq!(feed[1].text, "ola do sistema");
}

#[test]
fn list_sessions_returns_array() {
    let mut routes = HashMap::new();
    routes.insert(
        ("GET", "/api/sessions"),
        (200, format!("[{SESSION_JSON}]")),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let sessions = client.list_sessions().expect("list_sessions");
    assert_eq!(sessions.len(), 1);
    assert_eq!(sessions[0].title, "quickstart");
}

#[test]
fn list_sessions_empty_ok() {
    let mut routes = HashMap::new();
    routes.insert(("GET", "/api/sessions"), (200, "[]".to_string()));
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let sessions = client.list_sessions().expect("list empty");
    assert!(sessions.is_empty());
}

#[test]
fn create_session_posts_and_returns_body() {
    let mut routes = HashMap::new();
    routes.insert(
        ("POST", "/api/sessions"),
        (201, SESSION_JSON.to_string()),
    );
    let base_url = start_fake_server(routes);
    let client = SessionCoreClient::new(base_url);

    let session = client
        .create_session("Sessão local", "interview-technical")
        .expect("create_session");
    assert_eq!(session.id, "11111111-1111-1111-1111-111111111111");
}
