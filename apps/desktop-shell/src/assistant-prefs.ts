// Preferências do Assistente por sessão — tipos, defaults e wrappers Tauri (FR-025 / 023 / 028).
import { invoke } from "@tauri-apps/api/core";

export type CanonicalSourceType = "microphone" | "system";
export type InputMode = "question-only" | "question-plus-recent-context";

export interface AssistantSessionPreferences {
  autoEnabled: boolean;
  enabledSourceTypes: CanonicalSourceType[];
  inputMode: InputMode;
  /** FR-004 (023): Final system ≥8 chars is always a candidate. Also enables interview style (028). */
  interviewMode: boolean;
  /** FR-006/008: use optional prosody.questionScore from Final events. */
  useProsody: boolean;
  /** [0,1]; no dedicated UI control in v1 (store default). */
  prosodyThreshold: number;
  /**
   * 028: include microphone Finals in recent-context builder.
   * Default ON when missing (opt-out). Does NOT affect trigger origins.
   */
  includeMicrophoneInContext: boolean;
}

export const DEFAULT_ASSISTANT_PREFS: AssistantSessionPreferences = {
  autoEnabled: false,
  enabledSourceTypes: ["system"],
  inputMode: "question-plus-recent-context",
  interviewMode: false,
  useProsody: false,
  prosodyThreshold: 0.65,
  includeMicrophoneInContext: true,
};

/** Clone prefs with a fresh enabledSourceTypes array. */
export function clonePrefs(prefs: AssistantSessionPreferences): AssistantSessionPreferences {
  return {
    autoEnabled: prefs.autoEnabled,
    enabledSourceTypes: [...prefs.enabledSourceTypes],
    inputMode: prefs.inputMode,
    interviewMode: prefs.interviewMode,
    useProsody: prefs.useProsody,
    prosodyThreshold: prefs.prosodyThreshold,
    includeMicrophoneInContext: prefs.includeMicrophoneInContext,
  };
}

/** Store em memória para testes (sem Tauri). */
export interface AssistantPrefsStore {
  load(sessionId: string): Promise<AssistantSessionPreferences>;
  save(sessionId: string, prefs: AssistantSessionPreferences): Promise<void>;
}

export function createMemoryPrefsStore(
  initial: Record<string, AssistantSessionPreferences> = {},
): AssistantPrefsStore {
  const map = new Map<string, AssistantSessionPreferences>(
    Object.entries(initial).map(([k, v]) => [k, clonePrefs(v)]),
  );
  return {
    async load(sessionId: string) {
      const existing = map.get(sessionId);
      if (!existing) {
        return clonePrefs(DEFAULT_ASSISTANT_PREFS);
      }
      return clonePrefs(existing);
    },
    async save(sessionId: string, prefs: AssistantSessionPreferences) {
      map.set(sessionId, clonePrefs(prefs));
    },
  };
}

/** Load via comando Tauri; em ambiente sem invoke (vitest) o caller deve injetar store. */
export async function loadPrefs(sessionId: string): Promise<AssistantSessionPreferences> {
  try {
    const result = await invoke<AssistantSessionPreferences>("get_assistant_prefs", { sessionId });
    return normalizePrefs(result);
  } catch {
    return clonePrefs(DEFAULT_ASSISTANT_PREFS);
  }
}

export async function savePrefs(
  sessionId: string,
  prefs: AssistantSessionPreferences,
): Promise<void> {
  await invoke("set_assistant_prefs", {
    sessionId,
    prefs: {
      autoEnabled: prefs.autoEnabled,
      enabledSourceTypes: prefs.enabledSourceTypes,
      inputMode: prefs.inputMode,
      interviewMode: prefs.interviewMode,
      useProsody: prefs.useProsody,
      prosodyThreshold: prefs.prosodyThreshold,
      includeMicrophoneInContext: prefs.includeMicrophoneInContext,
    },
  });
}

function clampThreshold(value: unknown): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return DEFAULT_ASSISTANT_PREFS.prosodyThreshold;
  }
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return value;
}

/** Missing/null includeMicrophoneInContext → true (028 default ON). */
function normalizeIncludeMic(raw: Partial<AssistantSessionPreferences>): boolean {
  if (raw.includeMicrophoneInContext === undefined || raw.includeMicrophoneInContext === null) {
    return true;
  }
  return Boolean(raw.includeMicrophoneInContext);
}

export function normalizePrefs(
  raw: Partial<AssistantSessionPreferences> | null | undefined,
): AssistantSessionPreferences {
  if (!raw) {
    return clonePrefs(DEFAULT_ASSISTANT_PREFS);
  }
  const sources = Array.isArray(raw.enabledSourceTypes)
    ? raw.enabledSourceTypes.filter((s): s is CanonicalSourceType => s === "microphone" || s === "system")
    : [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes];
  const inputMode: InputMode =
    raw.inputMode === "question-only" || raw.inputMode === "question-plus-recent-context"
      ? raw.inputMode
      : DEFAULT_ASSISTANT_PREFS.inputMode;
  return {
    autoEnabled: Boolean(raw.autoEnabled),
    enabledSourceTypes: sources.length > 0 ? sources : [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes],
    inputMode,
    interviewMode: Boolean(raw.interviewMode),
    useProsody: Boolean(raw.useProsody),
    prosodyThreshold: clampThreshold(raw.prosodyThreshold),
    includeMicrophoneInContext: normalizeIncludeMic(raw),
  };
}
