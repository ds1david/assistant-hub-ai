//! Cliente puro (sem Tauri) para a API REST já publicada do `session-core`. O shell é
//! estritamente um consumidor — nenhuma escrita de sessão/evento é feita aqui (FR-010).
//! Formas de wire (ConversationSession/HubEvent) espelham
//! `services/session-core/src/main/java/ai/assistanthub/core/session/SessionController.java`
//! e `ai/assistanthub/sdk/HubEvent.java` (ver data-model.md).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;

// ---------------------------------------------------------------------------------------
// Wire types (formato exato devolvido pelo session-core)
// ---------------------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationSession {
    pub id: String,
    pub title: String,
    #[serde(rename = "profileId")]
    pub profile_id: String,
    pub status: String,
    #[serde(rename = "createdAt")]
    pub created_at: Option<String>,
    #[serde(rename = "startedAt")]
    pub started_at: Option<String>,
    #[serde(rename = "endedAt")]
    pub ended_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HubEvent {
    pub id: String,
    #[serde(rename = "sessionId")]
    pub session_id: String,
    #[serde(rename = "type")]
    pub event_type: String,
    pub source: String,
    #[serde(rename = "occurredAt")]
    pub occurred_at: String,
    #[serde(default)]
    pub payload: serde_json::Map<String, serde_json::Value>,
    #[serde(default)]
    pub correlation: HashMap<String, String>,
}

impl HubEvent {
    fn correlation_get(&self, key: &str) -> Option<String> {
        self.correlation
            .get(key)
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty())
    }

    fn channel_id(&self) -> Option<String> {
        self.correlation_get("channelId")
    }
}

// ---------------------------------------------------------------------------------------
// Erros
// ---------------------------------------------------------------------------------------

#[derive(Debug)]
pub enum ClientError {
    NotFound,
    Http(String),
    Network(String),
    Decode(String),
}

impl fmt::Display for ClientError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ClientError::NotFound => write!(f, "recurso não encontrado"),
            ClientError::Http(msg) => write!(f, "resposta HTTP inesperada: {msg}"),
            ClientError::Network(msg) => write!(f, "falha de rede: {msg}"),
            ClientError::Decode(msg) => write!(f, "falha ao decodificar resposta: {msg}"),
        }
    }
}

impl std::error::Error for ClientError {}

// ---------------------------------------------------------------------------------------
// Cliente HTTP cru (T008)
// ---------------------------------------------------------------------------------------

pub struct SessionCoreClient {
    base_url: String,
    http: reqwest::blocking::Client,
}

impl SessionCoreClient {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            http: reqwest::blocking::Client::new(),
        }
    }

    pub fn get_session(&self, session_id: &str) -> Result<ConversationSession, ClientError> {
        let url = format!("{}/api/sessions/{session_id}", self.base_url);
        let resp = self
            .http
            .get(url)
            .send()
            .map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200 => resp
                .json::<ConversationSession>()
                .map_err(|e| ClientError::Decode(e.to_string())),
            404 => Err(ClientError::NotFound),
            other => Err(ClientError::Http(other.to_string())),
        }
    }

    /// Cria sessão no session-core (necessário para o agent/transcript e o assistente automático
    /// compartilharem o mesmo `sessionId`). Escrita deliberada — o restante do cliente permanece
    /// consumidor de eventos/status.
    pub fn create_session(
        &self,
        title: &str,
        profile_id: &str,
    ) -> Result<ConversationSession, ClientError> {
        let url = format!("{}/api/sessions", self.base_url);
        let body = serde_json::json!({
            "title": title,
            "profileId": profile_id,
            "metadata": {}
        });
        let resp = self
            .http
            .post(url)
            .json(&body)
            .send()
            .map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200 | 201 => resp
                .json::<ConversationSession>()
                .map_err(|e| ClientError::Decode(e.to_string())),
            other => Err(ClientError::Http(other.to_string())),
        }
    }

    /// Lista sessões conhecidas (`GET /api/sessions`, FR-026).
    pub fn list_sessions(&self) -> Result<Vec<ConversationSession>, ClientError> {
        let url = format!("{}/api/sessions", self.base_url);
        let resp = self
            .http
            .get(url)
            .send()
            .map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200 => resp
                .json::<Vec<ConversationSession>>()
                .map_err(|e| ClientError::Decode(e.to_string())),
            other => Err(ClientError::Http(other.to_string())),
        }
    }

    pub fn get_events(&self, session_id: &str) -> Result<Vec<HubEvent>, ClientError> {
        let url = format!("{}/api/sessions/{session_id}/events", self.base_url);
        let resp = self
            .http
            .get(url)
            .send()
            .map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200 => resp
                .json::<Vec<HubEvent>>()
                .map_err(|e| ClientError::Decode(e.to_string())),
            404 => Err(ClientError::NotFound),
            other => Err(ClientError::Http(other.to_string())),
        }
    }

    pub fn get_health(&self) -> HealthState {
        let url = format!("{}/actuator/health", self.base_url);
        match self.http.get(url).send() {
            Ok(resp) if resp.status().is_success() => HealthState::Up,
            _ => HealthState::Down,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HealthState {
    Up,
    Down,
}

// ---------------------------------------------------------------------------------------
// SessionStatusView (US1 / FR-001 / FR-009) — T014
// ---------------------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Serialize)]
pub enum Connectivity {
    Connected,
    Disconnected,
    Error(String),
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct SessionSummary {
    pub id: String,
    pub title: String,
    #[serde(rename = "profileId")]
    pub profile_id: String,
    pub status: String,
    #[serde(rename = "createdAt")]
    pub created_at: Option<String>,
    #[serde(rename = "startedAt")]
    pub started_at: Option<String>,
    #[serde(rename = "endedAt")]
    pub ended_at: Option<String>,
}

impl From<ConversationSession> for SessionSummary {
    fn from(s: ConversationSession) -> Self {
        Self {
            id: s.id,
            title: s.title,
            profile_id: s.profile_id,
            status: s.status,
            created_at: s.created_at,
            started_at: s.started_at,
            ended_at: s.ended_at,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionStatusView {
    pub connectivity: Connectivity,
    /// `None` cobre tanto "sem sessão ativa" quanto "sessão não encontrada" — a spec (FR-001,
    /// edge cases) trata os dois como "sem sessão ativa" do ponto de vista do operador; a
    /// distinção de conectividade fica só em `connectivity` (FR-009).
    pub session: Option<SessionSummary>,
}

/// Combina `get_health` + `get_session`, nunca expondo dado obsoleto como se fosse corrente
/// (FR-009): se o session-core está fora do ar, `connectivity = Disconnected` e nenhum dado
/// de sessão é retornado, mesmo que uma chamada anterior tenha tido sucesso.
pub fn session_status_view(client: &SessionCoreClient, session_id: &str) -> SessionStatusView {
    if client.get_health() == HealthState::Down {
        return SessionStatusView {
            connectivity: Connectivity::Disconnected,
            session: None,
        };
    }

    match client.get_session(session_id) {
        Ok(session) => SessionStatusView {
            connectivity: Connectivity::Connected,
            session: Some(session.into()),
        },
        Err(ClientError::NotFound) => SessionStatusView {
            connectivity: Connectivity::Connected,
            session: None,
        },
        Err(other) => SessionStatusView {
            connectivity: Connectivity::Error(other.to_string()),
            session: None,
        },
    }
}

// ---------------------------------------------------------------------------------------
// ChannelStatusView (US1 / FR-002) — T015
// ---------------------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ChannelStatusView {
    pub channel_id: String,
    pub source_type: Option<String>,
    pub label: Option<String>,
    pub device_index: Option<String>,
    pub device_name: Option<String>,
    pub device_endpoint_id: Option<String>,
    pub last_event_at: Option<String>,
    pub event_count: usize,
}

/// Agrupa eventos por `channelId` (nunca por `label`, edge case de `label` duplicado entre
/// canais — spec.md § Edge Cases), preservando `sourceType`/`label`/`device`.
pub fn channel_status_views(events: &[HubEvent]) -> Vec<ChannelStatusView> {
    let mut order: Vec<String> = Vec::new();
    let mut by_channel: HashMap<String, ChannelStatusView> = HashMap::new();

    for event in events {
        let Some(channel_id) = event.channel_id() else {
            continue; // evento sem correlation/channelId — nada a agrupar (edge case)
        };

        let entry = by_channel.entry(channel_id.clone()).or_insert_with(|| {
            order.push(channel_id.clone());
            ChannelStatusView {
                channel_id: channel_id.clone(),
                source_type: None,
                label: None,
                device_index: None,
                device_name: None,
                device_endpoint_id: None,
                last_event_at: None,
                event_count: 0,
            }
        });

        entry.event_count += 1;
        entry.source_type = entry
            .source_type
            .clone()
            .or_else(|| event.correlation_get("sourceType"));
        entry.label = entry
            .label
            .clone()
            .or_else(|| event.correlation_get("label"));
        entry.device_index = entry
            .device_index
            .clone()
            .or_else(|| event.correlation_get("device.index"));
        entry.device_name = entry
            .device_name
            .clone()
            .or_else(|| event.correlation_get("device.name"));
        entry.device_endpoint_id = entry
            .device_endpoint_id
            .clone()
            .or_else(|| event.correlation_get("device.endpointId"));

        if entry
            .last_event_at
            .as_deref()
            .map(|current| event.occurred_at.as_str() > current)
            .unwrap_or(true)
        {
            entry.last_event_at = Some(event.occurred_at.clone());
        }
    }

    order
        .into_iter()
        .filter_map(|id| by_channel.remove(&id))
        .collect()
}

// ---------------------------------------------------------------------------------------
// TranscriptFeedEntry (US2 / FR-003 / FR-004 / FR-005) — T021
// ---------------------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum FeedEntryKind {
    Partial,
    Final,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TranscriptFeedEntry {
    pub event_id: String,
    pub channel_id: Option<String>,
    pub source_type: Option<String>,
    pub label: Option<String>,
    pub text: String,
    pub kind: FeedEntryKind,
    pub occurred_at: String,
}

/// Filtra eventos de transcrição (`transcript.partial.v2`/`transcript.final.v2`), mapeia para
/// `TranscriptFeedEntry`, deduplica por `event_id` (para merges seguros entre polls sucessivos)
/// e ordena cronologicamente — nunca combina texto de canais diferentes em uma única entrada
/// (FR-004).
pub fn transcript_feed_entries(events: &[HubEvent]) -> Vec<TranscriptFeedEntry> {
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut entries: Vec<TranscriptFeedEntry> = events
        .iter()
        .filter_map(|event| {
            let kind = match event.event_type.as_str() {
                "transcript.partial.v2" => FeedEntryKind::Partial,
                "transcript.final.v2" => FeedEntryKind::Final,
                _ => return None,
            };
            if !seen.insert(event.id.clone()) {
                return None; // já visto (dedup entre polls)
            }
            let text = event
                .payload
                .get("text")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            Some(TranscriptFeedEntry {
                event_id: event.id.clone(),
                channel_id: event.channel_id(),
                source_type: event.correlation_get("sourceType"),
                label: event.correlation_get("label"),
                text,
                kind,
                occurred_at: event.occurred_at.clone(),
            })
        })
        .collect();

    entries.sort_by(|a, b| a.occurred_at.cmp(&b.occurred_at));
    entries
}

#[cfg(test)]
mod tests {
    use super::*;

    fn event(
        id: &str,
        channel_id: &str,
        source_type: &str,
        label: &str,
        occurred_at: &str,
        text: &str,
        event_type: &str,
    ) -> HubEvent {
        let mut correlation = HashMap::new();
        correlation.insert("channelId".to_string(), channel_id.to_string());
        correlation.insert("sourceType".to_string(), source_type.to_string());
        correlation.insert("label".to_string(), label.to_string());

        let mut payload = serde_json::Map::new();
        payload.insert(
            "text".to_string(),
            serde_json::Value::String(text.to_string()),
        );

        HubEvent {
            id: id.to_string(),
            session_id: "s1".to_string(),
            event_type: event_type.to_string(),
            source: "transcription-service".to_string(),
            occurred_at: occurred_at.to_string(),
            payload,
            correlation,
        }
    }

    #[test]
    fn channel_status_views_groups_by_channel_id_not_label() {
        let events = vec![
            event(
                "e1",
                "mic-1",
                "microphone",
                "Canal",
                "2026-01-01T00:00:01Z",
                "oi",
                "transcript.final.v2",
            ),
            event(
                "e2",
                "sys-1",
                "system_audio",
                "Canal",
                "2026-01-01T00:00:02Z",
                "oi2",
                "transcript.final.v2",
            ),
        ];

        let channels = channel_status_views(&events);

        assert_eq!(
            channels.len(),
            2,
            "dois channelId diferentes, mesmo label, não podem virar um só canal"
        );
        assert_eq!(channels[0].channel_id, "mic-1");
        assert_eq!(channels[0].source_type.as_deref(), Some("microphone"));
        assert_eq!(channels[1].channel_id, "sys-1");
        assert_eq!(channels[1].event_count, 1);
    }

    #[test]
    fn channel_status_views_ignores_events_without_channel_id() {
        let mut legacy = event(
            "e1",
            "",
            "",
            "",
            "2026-01-01T00:00:01Z",
            "oi",
            "transcript.final.v2",
        );
        legacy.correlation.clear();

        let channels = channel_status_views(&[legacy]);

        assert!(channels.is_empty());
    }

    #[test]
    fn transcript_feed_entries_orders_chronologically_across_channels() {
        let events = vec![
            event(
                "e2",
                "sys-1",
                "system_audio",
                "Sistema",
                "2026-01-01T00:00:05Z",
                "segundo",
                "transcript.final.v2",
            ),
            event(
                "e1",
                "mic-1",
                "microphone",
                "Microfone",
                "2026-01-01T00:00:01Z",
                "primeiro",
                "transcript.final.v2",
            ),
        ];

        let feed = transcript_feed_entries(&events);

        assert_eq!(feed.len(), 2);
        assert_eq!(feed[0].text, "primeiro");
        assert_eq!(feed[0].channel_id.as_deref(), Some("mic-1"));
        assert_eq!(feed[1].text, "segundo");
        assert_eq!(feed[1].channel_id.as_deref(), Some("sys-1"));
    }

    #[test]
    fn transcript_feed_entries_never_mixes_channels_in_one_entry() {
        let events = vec![
            event(
                "e1",
                "mic-1",
                "microphone",
                "Microfone",
                "2026-01-01T00:00:01Z",
                "do microfone",
                "transcript.final.v2",
            ),
            event(
                "e2",
                "sys-1",
                "system_audio",
                "Sistema",
                "2026-01-01T00:00:02Z",
                "do sistema",
                "transcript.final.v2",
            ),
        ];

        let feed = transcript_feed_entries(&events);

        for entry in &feed {
            assert!(
                !entry.text.contains("do microfone")
                    || entry.channel_id.as_deref() == Some("mic-1")
            );
            assert!(
                !entry.text.contains("do sistema") || entry.channel_id.as_deref() == Some("sys-1")
            );
        }
    }

    #[test]
    fn transcript_feed_entries_ignores_non_transcript_events() {
        let events = vec![event(
            "e1",
            "mic-1",
            "microphone",
            "Microfone",
            "2026-01-01T00:00:01Z",
            "oi",
            "session.status.v1",
        )];

        let feed = transcript_feed_entries(&events);

        assert!(feed.is_empty());
    }

    #[test]
    fn transcript_feed_entries_deduplicates_by_event_id_across_merged_polls() {
        let first_poll = event(
            "e1",
            "mic-1",
            "microphone",
            "Microfone",
            "2026-01-01T00:00:01Z",
            "oi",
            "transcript.final.v2",
        );
        let second_poll_repeat = first_poll.clone();
        let events = vec![first_poll, second_poll_repeat];

        let feed = transcript_feed_entries(&events);

        assert_eq!(feed.len(), 1);
    }
}
