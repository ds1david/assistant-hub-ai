// Wrappers tipados em torno de `invoke` do Tauri — nunca `fetch` direto no webview
// (plan.md § Structure Decision). Os tipos abaixo espelham as structs Rust serializáveis de
// apps/desktop-shell/src-tauri/src/{session_core_client,agent_control}.rs (camelCase via
// `#[serde(rename_all = "camelCase")]`).
import { invoke } from "@tauri-apps/api/core";

export type Connectivity = "Connected" | "Disconnected" | { Error: string };

export interface SessionSummary {
  id: string;
  title: string;
  profileId: string;
  status: string;
  createdAt: string | null;
  startedAt: string | null;
  endedAt: string | null;
}

export interface SessionStatusView {
  connectivity: Connectivity;
  session: SessionSummary | null;
}

export interface ChannelStatusView {
  channelId: string;
  sourceType: string | null;
  label: string | null;
  deviceIndex: string | null;
  deviceName: string | null;
  deviceEndpointId: string | null;
  lastEventAt: string | null;
  eventCount: number;
}

export interface SessionStatusResponse {
  status: SessionStatusView;
  channels: ChannelStatusView[];
}

export type FeedEntryKind = "Partial" | "Final";

export interface TranscriptFeedEntry {
  eventId: string;
  channelId: string | null;
  sourceType: string | null;
  label: string | null;
  text: string;
  kind: FeedEntryKind;
  occurredAt: string;
}

export type ControlMode = "Direct" | "Guided";

export interface AgentStatus {
  running: boolean;
  controlMode: ControlMode;
  guidanceCommand: string;
  lastError: string | null;
}

export interface ShellConfig {
  sessionCoreBaseUrl: string;
  windowState?: { width: number; height: number; x?: number; y?: number };
}

export function getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
  return invoke("get_session_status", { sessionId });
}

export function getTranscriptFeed(sessionId: string): Promise<TranscriptFeedEntry[]> {
  return invoke("get_transcript_feed", { sessionId });
}

export function getAgentStatus(): Promise<AgentStatus> {
  return invoke("get_agent_status");
}

export function startAgent(sessionId: string, profilePath: string): Promise<AgentStatus> {
  return invoke("start_agent", { sessionId, profilePath });
}

export function stopAgent(): Promise<void> {
  return invoke("stop_agent");
}

export function getShellConfig(): Promise<ShellConfig> {
  return invoke("get_shell_config");
}

// ---------------------------------------------------------------------------------------
// AI Provider Hub (R6, issue #37, US3) — espelha ai.assistanthub.core.provider.* do
// session-core (ver specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md).
// ---------------------------------------------------------------------------------------

export type AuthenticationMode = "none" | "bearer" | "api-key";

export interface ProviderAuthentication {
  mode: AuthenticationMode;
  secretRef?: string | null;
  headerName?: string | null;
}

export interface ProviderDefaults {
  model: string;
  temperature?: number | null;
  topP?: number | null;
  maxTokens?: number | null;
  timeoutMs: number;
}

export type ProviderType = "openai-compatible" | "anthropic" | "gemini" | "custom-http";

export interface Provider {
  id: string;
  label: string;
  type: ProviderType;
  enabled: boolean;
  baseUrl: string;
  authentication: ProviderAuthentication;
  defaults: ProviderDefaults;
  capabilities: string[];
}

export type InvocationErrorType =
  | "AUTHENTICATION"
  | "MODEL_NOT_FOUND"
  | "TIMEOUT"
  | "RATE_LIMITED"
  | "GENERIC"
  | "CAPABILITY_MISMATCH";

export interface ConnectionTestResult {
  providerId: string;
  success: boolean;
  errorType?: InvocationErrorType | null;
  message?: string | null;
}

export interface InvocationResult {
  providerId: string;
  model?: string | null;
  capability: string;
  sessionId: string;
  channelId?: string | null;
  success: boolean;
  errorType?: InvocationErrorType | null;
  output?: string | null;
  message?: string | null;
  latencyMs: number;
  occurredAt: string;
}

export interface SecretPreview {
  providerId: string;
  maskedValue?: string | null;
}

export function listAiProviders(): Promise<Provider[]> {
  return invoke("list_ai_providers");
}

export function saveAiProvider(provider: Provider): Promise<Provider> {
  return invoke("save_ai_provider", { provider });
}

export function setAiProviderEnabled(providerId: string, enabled: boolean): Promise<Provider> {
  return invoke("set_ai_provider_enabled", { providerId, enabled });
}

export function deleteAiProvider(providerId: string): Promise<void> {
  return invoke("delete_ai_provider", { providerId });
}

export function getAiProviderSecretPreview(providerId: string): Promise<SecretPreview> {
  return invoke("get_ai_provider_secret_preview", { providerId });
}

export function testAiProviderConnection(providerId: string): Promise<ConnectionTestResult> {
  return invoke("test_ai_provider_connection", { providerId });
}

export function invokeAiProvider(
  sessionId: string,
  route: string,
  capability: string,
  input: string,
  channelId?: string,
): Promise<InvocationResult> {
  return invoke("invoke_ai_provider", { sessionId, channelId: channelId ?? null, route, capability, input });
}
