// Assistente automático a partir do transcript (perguntas finais → rota live-answer).
// 023: FR-002 lexical expandido, FR-004 interviewMode, FR-006 isQuestionCandidate (OR gate).
// 028: contexto mic+system rotulado, includeMicrophoneInContext, instrução 1ª pessoa.
// Cancelamento é lógico (resposta obsoleta descartada) — invoke Tauri/HTTP sem abort token.
import type { InvocationResult, TranscriptFeedEntry } from "./api-client";
import {
  DEFAULT_ASSISTANT_PREFS,
  clonePrefs,
  type AssistantSessionPreferences,
  type CanonicalSourceType,
  type InputMode,
} from "./assistant-prefs";
import type { AssistantEmptyKind } from "./session-alignment";

export type AssistantTurnStatus = "running" | "done" | "error" | "cancelled" | "queued";

export interface AssistantTurn {
  id: string;
  question: string;
  eventId: string;
  channelId: string | null;
  status: AssistantTurnStatus;
  answer: string | null;
  error: string | null;
  providerId: string | null;
  latencyMs: number | null;
}

export interface AssistantConflict {
  runningTurnId: string;
  runningQuestion: string;
  incoming: QuestionCandidate;
}

export interface QuestionCandidate {
  eventId: string;
  text: string;
  channelId: string | null;
  sourceType: CanonicalSourceType | null;
}

export interface AssistantAutoView {
  enabled: boolean;
  prefs: AssistantSessionPreferences;
  turns: AssistantTurn[];
  conflict: AssistantConflict | null;
  busy: boolean;
  /** Controles desabilitados (sem sessão / core down). */
  controlsDisabled?: boolean;
  sessionHint?: string | null;
  /** Estado vazio do painel (FR-010); null se há turns ou não computado. */
  emptyKind?: AssistantEmptyKind | null;
}

export type ConflictChoice = "cancel" | "wait";

export interface AssistantAutoDeps {
  /** Invoca a rota live-answer com o input já montado (sem channelId). */
  invoke: (input: string) => Promise<InvocationResult>;
  createId?: () => string;
}

/**
 * Prefixos canônicos FR-002 (supersede de 019 FR-004 no shell) + imperativos de entrevista.
 * Ordem: mais longos primeiro para evitar match parcial acidental.
 * Fonte canônica da lista: specs/023-issue-52-question-detection-quality/spec.md FR-002.
 */
const PT_PREFIXES = [
  "será que",
  "me descreva",
  "me conte",
  "me conta",
  "me fale",
  "me fala",
  "me diga",
  "me explique",
  "pode me",
  "pode descrever",
  "pode explicar",
  "pode contar",
  "conte sobre",
  "conte-me",
  "conte me",
  "descreva",
  "explique",
  "por que",
  "porque",
  "para que",
  "pra que",
  "em que",
  "o que",
  "quais",
  "qual",
  "quem",
  "quando",
  "onde",
  "como",
] as const;

const EN_PREFIXES = [
  "tell me about",
  "tell me",
  "walk me through",
  "describe",
  "explain",
  "what",
  "which",
  "who",
  "when",
  "where",
  "why",
  "how",
  "is ",
  "are ",
  "do ",
  "does ",
  "can ",
  "could ",
  "would ",
] as const;

const ALL_PREFIXES: readonly string[] = [...PT_PREFIXES, ...EN_PREFIXES];

export const MAX_CONTEXT_FINAL_SEGMENTS = 12;
export const MAX_CONTEXT_CHARS = 4000;

/** Rótulos canônicos no bloco de contexto (028 FR-007). */
export const CONTEXT_LABEL_SYSTEM = "Entrevistador";
export const CONTEXT_LABEL_MICROPHONE = "Candidato (eu)";

/**
 * Instrução fixa de modo entrevista (028 FR-009–011).
 * Prefixa o input do invoke quando interviewMode=true.
 */
export const INTERVIEW_ANSWER_INSTRUCTION = [
  "Instruções de resposta (modo entrevista):",
  "- Responda em 1ª pessoa (eu/meu/minha), em português do Brasil natural.",
  "- Escreva como fala oral pronta para eu ler em voz alta (~30 a 90 segundos).",
  "- Saída: SOMENTE o texto da fala. Sem prefácio de assistente, sem markdown pesado, sem listas longas.",
  "- Não diga “Claro!”, “Como candidato…”, “Você poderia dizer…”, “Responda assim…”.",
  "- Não invente empresas, números, datas ou fatos fora do contexto fornecido.",
  "- Se faltar contexto, diga de forma curta e honesta o que consegue afirmar.",
].join("\n");

export interface RecentFinalSegment {
  eventId: string;
  text: string;
  sourceType: CanonicalSourceType | null;
}

export interface BuildInvokeInputOptions {
  excludeEventId?: string;
  /** Default true when omitted. */
  includeMicrophoneInContext?: boolean;
  /** Default false when omitted. */
  interviewMode?: boolean;
}

/**
 * Detector de padrões de meta-assistente (028 FR-012).
 * Uso em testes; runtime NÃO deve rejeitar a resposta do modelo (FR-012b).
 */
export function hasMetaAssistantStyle(text: string): boolean {
  const t = text.trim();
  if (!t) {
    return false;
  }
  // Prefácios no início
  if (/^(Claro!|Claro,|Com certeza!)/i.test(t)) {
    return true;
  }
  const lower = t.toLowerCase();
  const phrases = [
    "como candidato",
    "você poderia dizer",
    "você deve responder",
    "na sua resposta",
    "responda assim",
    "aqui está uma sugestão de resposta",
  ];
  for (const p of phrases) {
    if (lower.includes(p)) {
      return true;
    }
  }
  // Markdown pesado: ≥4 bullets consecutivos ou headings
  if (/(^|\n)#{1,2}\s/m.test(t)) {
    return true;
  }
  const lines = t.split(/\r?\n/);
  let streak = 0;
  for (const line of lines) {
    if (/^\s*[-*]\s+/.test(line)) {
      streak += 1;
      if (streak >= 4) {
        return true;
      }
    } else if (line.trim() !== "") {
      streak = 0;
    }
  }
  return false;
}

function contextLabelFor(sourceType: CanonicalSourceType): string {
  return sourceType === "system" ? CONTEXT_LABEL_SYSTEM : CONTEXT_LABEL_MICROPHONE;
}

function withInterviewInstruction(body: string, interviewMode: boolean): string {
  if (!interviewMode) {
    return body;
  }
  return `${INTERVIEW_ANSWER_INSTRUCTION}\n\n${body}`;
}

/** Remove vocativo curto no início: "David, me conte…" → "me conte…". */
export function stripLeadingVocative(lower: string): string {
  // Nome/apelido + vírgula (até ~40 chars de letras/espaços/hífen/apóstrofo).
  const m = lower.match(/^[\p{L}][\p{L}\d\s.'-]{0,40},\s+/u);
  if (m) {
    return lower.slice(m[0].length);
  }
  return lower;
}

/** Candidatos de início: texto inteiro, sem vocativo, e após . ! */
function questionStartCandidates(lower: string): string[] {
  const out: string[] = [];
  const push = (s: string) => {
    const t = s.trim();
    if (t.length > 0) {
      out.push(t);
      const stripped = stripLeadingVocative(t);
      if (stripped !== t && stripped.length > 0) {
        out.push(stripped);
      }
    }
  };
  push(lower);
  for (const part of lower.split(/(?<=[.!])\s+/)) {
    push(part);
  }
  return out;
}

function startsWithQuestionPrefix(candidate: string): boolean {
  for (const p of ALL_PREFIXES) {
    if (!candidate.startsWith(p)) {
      continue;
    }
    // Prefixo com espaço final já impõe limite ("is ", "are ").
    if (p.endsWith(" ")) {
      return true;
    }
    const next = candidate.charAt(p.length);
    // Limite de palavra: evita qual≠qualidade, how≠however, describe≠described.
    if (next === "" || /[\s,?!:;.\-']/.test(next)) {
      return true;
    }
  }
  return false;
}

/**
 * Heurística FR-002: ≥8 chars + (`?` ou prefixo canônico/entrevista pt/en
 * no início do trecho, após vocativo, ou em nova sentença).
 */
export function looksLikeQuestion(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 8) {
    return false;
  }
  if (trimmed.includes("?")) {
    return true;
  }
  const lower = trimmed.toLowerCase();
  for (const candidate of questionStartCandidates(lower)) {
    if (startsWithQuestionPrefix(candidate)) {
      return true;
    }
  }
  return false;
}

/** Minimal shape for FR-006 gate (feed entry or test fixture). */
export interface QuestionGateEntry {
  kind: string;
  text?: string | null;
  sourceType?: string | null;
  prosody?: { questionScore?: number | null } | null;
}

/** Normaliza sourceType do feed para canônico; desconhecido/ausente → null (inelegível). */
export function normalizeSourceType(raw: string | null | undefined): CanonicalSourceType | null {
  if (raw == null || raw.trim() === "") {
    return null;
  }
  const s = raw.trim().toLowerCase();
  if (s === "microphone" || s === "mic") {
    return "microphone";
  }
  if (s === "system" || s === "system_audio" || s === "system-audio") {
    return "system";
  }
  return null;
}

export function isOriginEnabled(
  sourceType: CanonicalSourceType | null,
  enabled: readonly CanonicalSourceType[],
): boolean {
  if (sourceType == null) {
    return false;
  }
  return enabled.includes(sourceType);
}

/**
 * Gate multimodal FR-006 (puro, sem I/O):
 * Final AND origin enabled AND (lexical OR interviewMode system≥8 OR useProsody score≥T).
 */
export function isQuestionCandidate(
  entry: QuestionGateEntry,
  prefs: AssistantSessionPreferences,
): boolean {
  if (entry.kind !== "Final") {
    return false;
  }
  const text = entry.text?.trim() ?? "";
  const origin = normalizeSourceType(entry.sourceType);
  if (!isOriginEnabled(origin, prefs.enabledSourceTypes)) {
    return false;
  }
  if (looksLikeQuestion(text)) {
    return true;
  }
  if (prefs.interviewMode && origin === "system" && text.length >= 8) {
    return true;
  }
  if (prefs.useProsody) {
    const score = entry.prosody?.questionScore;
    if (typeof score === "number" && !Number.isNaN(score) && score >= prefs.prosodyThreshold) {
      return true;
    }
  }
  return false;
}

export function shouldAutoAnswerFromEntry(
  entry: TranscriptFeedEntry,
  prefs: AssistantSessionPreferences,
): boolean {
  return isQuestionCandidate(entry, prefs);
}

export function extractNewQuestions(
  entries: TranscriptFeedEntry[],
  seenEventIds: ReadonlySet<string>,
  prefs: AssistantSessionPreferences = DEFAULT_ASSISTANT_PREFS,
): QuestionCandidate[] {
  const out: QuestionCandidate[] = [];
  for (const entry of entries) {
    if (seenEventIds.has(entry.eventId)) {
      continue;
    }
    if (!shouldAutoAnswerFromEntry(entry, prefs)) {
      continue;
    }
    out.push({
      eventId: entry.eventId,
      text: entry.text.trim(),
      channelId: entry.channelId,
      sourceType: normalizeSourceType(entry.sourceType),
    });
  }
  return out;
}

/**
 * Monta input do invoke (019 FR-022–024 + 028 contexto rotulado / instrução entrevista).
 * question-only: sem contexto; com interviewMode ainda prefixa instrução (028 FR-003).
 */
export function buildInvokeInput(
  question: string,
  recentFinals: readonly RecentFinalSegment[],
  inputMode: InputMode,
  options: BuildInvokeInputOptions = {},
): string {
  const excludeEventId = options.excludeEventId;
  const includeMic = options.includeMicrophoneInContext !== false;
  const interviewMode = Boolean(options.interviewMode);

  if (inputMode === "question-only") {
    return withInterviewInstruction(question, interviewMode);
  }

  const prior = recentFinals.filter((f) => {
    if (f.eventId === excludeEventId) {
      return false;
    }
    const origin = f.sourceType;
    if (origin !== "system" && origin !== "microphone") {
      return false; // FR-007b: omit unknown
    }
    if (origin === "microphone" && !includeMic) {
      return false;
    }
    return true;
  });

  // Mais recentes no fim → pega últimos N; labels contam no orçamento de chars.
  const window: { label: string; text: string }[] = [];
  let chars = 0;
  for (let i = prior.length - 1; i >= 0 && window.length < MAX_CONTEXT_FINAL_SEGMENTS; i--) {
    const t = prior[i].text.trim();
    if (!t) {
      continue;
    }
    const origin = prior[i].sourceType as CanonicalSourceType;
    const label = contextLabelFor(origin);
    const lineBody = `${label}: ${t}`;
    if (chars + lineBody.length > MAX_CONTEXT_CHARS && window.length > 0) {
      break;
    }
    window.unshift({ label, text: t });
    chars += lineBody.length;
  }

  let body: string;
  if (window.length === 0) {
    body = question;
  } else {
    body = [
      "Contexto recente do transcript:",
      ...window.map((w, i) => `${i + 1}. ${w.label}: ${w.text}`),
      "",
      "Pergunta atual:",
      question,
    ].join("\n");
  }
  return withInterviewInstruction(body, interviewMode);
}

export class AssistantAutoController {
  private prefs: AssistantSessionPreferences = clonePrefs(DEFAULT_ASSISTANT_PREFS);
  private turns: AssistantTurn[] = [];
  private seenEventIds = new Set<string>();
  private recentFinals: RecentFinalSegment[] = [];
  private generation = 0;
  private runningTurnId: string | null = null;
  private conflict: AssistantConflict | null = null;
  private queued: QuestionCandidate | null = null;
  private controlsDisabled = false;
  private sessionHint: string | null = null;
  private readonly invoke: AssistantAutoDeps["invoke"];
  private readonly createId: () => string;
  private onChange: ((view: AssistantAutoView) => void) | null = null;

  constructor(deps: AssistantAutoDeps) {
    this.invoke = deps.invoke;
    this.createId = deps.createId ?? (() => crypto.randomUUID());
  }

  setOnChange(handler: (view: AssistantAutoView) => void): void {
    this.onChange = handler;
  }

  getView(): AssistantAutoView {
    return {
      enabled: this.prefs.autoEnabled,
      prefs: clonePrefs(this.prefs),
      turns: [...this.turns],
      conflict: this.conflict,
      busy: this.runningTurnId !== null,
      controlsDisabled: this.controlsDisabled,
      sessionHint: this.sessionHint,
    };
  }

  setPrefs(prefs: AssistantSessionPreferences): void {
    this.prefs = clonePrefs(prefs);
    this.emit();
  }

  getPrefs(): AssistantSessionPreferences {
    return clonePrefs(this.prefs);
  }

  setEnabled(enabled: boolean): void {
    this.prefs = { ...this.prefs, autoEnabled: enabled };
    this.emit();
  }

  setControlsDisabled(disabled: boolean, hint: string | null = null): void {
    // Idempotente: paintAssistant/onChange pode reaplicar os guards sem reentrar em emit.
    if (this.controlsDisabled === disabled && this.sessionHint === hint) {
      return;
    }
    this.controlsDisabled = disabled;
    this.sessionHint = hint;
    this.emit();
  }

  /** Zera turns/seen ao trocar de sessão (histórico só na sessão corrente na UI). */
  resetSessionState(): void {
    this.turns = [];
    this.seenEventIds = new Set();
    this.recentFinals = [];
    this.generation += 1;
    this.runningTurnId = null;
    this.conflict = null;
    this.queued = null;
    this.emit();
  }

  /** Marca eventos já vistos sem disparar (ex.: hidratar feed histórico no boot). */
  markSeen(entries: TranscriptFeedEntry[]): void {
    for (const entry of entries) {
      this.seenEventIds.add(entry.eventId);
      if (entry.kind === "Final" && entry.text?.trim()) {
        this.trackFinal(
          entry.eventId,
          entry.text.trim(),
          normalizeSourceType(entry.sourceType),
        );
      }
    }
  }

  /** Consome o feed; só dispara em trechos Final novos elegíveis com automático ligado. */
  ingestTranscript(entries: TranscriptFeedEntry[]): void {
    for (const entry of entries) {
      if (entry.kind === "Final" && entry.text?.trim()) {
        this.trackFinal(
          entry.eventId,
          entry.text.trim(),
          normalizeSourceType(entry.sourceType),
        );
      }
    }
    const candidates = extractNewQuestions(entries, this.seenEventIds, this.prefs);
    for (const c of candidates) {
      this.seenEventIds.add(c.eventId);
    }
    // Também marca não-candidatos Final/Partial como vistos para idempotência
    for (const entry of entries) {
      this.seenEventIds.add(entry.eventId);
    }
    if (!this.prefs.autoEnabled || this.controlsDisabled || candidates.length === 0) {
      this.emit();
      return;
    }
    for (const candidate of candidates) {
      this.handleIncoming(candidate);
    }
    this.emit();
  }

  resolveConflict(choice: ConflictChoice): void {
    if (!this.conflict) {
      return;
    }
    const incoming = this.conflict.incoming;
    if (choice === "cancel") {
      this.cancelRunning();
      this.conflict = null;
      this.queued = null;
      void this.startTurn(incoming);
      return;
    }
    // wait: enfileira a nova e fecha o diálogo. Se A ainda roda, o finally de startTurn
    // chama drainQueue. Se A já terminou com o diálogo aberto, drainQueue no finally
    // retornou cedo (conflict != null) — drenar agora (FR-009 / SC-004 / T041).
    this.queued = incoming;
    this.conflict = null;
    this.ensureQueuedTurn(incoming);
    this.emit();
    if (this.runningTurnId === null) {
      this.drainQueue();
    }
  }

  private trackFinal(
    eventId: string,
    text: string,
    sourceType: CanonicalSourceType | null,
  ): void {
    if (this.recentFinals.some((f) => f.eventId === eventId)) {
      return;
    }
    this.recentFinals.push({ eventId, text, sourceType });
    // Limite generoso em memória; builder aplica 12/4000
    if (this.recentFinals.length > 200) {
      this.recentFinals = this.recentFinals.slice(-100);
    }
  }

  private handleIncoming(candidate: QuestionCandidate): void {
    if (this.runningTurnId === null && this.conflict === null) {
      void this.startTurn(candidate);
      return;
    }
    const running = this.turns.find((t) => t.id === this.runningTurnId);
    this.conflict = {
      runningTurnId: this.runningTurnId ?? this.conflict?.runningTurnId ?? "",
      runningQuestion: running?.question ?? this.conflict?.runningQuestion ?? "(em andamento)",
      incoming: candidate,
    };
    this.queued = candidate;
    this.ensureQueuedTurn(candidate);
  }

  private ensureQueuedTurn(candidate: QuestionCandidate): void {
    const existingQueued = this.turns.find((t) => t.status === "queued");
    if (existingQueued) {
      existingQueued.question = candidate.text;
      existingQueued.eventId = candidate.eventId;
      existingQueued.channelId = candidate.channelId;
      return;
    }
    this.turns = [
      ...this.turns,
      {
        id: this.createId(),
        question: candidate.text,
        eventId: candidate.eventId,
        channelId: candidate.channelId,
        status: "queued",
        answer: null,
        error: null,
        providerId: null,
        latencyMs: null,
      },
    ];
  }

  private cancelRunning(): void {
    this.generation += 1;
    if (this.runningTurnId) {
      const turn = this.turns.find((t) => t.id === this.runningTurnId);
      if (turn && turn.status === "running") {
        turn.status = "cancelled";
        turn.error = "cancelada por nova pergunta";
      }
    }
    this.runningTurnId = null;
    this.turns = this.turns.filter((t) => t.status !== "queued");
  }

  private async startTurn(candidate: QuestionCandidate): Promise<void> {
    this.turns = this.turns.filter(
      (t) => !(t.status === "queued" && (t.eventId === candidate.eventId || t.question === candidate.text)),
    );

    const turnId = this.createId();
    const generation = ++this.generation;
    const turn: AssistantTurn = {
      id: turnId,
      question: candidate.text,
      eventId: candidate.eventId,
      channelId: candidate.channelId,
      status: "running",
      answer: null,
      error: null,
      providerId: null,
      latencyMs: null,
    };
    this.turns = [...this.turns, turn];
    this.runningTurnId = turnId;
    this.queued = null;
    this.emit();

    const input = buildInvokeInput(
      candidate.text,
      this.recentFinals,
      this.prefs.inputMode,
      {
        excludeEventId: candidate.eventId,
        includeMicrophoneInContext: this.prefs.includeMicrophoneInContext,
        interviewMode: this.prefs.interviewMode,
      },
    );

    try {
      const result = await this.invoke(input);
      if (generation !== this.generation) {
        return;
      }
      const current = this.turns.find((t) => t.id === turnId);
      if (!current) {
        return;
      }
      if (result.success) {
        current.status = "done";
        current.answer = result.output ?? "";
        current.providerId = result.providerId;
        current.latencyMs = result.latencyMs;
      } else {
        current.status = "error";
        current.error = result.message ?? result.errorType ?? "falha na invocação";
        current.providerId = result.providerId;
        current.latencyMs = result.latencyMs;
      }
    } catch (error) {
      if (generation !== this.generation) {
        return;
      }
      const current = this.turns.find((t) => t.id === turnId);
      if (current) {
        current.status = "error";
        current.error = String(error);
      }
    } finally {
      if (generation === this.generation) {
        this.runningTurnId = null;
        this.emit();
        this.drainQueue();
      }
    }
  }

  private drainQueue(): void {
    if (this.conflict) {
      return;
    }
    if (!this.queued) {
      const next = this.turns.find((t) => t.status === "queued");
      if (!next) {
        return;
      }
      void this.startTurn({
        eventId: next.eventId,
        text: next.question,
        channelId: next.channelId,
        sourceType: null,
      });
      return;
    }
    const next = this.queued;
    this.queued = null;
    void this.startTurn(next);
  }

  private emit(): void {
    this.onChange?.(this.getView());
  }
}
