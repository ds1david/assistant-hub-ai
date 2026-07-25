// Preferências do Assistente por sessão — tipos, defaults e wrappers Tauri (FR-025).
import { invoke } from "@tauri-apps/api/core";

export type CanonicalSourceType = "microphone" | "system";
export type InputMode = "question-only" | "question-plus-recent-context";

export interface AssistantSessionPreferences {
  autoEnabled: boolean;
  enabledSourceTypes: CanonicalSourceType[];
  inputMode: InputMode;
}

export const DEFAULT_ASSISTANT_PREFS: AssistantSessionPreferences = {
  autoEnabled: false,
  enabledSourceTypes: ["system"],
  inputMode: "question-plus-recent-context",
};

/** Store em memória para testes (sem Tauri). */
export interface AssistantPrefsStore {
  load(sessionId: string): Promise<AssistantSessionPreferences>;
  save(sessionId: string, prefs: AssistantSessionPreferences): Promise<void>;
}

export function createMemoryPrefsStore(
  initial: Record<string, AssistantSessionPreferences> = {},
): AssistantPrefsStore {
  const map = new Map<string, AssistantSessionPreferences>(
    Object.entries(initial).map(([k, v]) => [k, { ...v, enabledSourceTypes: [...v.enabledSourceTypes] }]),
  );
  return {
    async load(sessionId: string) {
      const existing = map.get(sessionId);
      if (!existing) {
        return { ...DEFAULT_ASSISTANT_PREFS, enabledSourceTypes: [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes] };
      }
      return {
        autoEnabled: existing.autoEnabled,
        enabledSourceTypes: [...existing.enabledSourceTypes],
        inputMode: existing.inputMode,
      };
    },
    async save(sessionId: string, prefs: AssistantSessionPreferences) {
      map.set(sessionId, {
        autoEnabled: prefs.autoEnabled,
        enabledSourceTypes: [...prefs.enabledSourceTypes],
        inputMode: prefs.inputMode,
      });
    },
  };
}

/** Load via comando Tauri; em ambiente sem invoke (vitest) o caller deve injetar store. */
export async function loadPrefs(sessionId: string): Promise<AssistantSessionPreferences> {
  try {
    const result = await invoke<AssistantSessionPreferences>("get_assistant_prefs", { sessionId });
    return normalizePrefs(result);
  } catch {
    return { ...DEFAULT_ASSISTANT_PREFS, enabledSourceTypes: [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes] };
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
    },
  });
}

export function normalizePrefs(raw: Partial<AssistantSessionPreferences> | null | undefined): AssistantSessionPreferences {
  if (!raw) {
    return { ...DEFAULT_ASSISTANT_PREFS, enabledSourceTypes: [...DEFAULT_ASSISTANT_PREFS.enabledSourceTypes] };
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
  };
}
