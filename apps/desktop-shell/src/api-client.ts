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

/** Optional prosody on Final events (023 FR-007); absent on partials / legacy feeds. */
export interface TranscriptProsody {
  questionScore?: number;
  contour?: string;
  f0EndSlopeSemitones?: number;
}

export interface TranscriptFeedEntry {
  eventId: string;
  channelId: string | null;
  sourceType: string | null;
  label: string | null;
  text: string;
  kind: FeedEntryKind;
  occurredAt: string;
  prosody?: TranscriptProsody | null;
}

export type ControlMode = "Direct" | "Guided";

export type AgentSessionSource = "cmdline" | "managed" | "unknown";

/** 025 — origem do binário do agent (sidecar / config / PATH). */
export type BinarySource = "sidecar" | "config" | "path" | "missing";

export interface AgentStatus {
  running: boolean;
  controlMode: ControlMode;
  guidanceCommand: string;
  lastError: string | null;
  /** Sessão resolvida do agent (cmdline → managed → null). */
  agentSessionId: string | null;
  agentSessionSource: AgentSessionSource;
  /** 025 — path resolvido; null se missing. */
  binaryPath?: string | null;
  binarySource?: BinarySource;
  agentVersion?: string | null;
  healthy?: boolean;
}

export interface ShellConfig {
  sessionCoreBaseUrl: string;
  windowState?: { width: number; height: number; x?: number; y?: number };
  /** Override local do binário do agent (025). */
  audioAgentBin?: string | null;
}

export function getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
  return invoke("get_session_status", { sessionId });
}

/** Cria sessão no session-core — id deve ser o mesmo usado pelo agent WASAPI. */
export function createSession(title: string, profileId: string): Promise<SessionSummary> {
  return invoke("create_session", { title, profileId });
}

/** Lista sessões conhecidas (`GET /api/sessions`, FR-026). */
export function listSessions(): Promise<SessionSummary[]> {
  return invoke("list_sessions");
}

export function getTranscriptFeed(sessionId: string): Promise<TranscriptFeedEntry[]> {
  return invoke("get_transcript_feed", { sessionId });
}

export interface MemorySearchHit {
  eventId: string;
  type: string;
  text: string;
  sourceType?: string | null;
  channelId?: string | null;
  occurredAt: string;
}

export interface MemoryItem {
  kind: string;
  text: string;
  eventId: string;
  sourceType?: string | null;
  occurredAt: string;
}

export function searchSessionMemory(
  sessionId: string,
  q?: string | null,
  sourceType?: string | null,
  limit?: number | null,
): Promise<MemorySearchHit[]> {
  return invoke("search_session_memory", {
    sessionId,
    q: q ?? null,
    sourceType: sourceType ?? null,
    limit: limit ?? null,
  });
}

export function getSessionMemoryItems(sessionId: string): Promise<MemoryItem[]> {
  return invoke("get_session_memory_items", { sessionId });
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
  | "CAPABILITY_MISMATCH"
  | "CIRCUIT_OPEN";

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
  /** Server-resolved channel origin (microphone | system); null when invoke has no channel. */
  sourceType?: string | null;
  success: boolean;
  errorType?: InvocationErrorType | null;
  output?: string | null;
  message?: string | null;
  latencyMs: number;
  occurredAt: string;
  /** 027 — only when provider reports usage; never invented. */
  promptTokens?: number | null;
  completionTokens?: number | null;
  totalTokens?: number | null;
}

export interface ModelInfo {
  id: string;
  ownedBy?: string | null;
}

export interface ModelsDiscoveryResult {
  providerId: string;
  success: boolean;
  errorType?: InvocationErrorType | null;
  message?: string | null;
  models: ModelInfo[];
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

/** Store secret in OS/memory store; returns `os:…` secretRef. Value is never returned. */
export function secretStorePut(providerId: string, value: string): Promise<string> {
  return invoke("secret_store_put", { providerId, value });
}

export function secretStoreDelete(providerId: string): Promise<void> {
  return invoke("secret_store_delete", { providerId });
}

export function secretStoreListIds(): Promise<string[]> {
  return invoke("secret_store_list_ids");
}

export function secretStoreHas(providerId: string): Promise<boolean> {
  return invoke("secret_store_has", { providerId });
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
