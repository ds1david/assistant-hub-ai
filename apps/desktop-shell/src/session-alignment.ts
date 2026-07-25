// Alinhamento sessionId UI↔agent e estados vazios do Assistente (020 / FR-005–FR-010).
import type { AgentStatus, FeedEntryKind, TranscriptFeedEntry } from "./api-client";
import {
  looksLikeQuestion,
  normalizeSourceType,
  isOriginEnabled,
} from "./assistant-auto";
import type { AssistantSessionPreferences, CanonicalSourceType } from "./assistant-prefs";

export type AlignmentState =
  | "no_active_session"
  | "agent_stopped"
  | "agent_session_unknown"
  | "aligned"
  | "mismatched";

export type AssistantEmptyKind =
  | "session_mismatch"
  | "prefs_auto_off"
  | "prefs_no_origin"
  | "awaiting_transcript"
  | "awaiting_final"
  | "no_eligible_question"
  | "generic";

export function resolveAlignment(
  activeSessionId: string | null,
  agent: { running: boolean; agentSessionId: string | null },
): AlignmentState {
  if (activeSessionId == null || activeSessionId.trim() === "") {
    return "no_active_session";
  }
  if (!agent.running) {
    return "agent_stopped";
  }
  if (agent.agentSessionId == null || agent.agentSessionId.trim() === "") {
    return "agent_session_unknown";
  }
  if (agent.agentSessionId === activeSessionId) {
    return "aligned";
  }
  return "mismatched";
}

export function buildGuidanceCommand(sessionId: string, profilePath: string): string {
  return `assistant-hub-audio run --session ${sessionId} --profile ${profilePath}`;
}

/** FR-010: só aplica quando turns.length === 0 (caller garante). */
export function resolveAssistantEmptyKind(input: {
  alignment: AlignmentState;
  autoEnabled: boolean;
  enabledSourceTypes: readonly CanonicalSourceType[];
  feed: readonly Pick<TranscriptFeedEntry, "kind" | "text" | "sourceType">[];
}): AssistantEmptyKind {
  if (input.alignment === "mismatched") {
    return "session_mismatch";
  }
  if (!input.autoEnabled) {
    return "prefs_auto_off";
  }
  if (input.enabledSourceTypes.length === 0) {
    return "prefs_no_origin";
  }
  if (input.feed.length === 0) {
    return "awaiting_transcript";
  }

  const hasPartial = input.feed.some((e) => e.kind === ("Partial" as FeedEntryKind));
  const finals = input.feed.filter((e) => e.kind === ("Final" as FeedEntryKind));
  const hasEligibleFinal = finals.some((e) => {
    const text = e.text?.trim() ?? "";
    if (!looksLikeQuestion(text)) {
      return false;
    }
    const origin = normalizeSourceType(e.sourceType);
    return isOriginEnabled(origin, input.enabledSourceTypes);
  });

  if (hasEligibleFinal) {
    // Com turn ainda zero e final elegível, o orquestrador deve consumir em breve;
    // genérico evita culpar partials.
    return "generic";
  }

  if (hasPartial && finals.length === 0) {
    return "awaiting_final";
  }

  if (finals.length > 0) {
    return "no_eligible_question";
  }

  // Só partials? already handled. Só lixo sem kind? generic.
  if (hasPartial) {
    return "awaiting_final";
  }
  return "generic";
}

export function emptyKindCopy(kind: AssistantEmptyKind): string {
  switch (kind) {
    case "session_mismatch":
      return "Sessão do agent diferente da sessão ativa — alinhe com «Reiniciar agent com sessão ativa» ou pare o agent manualmente e reinicie com o id da UI.";
    case "prefs_auto_off":
      return "Automático desligado. Ligue o automático para gerar respostas a partir de perguntas finais no transcript.";
    case "prefs_no_origin":
      return "Nenhuma origem de canal habilitada. Habilite sistema e/ou microfone para disparar o Assistente.";
    case "awaiting_transcript":
      return "Aguardando transcript nesta sessão. Inicie o agent com o mesmo sessionId da UI.";
    case "awaiting_final":
      return "Aguardando trecho final. O automático só dispara em perguntas finais (não em partials).";
    case "no_eligible_question":
      return "Há trechos finais, mas nenhum foi reconhecido como pergunta elegível nas origens habilitadas.";
    case "generic":
    default:
      return "Nenhuma interação ainda. Com o automático ligado e uma sessão ativa, perguntas finais no transcript (origem habilitada) disparam a rota live-answer.";
  }
}

/** Helper de paint: enriquece status com guidance da sessão ativa. */
export function withActiveGuidance(
  status: AgentStatus,
  activeSessionId: string | null,
  profilePath: string,
): AgentStatus {
  if (!activeSessionId) {
    return status;
  }
  return {
    ...status,
    guidanceCommand: buildGuidanceCommand(activeSessionId, profilePath),
  };
}
