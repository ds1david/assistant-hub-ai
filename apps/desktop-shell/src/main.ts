// Bootstrap do shell: sessão (lista/criar/selecionar), transcript, agent, provedores, assistente.
// Sem auto-create silencioso de sessão (FR-026). Prefs do Assistente por sessão com save on change.
import {
  createSession,
  deleteAiProvider,
  getAgentStatus,
  getAiProviderSecretPreview,
  secretStorePut,
  secretStoreDelete,
  getSessionStatus,
  getSessionMemoryItems,
  getShellConfig,
  getTranscriptFeed,
  invokeAiProvider,
  listAiProviders,
  listSessions,
  probeHttpHealth,
  saveAiProvider,
  searchSessionMemory,
  setAiProviderEnabled,
  startAgent,
  stopAgent,
  testAiProviderConnection,
  type AgentStatus,
  type MemoryItem,
  type MemorySearchHit,
  type Provider,
  type SessionSummary,
  type TranscriptFeedEntry,
} from "./api-client";
import { AssistantAutoController } from "./assistant-auto";
import { renderAssistantPanel } from "./assistant-panel";
import { renderMemoryPanel, type MemoryPanelState } from "./memory-panel";
import {
  buildDiagnosticSnapshot,
  DEFAULT_STT_BASE_URL,
  formatDiagnosticReport,
  type DiagnosticSnapshot,
} from "./diagnostics";
import {
  renderDiagnosticsPanel,
  type DiagnosticsPanelState,
} from "./diagnostics-panel";
import {
  DEFAULT_ASSISTANT_PREFS,
  clonePrefs,
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
import {
  onSessionSelected,
  restartAgentWithActiveSession,
} from "./agent-session-actions";
import {
  resolveAlignment,
  resolveAssistantEmptyKind,
  withActiveGuidance,
} from "./session-alignment";
import {
  afterCreateSuccess,
  isSelectableSessionId,
  reconcileActiveSessionAfterList,
} from "./session-selection";

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
/** Último feed da sessão ativa (empty states FR-010). */
let lastTranscriptFeed: TranscriptFeedEntry[] = [];
/** Último status do agent (alignment + empty kind). */
let lastAgentStatus: AgentStatus | null = null;

const agentProcessActions = {
  start: (sessionId: string, profilePath: string) => startAgent(sessionId, profilePath),
  stop: () => stopAgent(),
};

let aiProviderPanelState: AiProviderPanelState = {
  providers: [],
  selectedProviderId: null,
  testResult: null,
  secretPreview: null,
  error: null,
};

let memoryPanelState: MemoryPanelState = {
  sessionId: null,
  query: "",
  sourceTypeFilter: "",
  hits: [],
  items: [],
  error: null,
  busy: false,
};

let diagnosticsState: DiagnosticsPanelState = {
  snapshot: null,
  busy: false,
  error: null,
  copyFeedback: null,
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

function memoryPanelContainer(): HTMLElement {
  return document.getElementById("memory-panel") as HTMLElement;
}

function diagnosticsPanelContainer(): HTMLElement {
  return document.getElementById("diagnostics-panel") as HTMLElement;
}

function paintDiagnosticsPanel(): void {
  const el = diagnosticsPanelContainer();
  if (!el) {
    return;
  }
  renderDiagnosticsPanel(el, diagnosticsState, {
    onRefresh: () => {
      void refreshDiagnostics();
    },
    onCopyReport: () => {
      void copyDiagnosticsReport();
    },
  });
}

async function refreshDiagnostics(): Promise<void> {
  diagnosticsState = { ...diagnosticsState, busy: true, error: null, copyFeedback: null };
  paintDiagnosticsPanel();
  try {
    const config = await getShellConfig();
    const coreUrl = config.sessionCoreBaseUrl.replace(/\/$/, "");
    const sttUrl = DEFAULT_STT_BASE_URL.replace(/\/$/, "");
    const [coreProbe, sttProbe, agent] = await Promise.all([
      probeHttpHealth(`${coreUrl}/actuator/health`).catch((e) => ({
        ok: false,
        detail: String(e),
        statusCode: null,
      })),
      probeHttpHealth(`${sttUrl}/health`).catch((e) => ({
        ok: false,
        detail: String(e),
        statusCode: null,
      })),
      getAgentStatus().catch(
        (): AgentStatus => ({
          running: false,
          controlMode: "Guided",
          guidanceCommand: "",
          lastError: "falha ao ler status do agent",
          agentSessionId: null,
          agentSessionSource: "unknown",
          binarySource: "missing",
          binaryPath: null,
          agentVersion: null,
          healthy: false,
        }),
      ),
    ]);
    const snapshot: DiagnosticSnapshot = buildDiagnosticSnapshot({
      sessionCoreBaseUrl: coreUrl,
      sttBaseUrl: sttUrl,
      activeSessionId,
      sessionCore: {
        ok: coreProbe.ok,
        detail: coreProbe.detail ?? (coreProbe.ok ? "ok" : "down"),
      },
      stt: {
        ok: sttProbe.ok,
        detail: sttProbe.detail ?? (sttProbe.ok ? "ok" : "down"),
      },
      agent: {
        running: agent.running,
        healthy: agent.healthy,
        binarySource: agent.binarySource ?? null,
        binaryPath: agent.binaryPath ?? null,
        agentVersion: agent.agentVersion ?? null,
        agentSessionId: agent.agentSessionId ?? null,
        lastError: agent.lastError ?? null,
      },
      shellRunning: true,
    });
    diagnosticsState = {
      snapshot,
      busy: false,
      error: null,
      copyFeedback: null,
    };
  } catch (error) {
    diagnosticsState = {
      ...diagnosticsState,
      busy: false,
      error: String(error),
    };
  }
  paintDiagnosticsPanel();
}

async function copyDiagnosticsReport(): Promise<void> {
  if (!diagnosticsState.snapshot) {
    return;
  }
  const text = formatDiagnosticReport(diagnosticsState.snapshot);
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback: no clipboard API
      throw new Error("clipboard indisponível");
    }
    diagnosticsState = { ...diagnosticsState, copyFeedback: "Copiado" };
  } catch {
    diagnosticsState = {
      ...diagnosticsState,
      copyFeedback: "Falha ao copiar — selecione o relatório manualmente",
    };
  }
  paintDiagnosticsPanel();
}

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

function computeAssistantEmptyKind() {
  const view = assistantController.getView();
  if (view.turns.length > 0) {
    return null;
  }
  const alignment = resolveAlignment(activeSessionId, {
    running: lastAgentStatus?.running ?? false,
    agentSessionId: lastAgentStatus?.agentSessionId ?? null,
  });
  return resolveAssistantEmptyKind({
    alignment,
    autoEnabled: view.prefs.autoEnabled,
    enabledSourceTypes: view.prefs.enabledSourceTypes,
    feed: lastTranscriptFeed,
    interviewMode: view.prefs.interviewMode,
    useProsody: view.prefs.useProsody,
    prosodyThreshold: view.prefs.prosodyThreshold,
  });
}

/** Só renderiza o painel — não reaplica guards (evita loop setControlsDisabled → onChange → paint). */
function paintAssistant(): void {
  const base = assistantController.getView();
  const view = {
    ...base,
    emptyKind: base.turns.length === 0 ? computeAssistantEmptyKind() : null,
  };
  renderAssistantPanel(assistantPanelContainer(), view, {
    onToggleEnabled: (enabled) => {
      const prefs = { ...currentPrefsFromController(), autoEnabled: enabled };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
      // setPrefs já emite → onChange → paintAssistant
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
    },
    onInputModeChange: (mode: InputMode) => {
      const prefs = { ...currentPrefsFromController(), inputMode: mode };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
    },
    onToggleInterviewMode: (enabled) => {
      const prefs = { ...currentPrefsFromController(), interviewMode: enabled };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
    },
    onToggleIncludeMicContext: (enabled) => {
      const prefs = {
        ...currentPrefsFromController(),
        includeMicrophoneInContext: enabled,
      };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
    },
    onToggleUseProsody: (enabled) => {
      const prefs = { ...currentPrefsFromController(), useProsody: enabled };
      assistantController.setPrefs(prefs);
      void persistPrefs(prefs);
    },
    onResolveConflict: (choice) => {
      assistantController.resolveConflict(choice);
      // resolveConflict emite → onChange → paintAssistant
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
  // 020 FR-009 / 021 FR-011: troca de sessão NÃO reinicia o agent.
  if (!isSelectableSessionId(sessionId)) {
    return;
  }
  onSessionSelected(sessionId, (id) => {
    activeSessionId = id;
  });
  transcriptPrimed = false;
  lastTranscriptFeed = [];
  assistantController.resetSessionState();
  try {
    const prefs = await loadPrefs(sessionId);
    assistantController.setPrefs(prefs);
  } catch {
    assistantController.setPrefs(clonePrefs(DEFAULT_ASSISTANT_PREFS));
  }
  updateAssistantGuards();
  paintSessionPicker();
  // updateAssistantGuards emite se o estado mudou; paint cobre o caso sem mudança.
  paintAssistant();
  memoryPanelState = {
    ...memoryPanelState,
    sessionId,
    hits: [],
    items: [],
    error: null,
  };
  paintMemoryPanel();
  void refreshMemoryItems();
  void refreshAgentPanel();
  void pollSessionStatus();
  void pollTranscriptFeed();
}

function paintMemoryPanel(): void {
  const el = memoryPanelContainer();
  if (!el) {
    return;
  }
  renderMemoryPanel(el, memoryPanelState, {
    onSearch: (query, sourceType) => {
      void (async () => {
        if (!activeSessionId) {
          return;
        }
        memoryPanelState = {
          ...memoryPanelState,
          query,
          sourceTypeFilter: sourceType,
          busy: true,
          error: null,
        };
        paintMemoryPanel();
        try {
          const hits = await searchSessionMemory(
            activeSessionId,
            query,
            sourceType || null,
            50,
          );
          memoryPanelState = { ...memoryPanelState, hits, busy: false };
        } catch (error) {
          memoryPanelState = {
            ...memoryPanelState,
            hits: [],
            busy: false,
            error: String(error),
          };
        }
        paintMemoryPanel();
      })();
    },
    onRefreshItems: () => {
      void refreshMemoryItems();
    },
  });
}

async function refreshMemoryItems(): Promise<void> {
  if (!activeSessionId) {
    memoryPanelState = {
      ...memoryPanelState,
      sessionId: null,
      items: [] as MemoryItem[],
      hits: [] as MemorySearchHit[],
    };
    paintMemoryPanel();
    return;
  }
  try {
    const items = await getSessionMemoryItems(activeSessionId);
    memoryPanelState = {
      ...memoryPanelState,
      sessionId: activeSessionId,
      items,
      error: null,
    };
  } catch (error) {
    memoryPanelState = {
      ...memoryPanelState,
      sessionId: activeSessionId,
      error: String(error),
    };
  }
  paintMemoryPanel();
}

async function createAndSelectSession(): Promise<void> {
  sessionBusy = true;
  paintSessionPicker();
  try {
    const session = await createSession(DEFAULT_SESSION_TITLE, DEFAULT_PROFILE_ID);
    coreReachable = true;
    sessionListError = null;
    await refreshSessionList();
    // 021 FR-005: create → active sem segundo clique (via afterCreateSuccess).
    await afterCreateSuccess(session.id, selectSession);
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
    // 021 FR-006: orphan → null só em listagem bem-sucedida; paint reexibe «Nenhuma…» (FR-003).
    const reconciled = reconcileActiveSessionAfterList(activeSessionId, sessionList);
    if (reconciled !== activeSessionId) {
      if (reconciled == null) {
        transcriptPrimed = false;
        lastTranscriptFeed = [];
        assistantController.resetSessionState();
      }
      activeSessionId = reconciled;
    }
  } catch (error) {
    // Falha de list: não inventar lista; manter active prévio + erro (data-model refresh_fail).
    sessionList = [];
    sessionListError = `Falha ao listar sessões (session-core?): ${String(error)}`;
    coreReachable = false;
  }
  updateAssistantGuards();
  paintSessionPicker();
  paintAssistant();
  void refreshAgentPanel();
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
    lastTranscriptFeed = entries;
    renderTranscriptFeed(transcriptFeedContainer(), entries);
    if (!transcriptPrimed) {
      assistantController.markSeen(entries);
      transcriptPrimed = true;
    } else {
      assistantController.ingestTranscript(entries);
    }
    paintAssistant();
  } catch (error) {
    console.error("Falha ao consultar o feed de transcript", error);
  }
}

async function refreshAgentPanel(): Promise<void> {
  try {
    let status = await getAgentStatus();
    status = withActiveGuidance(status, activeSessionId, DEFAULT_PROFILE_PATH);
    lastAgentStatus = status;
    renderAgentPanel(
      agentPanelContainer(),
      { status, activeSessionId },
      {
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
        onRestart: async () => {
          try {
            await restartAgentWithActiveSession(
              activeSessionId,
              status.controlMode,
              status.running,
              DEFAULT_PROFILE_PATH,
              agentProcessActions,
            );
          } catch (error) {
            console.error("Falha ao reiniciar o agent com sessão ativa", error);
          } finally {
            await refreshAgentPanel();
          }
        },
      },
    );
    paintAssistant();
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
    onSave: (provider: Provider, secretValue?: string | null) => {
      void (async () => {
        try {
          let toSave = provider;
          if (secretValue && secretValue.length > 0 && provider.authentication.mode !== "none") {
            const preferEnv = provider.authentication.secretRef?.startsWith("env:");
            if (!preferEnv) {
              const secretRef = await secretStorePut(provider.id, secretValue);
              toSave = {
                ...provider,
                authentication: {
                  ...provider.authentication,
                  secretRef,
                },
              };
            }
            // env: path: operator manages the variable; value field ignored for store.
          }
          await saveAiProvider(toSave);
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
          try {
            await secretStoreDelete(providerId);
          } catch {
            // store miss is ok
          }
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
  // Guards primeiro (sem sessão → controles desabilitados); paint se emit for no-op.
  updateAssistantGuards();
  paintAssistant();
  paintMemoryPanel();
  paintDiagnosticsPanel();
  paintSessionPicker();
  void refreshSessionList().then(() => {
    void refreshAgentPanel();
    void refreshAiProviderPanel();
    void refreshDiagnostics();
  });
  setInterval(() => void pollSessionStatus(), STATUS_POLL_MS);
  setInterval(() => void pollTranscriptFeed(), FEED_POLL_MS);
  setInterval(() => void refreshAgentPanel(), STATUS_POLL_MS);
  setInterval(() => void refreshAiProviderPanel(), AI_PROVIDER_POLL_MS);
}

if (typeof document !== "undefined") {
  bootstrap();
}
