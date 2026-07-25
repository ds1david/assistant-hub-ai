// Bootstrap do shell: sessão (lista/criar/selecionar), transcript, agent, provedores, assistente.
// Sem auto-create silencioso de sessão (FR-026). Prefs do Assistente por sessão com save on change.
import {
  createSession,
  deleteAiProvider,
  getAgentStatus,
  getAiProviderSecretPreview,
  getSessionStatus,
  getTranscriptFeed,
  invokeAiProvider,
  listAiProviders,
  listSessions,
  saveAiProvider,
  setAiProviderEnabled,
  startAgent,
  stopAgent,
  testAiProviderConnection,
  type Provider,
  type SessionSummary,
} from "./api-client";
import { AssistantAutoController } from "./assistant-auto";
import { renderAssistantPanel } from "./assistant-panel";
import {
  DEFAULT_ASSISTANT_PREFS,
  loadPrefs,
  savePrefs,
  type AssistantSessionPreferences,
  type CanonicalSourceType,
  type InputMode,
} from "./assistant-prefs";
import { renderSessionStatus } from "./session-status";
import { renderSessionPicker } from "./session-picker";
import { renderTranscriptFeed } from "./transcript-feed";
import { renderAgentPanel } from "./agent-panel";
import { renderAiProviderPanel, type AiProviderPanelState } from "./ai-provider-panel";

const STATUS_POLL_MS = 5000;
const FEED_POLL_MS = 2000;
const AI_PROVIDER_POLL_MS = 10000;
const DEFAULT_PROFILE_PATH = "perfil.yaml";
const DEFAULT_SESSION_TITLE = "Sessão local";
const DEFAULT_PROFILE_ID = "interview-technical";
const LIVE_ANSWER_ROUTE = "live-answer";

let activeSessionId: string | null = null;
/** Primeiro poll de transcript só marca vistos — evita auto-responder histórico antigo. */
let transcriptPrimed = false;
let sessionList: SessionSummary[] = [];
let sessionListError: string | null = null;
let sessionBusy = false;
let coreReachable = true;

let aiProviderPanelState: AiProviderPanelState = {
  providers: [],
  selectedProviderId: null,
  testResult: null,
  secretPreview: null,
  error: null,
};

const assistantController = new AssistantAutoController({
  invoke: (input) => {
    if (!activeSessionId) {
      return Promise.reject(new Error("sem sessão ativa"));
    }
    // Sem channelId: evita 422 de origem de canal; a pergunta já veio do transcript.
    return invokeAiProvider(activeSessionId, LIVE_ANSWER_ROUTE, "chat", input);
  },
});

function sessionStatusContainer(): HTMLElement {
  return document.getElementById("session-status") as HTMLElement;
}

function sessionPickerContainer(): HTMLElement {
  return document.getElementById("session-picker") as HTMLElement;
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

function assistantPanelContainer(): HTMLElement {
  return document.getElementById("assistant-panel") as HTMLElement;
}

function currentPrefsFromController(): AssistantSessionPreferences {
  return assistantController.getPrefs();
}

async function persistPrefs(prefs: AssistantSessionPreferences): Promise<void> {
  if (!activeSessionId) {
    return;
  }
  try {
    await savePrefs(activeSessionId, prefs);
  } catch (error) {
    console.error("Falha ao gravar preferências do Assistente", error);
  }
}

function updateAssistantGuards(): void {
  if (!activeSessionId) {
    assistantController.setControlsDisabled(
      true,
      "Selecione ou crie uma sessão para usar o Assistente automático.",
    );
    return;
  }
  if (!coreReachable) {
    assistantController.setControlsDisabled(
      true,
      "session-core indisponível — automático desabilitado até reconectar.",
    );
    return;
  }
  assistantController.setControlsDisabled(false, null);
}

function paintAssistant(): void {
  updateAssistantGuards();
  renderAssistantPanel(assistantPanelContainer(), assistantController.getView(), {
    onToggleEnabled: (enabled) => {
      const prefs = { ...currentPrefsFromController(), autoEnabled: enabled };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
      paintAssistant();
    },
    onToggleOrigin: (origin: CanonicalSourceType, enabled: boolean) => {
      const current = currentPrefsFromController();
      const set = new Set(current.enabledSourceTypes);
      if (enabled) {
        set.add(origin);
      } else {
        set.delete(origin);
      }
      const prefs: AssistantSessionPreferences = {
        ...current,
        enabledSourceTypes: Array.from(set) as CanonicalSourceType[],
      };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
      paintAssistant();
    },
    onInputModeChange: (mode: InputMode) => {
      const prefs = { ...currentPrefsFromController(), inputMode: mode };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
      paintAssistant();
    },
    onResolveConflict: (choice) => {
      assistantController.resolveConflict(choice);
      paintAssistant();
    },
  });
}

assistantController.setOnChange(() => {
  paintAssistant();
});

function paintSessionPicker(): void {
  renderSessionPicker(
    sessionPickerContainer(),
    {
      sessions: sessionList,
      activeSessionId,
      error: sessionListError,
      busy: sessionBusy,
    },
    {
      onSelect: (sessionId) => {
        void selectSession(sessionId);
      },
      onCreate: () => {
        void createAndSelectSession();
      },
      onRefresh: () => {
        void refreshSessionList();
      },
    },
  );
}

export async function selectSession(sessionId: string): Promise<void> {
  activeSessionId = sessionId;
  transcriptPrimed = false;
  assistantController.resetSessionState();
  try {
    const prefs = await loadPrefs(sessionId);
    assistantController.setPrefs(prefs);
  } catch {
    assistantController.setPrefs({
      ...DEFAULT_ASSISTANT_PREFS,
      enabledSourceTypes: [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes],
    });
  }
  updateAssistantGuards();
  paintSessionPicker();
  paintAssistant();
  void pollSessionStatus();
  void pollTranscriptFeed();
}

async function createAndSelectSession(): Promise<void> {
  sessionBusy = true;
  paintSessionPicker();
  try {
    const session = await createSession(DEFAULT_SESSION_TITLE, DEFAULT_PROFILE_ID);
    coreReachable = true;
    sessionListError = null;
    await refreshSessionList();
    await selectSession(session.id);
    console.info("Sessão criada para o shell:", session.id);
  } catch (error) {
    coreReachable = false;
    sessionListError = `Falha ao criar sessão: ${String(error)}`;
    updateAssistantGuards();
    paintSessionPicker();
    paintAssistant();
  } finally {
    sessionBusy = false;
    paintSessionPicker();
  }
}

async function refreshSessionList(): Promise<void> {
  try {
    sessionList = await listSessions();
    sessionListError = null;
    coreReachable = true;
  } catch (error) {
    sessionList = [];
    sessionListError = `Falha ao listar sessões (session-core?): ${String(error)}`;
    coreReachable = false;
  }
  updateAssistantGuards();
  paintSessionPicker();
  paintAssistant();
}

async function pollSessionStatus(): Promise<void> {
  if (!activeSessionId) {
    return;
  }
  try {
    const response = await getSessionStatus(activeSessionId);
    coreReachable = response.status.connectivity === "Connected"
      || (typeof response.status.connectivity === "object" && "Error" in response.status.connectivity
        ? false
        : response.status.connectivity !== "Disconnected");
    if (response.status.connectivity === "Disconnected") {
      coreReachable = false;
    } else if (response.status.connectivity === "Connected") {
      coreReachable = true;
    }
    renderSessionStatus(sessionStatusContainer(), response);
    updateAssistantGuards();
    paintAssistant();
  } catch (error) {
    console.error("Falha ao consultar status da sessão", error);
    coreReachable = false;
    updateAssistantGuards();
    paintAssistant();
  }
}

async function pollTranscriptFeed(): Promise<void> {
  if (!activeSessionId) {
    return;
  }
  try {
    const entries = await getTranscriptFeed(activeSessionId);
    renderTranscriptFeed(transcriptFeedContainer(), entries);
    if (!transcriptPrimed) {
      assistantController.markSeen(entries);
      transcriptPrimed = true;
    } else {
      assistantController.ingestTranscript(entries);
    }
  } catch (error) {
    console.error("Falha ao consultar o feed de transcript", error);
  }
}

async function refreshAgentPanel(): Promise<void> {
  try {
    const status = await getAgentStatus();
    renderAgentPanel(agentPanelContainer(), status, {
      onStart: async () => {
        if (!activeSessionId) {
          return;
        }
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
      aiProviderPanelState = {
        ...aiProviderPanelState,
        selectedProviderId: providerId,
        testResult: null,
        secretPreview: null,
      };
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

/** @deprecated use selectSession — mantido para testes legados. */
export function setActiveSession(sessionId: string): void {
  void selectSession(sessionId);
}

function bootstrap(): void {
  paintAssistant();
  paintSessionPicker();
  void refreshSessionList().then(() => {
    void refreshAgentPanel();
    void refreshAiProviderPanel();
  });
  setInterval(() => void pollSessionStatus(), STATUS_POLL_MS);
  setInterval(() => void pollTranscriptFeed(), FEED_POLL_MS);
  setInterval(() => void refreshAgentPanel(), STATUS_POLL_MS);
  setInterval(() => void refreshAiProviderPanel(), AI_PROVIDER_POLL_MS);
}

if (typeof document !== "undefined") {
  bootstrap();
}
