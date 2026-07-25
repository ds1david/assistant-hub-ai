//! Cliente puro (sem Tauri) para os endpoints REST novos do `session-core`
//! (specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md) — mesmo padrão de
//! `session_core_client.rs`: nenhuma chamada de rede sai do webview, só deste módulo Rust.
//! Formas de wire espelham `ai.assistanthub.core.provider.*` (ver data-model.md). Este módulo
//! nunca loga nem retorna o valor completo de um segredo — só `secretRef` (não sensível) e
//! `SecretPreview.masked_value` (FR-014).

use serde::{Deserialize, Serialize};

use crate::session_core_client::ClientError;

// ---------------------------------------------------------------------------------------
// Wire types (formato exato devolvido/aceito pelo session-core)
// ---------------------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderAuthentication {
    pub mode: String,
    #[serde(rename = "secretRef", skip_serializing_if = "Option::is_none")]
    pub secret_ref: Option<String>,
    #[serde(rename = "headerName", skip_serializing_if = "Option::is_none")]
    pub header_name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderDefaults {
    pub model: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    #[serde(rename = "topP", skip_serializing_if = "Option::is_none")]
    pub top_p: Option<f64>,
    #[serde(rename = "maxTokens", skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<i64>,
    #[serde(rename = "timeoutMs")]
    pub timeout_ms: i64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Provider {
    pub id: String,
    pub label: String,
    #[serde(rename = "type")]
    pub provider_type: String,
    pub enabled: bool,
    #[serde(rename = "baseUrl")]
    pub base_url: String,
    pub authentication: ProviderAuthentication,
    pub defaults: ProviderDefaults,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConnectionTestResult {
    #[serde(rename = "providerId")]
    pub provider_id: String,
    pub success: bool,
    #[serde(rename = "errorType", skip_serializing_if = "Option::is_none")]
    pub error_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InvocationResult {
    #[serde(rename = "providerId")]
    pub provider_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    pub capability: String,
    #[serde(rename = "sessionId")]
    pub session_id: String,
    #[serde(rename = "channelId", skip_serializing_if = "Option::is_none")]
    pub channel_id: Option<String>,
    pub success: bool,
    #[serde(rename = "errorType", skip_serializing_if = "Option::is_none")]
    pub error_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(rename = "latencyMs")]
    pub latency_ms: i64,
    #[serde(rename = "occurredAt")]
    pub occurred_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SecretPreview {
    #[serde(rename = "providerId")]
    pub provider_id: String,
    #[serde(rename = "maskedValue", skip_serializing_if = "Option::is_none")]
    pub masked_value: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct SetEnabledRequest {
    enabled: bool,
}

#[derive(Debug, Clone, Serialize)]
struct InvokeRequest<'a> {
    #[serde(rename = "sessionId")]
    session_id: &'a str,
    #[serde(rename = "channelId", skip_serializing_if = "Option::is_none")]
    channel_id: Option<&'a str>,
    route: &'a str,
    capability: &'a str,
    input: &'a str,
}

// ---------------------------------------------------------------------------------------
// Cliente HTTP cru
// ---------------------------------------------------------------------------------------

pub struct AiProviderClient {
    base_url: String,
    http: reqwest::blocking::Client,
}

impl AiProviderClient {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            http: reqwest::blocking::Client::new(),
        }
    }

    pub fn list_providers(&self) -> Result<Vec<Provider>, ClientError> {
        let url = format!("{}/api/ai-providers", self.base_url);
        self.send_and_decode(self.http.get(url))
    }

    pub fn create_provider(&self, provider: &Provider) -> Result<Provider, ClientError> {
        let url = format!("{}/api/ai-providers", self.base_url);
        self.send_and_decode(self.http.post(url).json(provider))
    }

    pub fn update_provider(&self, id: &str, provider: &Provider) -> Result<Provider, ClientError> {
        let url = format!("{}/api/ai-providers/{id}", self.base_url);
        self.send_and_decode(self.http.put(url).json(provider))
    }

    pub fn set_enabled(&self, id: &str, enabled: bool) -> Result<Provider, ClientError> {
        let url = format!("{}/api/ai-providers/{id}/enabled", self.base_url);
        self.send_and_decode(self.http.patch(url).json(&SetEnabledRequest { enabled }))
    }

    pub fn delete_provider(&self, id: &str) -> Result<(), ClientError> {
        let url = format!("{}/api/ai-providers/{id}", self.base_url);
        let resp = self
            .http
            .delete(url)
            .send()
            .map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200..=299 => Ok(()),
            404 => Err(ClientError::NotFound),
            other => Err(ClientError::Http(other.to_string())),
        }
    }

    pub fn secret_preview(&self, id: &str) -> Result<SecretPreview, ClientError> {
        let url = format!("{}/api/ai-providers/{id}/secret-preview", self.base_url);
        self.send_and_decode(self.http.get(url))
    }

    pub fn test_connection(&self, id: &str) -> Result<ConnectionTestResult, ClientError> {
        let url = format!("{}/api/ai-providers/{id}/test", self.base_url);
        self.send_and_decode(self.http.post(url))
    }

    pub fn invoke(
        &self,
        session_id: &str,
        channel_id: Option<&str>,
        route: &str,
        capability: &str,
        input: &str,
    ) -> Result<InvocationResult, ClientError> {
        let url = format!("{}/api/ai-providers/invoke", self.base_url);
        let body = InvokeRequest {
            session_id,
            channel_id,
            route,
            capability,
            input,
        };
        self.send_and_decode(self.http.post(url).json(&body))
    }

    /// Cria se o `id` ainda não existir, ou atualiza (`PUT`) se já existir — usado pela tela de
    /// configuração de provedores (US3), que não distingue "novo" de "edição" na UI (FR-013).
    pub fn save_provider(&self, provider: &Provider) -> Result<Provider, ClientError> {
        match self.update_provider(&provider.id, provider) {
            Ok(updated) => Ok(updated),
            Err(ClientError::NotFound) => self.create_provider(provider),
            Err(other) => Err(other),
        }
    }

    fn send_and_decode<T: serde::de::DeserializeOwned>(
        &self,
        request: reqwest::blocking::RequestBuilder,
    ) -> Result<T, ClientError> {
        let resp = request.send().map_err(|e| ClientError::Network(e.to_string()))?;
        match resp.status().as_u16() {
            200..=299 => resp.json::<T>().map_err(|e| ClientError::Decode(e.to_string())),
            404 => Err(ClientError::NotFound),
            other => Err(ClientError::Http(other.to_string())),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provider_round_trips_through_serde_json() {
        let provider = Provider {
            id: "real-1".to_string(),
            label: "Real".to_string(),
            provider_type: "openai-compatible".to_string(),
            enabled: true,
            base_url: "http://fake.invalid".to_string(),
            authentication: ProviderAuthentication {
                mode: "bearer".to_string(),
                secret_ref: Some("env:FAKE_VAR".to_string()),
                header_name: None,
            },
            defaults: ProviderDefaults {
                model: "gpt-test".to_string(),
                temperature: None,
                top_p: None,
                max_tokens: None,
                timeout_ms: 3000,
            },
            capabilities: vec!["chat".to_string()],
        };

        let json = serde_json::to_string(&provider).unwrap();
        let decoded: Provider = serde_json::from_str(&json).unwrap();

        assert_eq!(decoded, provider);
        assert!(json.contains("\"baseUrl\""));
        assert!(json.contains("\"secretRef\""));
    }

    #[test]
    fn secret_preview_never_serializes_a_full_value_field() {
        // Trava de regressão: o único campo de segredo permitido é maskedValue (já mascarado
        // pelo servidor) — nenhum campo "value"/"secret"/"token" bruto existe nesta struct.
        let json = serde_json::to_string(&SecretPreview {
            provider_id: "real-1".to_string(),
            masked_value: Some("sk-...aB3f".to_string()),
        })
        .unwrap();

        assert!(!json.to_lowercase().contains("\"secret\""));
        assert!(!json.to_lowercase().contains("\"token\""));
        assert!(json.contains("maskedValue"));
    }

    #[test]
    fn connection_test_result_decodes_typed_error() {
        let json = r#"{"providerId":"real-1","success":false,"errorType":"AUTHENTICATION","message":"HTTP 401"}"#;

        let decoded: ConnectionTestResult = serde_json::from_str(json).unwrap();

        assert_eq!(decoded.error_type.as_deref(), Some("AUTHENTICATION"));
        assert!(!decoded.success);
    }
}
