// Bootstrap do shell: liga os três painéis (US1/US2/US3) aos comandos Tauri via api-client,
// com polling conforme plan.md § Performance Goals (~5s status/canais, ~2s feed).
import {
  deleteAiProvider,
  getAgentStatus,
  getAiProviderSecretPreview,
  getSessionStatus,
  getTranscriptFeed,
  listAiProviders,
  saveAiProvider,
  setAiProviderEnabled,
  startAgent,
  stopAgent,
  testAiProviderConnection,
  type Provider,
} from "./api-client";
import { renderSessionStatus } from "./session-status";
import { renderTranscriptFeed } from "./transcript-feed";
import { renderAgentPanel } from "./agent-panel";
import { renderAiProviderPanel, type AiProviderPanelState } from "./ai-provider-panel";

const STATUS_POLL_MS = 5000;
const FEED_POLL_MS = 2000;
const AI_PROVIDER_POLL_MS = 10000;
const DEFAULT_PROFILE_PATH = "perfil.yaml";

let activeSessionId: string | null = null;

let aiProviderPanelState: AiProviderPanelState = {
  providers: [],
  selectedProviderId: null,
  testResult: null,
  secretPreview: null,
  error: null,
};

function sessionStatusContainer(): HTMLElement {
  return document.getElementById("session-status") as HTMLElement;
}

function transcriptFeedContainer(): HTMLElement {
  return document.getElementById("transcript-feed") as HTMLElement;
}

function agentPanelContainer(): HTMLElement {
  return document.getElementById("agent-panel") as HTMLElement;
}

function aiProviderPanelContainer(): HTMLElement {
  return document.getElementById("ai-provider-panel") as HTMLElement;
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

function renderAiProviders(): void {
  renderAiProviderPanel(aiProviderPanelContainer(), aiProviderPanelState, {
    onSelect: (providerId) => {
      aiProviderPanelState = { ...aiProviderPanelState, selectedProviderId: providerId, testResult: null, secretPreview: null };
      renderAiProviders();
      if (providerId) {
        void refreshSecretPreview(providerId);
      }
    },
    onSave: (provider: Provider) => {
      void (async () => {
        try {
          await saveAiProvider(provider);
          aiProviderPanelState = { ...aiProviderPanelState, error: null };
          await refreshAiProviderPanel();
        } catch (error) {
          aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
          renderAiProviders();
        }
      })();
    },
    onToggleEnabled: (providerId, enabled) => {
      void (async () => {
        try {
          await setAiProviderEnabled(providerId, enabled);
          await refreshAiProviderPanel();
        } catch (error) {
          aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
          renderAiProviders();
        }
      })();
    },
    onTestConnection: (providerId) => {
      void (async () => {
        try {
          const testResult = await testAiProviderConnection(providerId);
          aiProviderPanelState = { ...aiProviderPanelState, testResult, error: null };
        } catch (error) {
          aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
        }
        renderAiProviders();
      })();
    },
    onDelete: (providerId) => {
      void (async () => {
        try {
          await deleteAiProvider(providerId);
          await refreshAiProviderPanel();
        } catch (error) {
          aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
          renderAiProviders();
        }
      })();
    },
  });
}

async function refreshSecretPreview(providerId: string): Promise<void> {
  try {
    const secretPreview = await getAiProviderSecretPreview(providerId);
    aiProviderPanelState = { ...aiProviderPanelState, secretPreview };
  } catch (error) {
    aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
  }
  renderAiProviders();
}

async function refreshAiProviderPanel(): Promise<void> {
  try {
    const providers = await listAiProviders();
    aiProviderPanelState = { ...aiProviderPanelState, providers, error: null };
  } catch (error) {
    aiProviderPanelState = { ...aiProviderPanelState, error: String(error) };
  }
  renderAiProviders();
}

export function setActiveSession(sessionId: string): void {
  activeSessionId = sessionId;
  void pollSessionStatus();
  void pollTranscriptFeed();
}

function bootstrap(): void {
  void refreshAgentPanel();
  void refreshAiProviderPanel();
  setInterval(() => void pollSessionStatus(), STATUS_POLL_MS);
  setInterval(() => void pollTranscriptFeed(), FEED_POLL_MS);
  setInterval(() => void refreshAgentPanel(), STATUS_POLL_MS);
  setInterval(() => void refreshAiProviderPanel(), AI_PROVIDER_POLL_MS);
}

if (typeof document !== "undefined") {
  bootstrap();
}
