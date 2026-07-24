// Bootstrap do shell: liga os três painéis (US1/US2/US3) aos comandos Tauri via api-client,
// com polling conforme plan.md § Performance Goals (~5s status/canais, ~2s feed).
import {
  getAgentStatus,
  getSessionStatus,
  getTranscriptFeed,
  startAgent,
  stopAgent,
} from "./api-client";
import { renderSessionStatus } from "./session-status";
import { renderTranscriptFeed } from "./transcript-feed";
import { renderAgentPanel } from "./agent-panel";

const STATUS_POLL_MS = 5000;
const FEED_POLL_MS = 2000;
const DEFAULT_PROFILE_PATH = "perfil.yaml";

let activeSessionId: string | null = null;

function sessionStatusContainer(): HTMLElement {
  return document.getElementById("session-status") as HTMLElement;
}

function transcriptFeedContainer(): HTMLElement {
  return document.getElementById("transcript-feed") as HTMLElement;
}

function agentPanelContainer(): HTMLElement {
  return document.getElementById("agent-panel") as HTMLElement;
}

async function pollSessionStatus(): Promise<void> {
  if (!activeSessionId) return;
  try {
    const response = await getSessionStatus(activeSessionId);
    renderSessionStatus(sessionStatusContainer(), response);
  } catch (error) {
    console.error("Falha ao consultar status da sessão", error);
  }
}

async function pollTranscriptFeed(): Promise<void> {
  if (!activeSessionId) return;
  try {
    const entries = await getTranscriptFeed(activeSessionId);
    renderTranscriptFeed(transcriptFeedContainer(), entries);
  } catch (error) {
    console.error("Falha ao consultar o feed de transcript", error);
  }
}

async function refreshAgentPanel(): Promise<void> {
  try {
    const status = await getAgentStatus();
    renderAgentPanel(agentPanelContainer(), status, {
      onStart: async () => {
        if (!activeSessionId) return;
        try {
          await startAgent(activeSessionId, DEFAULT_PROFILE_PATH);
        } catch (error) {
          console.error("Falha ao iniciar o agent", error);
        } finally {
          await refreshAgentPanel();
        }
      },
      onStop: async () => {
        try {
          await stopAgent();
        } catch (error) {
          console.error("Falha ao parar o agent", error);
        } finally {
          await refreshAgentPanel();
        }
      },
    });
  } catch (error) {
    console.error("Falha ao consultar status do agent", error);
  }
}

export function setActiveSession(sessionId: string): void {
  activeSessionId = sessionId;
  void pollSessionStatus();
  void pollTranscriptFeed();
}

function bootstrap(): void {
  void refreshAgentPanel();
  setInterval(() => void pollSessionStatus(), STATUS_POLL_MS);
  setInterval(() => void pollTranscriptFeed(), FEED_POLL_MS);
  setInterval(() => void refreshAgentPanel(), STATUS_POLL_MS);
}

if (typeof document !== "undefined") {
  bootstrap();
}
