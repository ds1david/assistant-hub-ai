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
