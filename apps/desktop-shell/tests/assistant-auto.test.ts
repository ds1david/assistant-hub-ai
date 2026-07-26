import { describe, expect, it, vi } from "vitest";
import {
  AssistantAutoController,
  buildInvokeInput,
  CONTEXT_LABEL_MICROPHONE,
  CONTEXT_LABEL_SYSTEM,
  extractNewQuestions,
  hasMetaAssistantStyle,
  INTERVIEW_ANSWER_INSTRUCTION,
  isQuestionCandidate,
  looksLikeQuestion,
  MAX_CONTEXT_CHARS,
  normalizeSourceType,
} from "../src/assistant-auto";
import type { InvocationResult, TranscriptFeedEntry } from "../src/api-client";
import type { AssistantSessionPreferences } from "../src/assistant-prefs";

function finalEntry(overrides: Partial<TranscriptFeedEntry>): TranscriptFeedEntry {
  return {
    eventId: "e1",
    channelId: "sys-1",
    sourceType: "system",
    label: "Sistema",
    text: "Como funciona o garbage collector?",
    kind: "Final",
    occurredAt: "2026-01-01T00:00:01Z",
    ...overrides,
  };
}

function okResult(output: string): InvocationResult {
  return {
    providerId: "openai-gpt",
    model: "gpt-4o-mini",
    capability: "chat",
    sessionId: "s1",
    success: true,
    output,
    latencyMs: 10,
    occurredAt: "2026-01-01T00:00:02Z",
  };
}

const systemOnlyPrefs: AssistantSessionPreferences = {
  autoEnabled: true,
  enabledSourceTypes: ["system"],
  inputMode: "question-only",
  interviewMode: false,
  useProsody: false,
  prosodyThreshold: 0.65,
  includeMicrophoneInContext: true,
};

describe("looksLikeQuestion (FR-002)", () => {
  it("detects explicit question mark with min length", () => {
    expect(looksLikeQuestion("isso funciona de verdade?")).toBe(true);
  });

  it("detects portuguese openers", () => {
    expect(looksLikeQuestion("Como você implementaria um cache LRU")).toBe(true);
    expect(looksLikeQuestion("O que é um monólito modular")).toBe(true);
  });

  it("detects english openers", () => {
    expect(looksLikeQuestion("What is the time complexity")).toBe(true);
    expect(looksLikeQuestion("How does garbage collection work")).toBe(true);
  });

  it("detects interview-style imperatives (pt)", () => {
    expect(looksLikeQuestion("Me conte sobre um projeto relevante com Java Spring")).toBe(true);
    expect(looksLikeQuestion("Me descreva uma API REST que você implementou")).toBe(true);
    expect(looksLikeQuestion("Me fala de uma API REST que você construiu")).toBe(true);
    expect(looksLikeQuestion("Descreva o fluxo de autenticação da API")).toBe(true);
    expect(looksLikeQuestion("Em que sistema você atuava na Claro")).toBe(true);
  });

  it("detects vocative + interview opener", () => {
    expect(looksLikeQuestion("David, me conte sobre um projeto relevante")).toBe(true);
    expect(looksLikeQuestion("David, me descreva uma API REST com Spring")).toBe(true);
  });

  it("detects question after a short lead-in sentence", () => {
    expect(
      looksLikeQuestion("Claro, sem problema. Me descreva uma API REST com Java e Spring"),
    ).toBe(true);
  });

  it("detects english interview openers", () => {
    expect(looksLikeQuestion("Tell me about a relevant project you led")).toBe(true);
    expect(looksLikeQuestion("Describe an API you designed end to end")).toBe(true);
    expect(looksLikeQuestion("Walk me through your design decisions")).toBe(true);
  });

  it("rejects short or non-questions", () => {
    expect(looksLikeQuestion("ok")).toBe(false);
    expect(looksLikeQuestion("sim")).toBe(false);
    expect(looksLikeQuestion("entendi")).toBe(false);
    expect(looksLikeQuestion("Vamos seguir com o plano combinado")).toBe(false);
    expect(looksLikeQuestion("porque")).toBe(false); // < 8 chars after... actually "porque" is 6
    expect(looksLikeQuestion("abc?")).toBe(false); // < 8
    expect(looksLikeQuestion("qualidade do serviço ficou estável no mês")).toBe(false);
    expect(looksLikeQuestion("Claro, sem problema. Vamos seguir em frente")).toBe(false);
    expect(looksLikeQuestion("Perfeito, vamos praticar exatamente essa saída")).toBe(false);
  });
});

describe("origin filter (FR-002)", () => {
  it("maps system_audio to system", () => {
    expect(normalizeSourceType("system_audio")).toBe("system");
    expect(normalizeSourceType("microphone")).toBe("microphone");
    expect(normalizeSourceType(null)).toBeNull();
    expect(normalizeSourceType("unknown")).toBeNull();
  });

  it("default system-only rejects microphone questions", () => {
    const entries = [
      finalEntry({ eventId: "m1", sourceType: "microphone", text: "Como faz no mic?" }),
    ];
    expect(extractNewQuestions(entries, new Set(), systemOnlyPrefs)).toHaveLength(0);
  });

  it("unknown origin is ineligible", () => {
    const entries = [finalEntry({ eventId: "u1", sourceType: null, text: "Como faz sem origem?" })];
    expect(extractNewQuestions(entries, new Set(), systemOnlyPrefs)).toHaveLength(0);
  });

  it("allows microphone when enabled", () => {
    const prefs: AssistantSessionPreferences = {
      ...systemOnlyPrefs,
      enabledSourceTypes: ["system", "microphone"],
    };
    const entries = [
      finalEntry({ eventId: "m1", sourceType: "microphone", text: "Como faz no mic?" }),
    ];
    expect(extractNewQuestions(entries, new Set(), prefs)).toHaveLength(1);
  });
});

describe("extractNewQuestions", () => {
  it("only returns unseen Final question-like entries", () => {
    const entries = [
      finalEntry({ eventId: "e1", text: "Como funciona X?" }),
      finalEntry({ eventId: "e2", text: "afirmacao sem interrogacao aqui", kind: "Final" }),
      finalEntry({ eventId: "e3", text: "O que e Y?", kind: "Partial" }),
    ];
    const seen = new Set<string>(["e1"]);
    const got = extractNewQuestions(entries, seen, systemOnlyPrefs);
    expect(got).toHaveLength(0);
  });

  it("returns new finals with question mark", () => {
    const entries = [finalEntry({ eventId: "e9", text: "Qual a complexidade?" })];
    expect(extractNewQuestions(entries, new Set(), systemOnlyPrefs)).toEqual([
      {
        eventId: "e9",
        text: "Qual a complexidade?",
        channelId: "sys-1",
        sourceType: "system",
      },
    ]);
  });
});

describe("buildInvokeInput (028)", () => {
  const mixed = [
    { eventId: "a", text: "Resposta anterior do candidato sobre Spring", sourceType: "microphone" as const },
    { eventId: "b", text: "Pergunta do entrevistador sobre Java", sourceType: "system" as const },
    { eventId: "c", text: "Pergunta atual?", sourceType: "system" as const },
  ];

  it("question-only omits context", () => {
    const input = buildInvokeInput(
      "Pergunta?",
      [
        { eventId: "a", text: "contexto um", sourceType: "system" },
        { eventId: "b", text: "contexto dois", sourceType: "microphone" },
      ],
      "question-only",
      { excludeEventId: "b" },
    );
    expect(input).toBe("Pergunta?");
    expect(input).not.toContain("contexto");
  });

  it("question-only with interviewMode prefixes instruction", () => {
    const input = buildInvokeInput("Pergunta?", [], "question-only", {
      interviewMode: true,
    });
    expect(input).toContain(INTERVIEW_ANSWER_INSTRUCTION);
    expect(input).toContain("Pergunta?");
  });

  it("mixed finals + include mic ON contain labels and both origins", () => {
    const input = buildInvokeInput("Pergunta atual?", mixed, "question-plus-recent-context", {
      excludeEventId: "c",
      includeMicrophoneInContext: true,
    });
    expect(input).toContain("Resposta anterior do candidato sobre Spring");
    expect(input).toContain("Pergunta do entrevistador sobre Java");
    expect(input).toContain(`${CONTEXT_LABEL_MICROPHONE}:`);
    expect(input).toContain(`${CONTEXT_LABEL_SYSTEM}:`);
    expect(input).toContain("Pergunta atual?");
    expect(input).toContain("Contexto recente");
  });

  it("include mic OFF excludes microphone text", () => {
    const input = buildInvokeInput("Pergunta atual?", mixed, "question-plus-recent-context", {
      excludeEventId: "c",
      includeMicrophoneInContext: false,
    });
    expect(input).not.toContain("Resposta anterior do candidato");
    expect(input).not.toContain(CONTEXT_LABEL_MICROPHONE);
    expect(input).toContain("Pergunta do entrevistador sobre Java");
    expect(input).toContain(CONTEXT_LABEL_SYSTEM);
  });

  it("omits null/unknown sourceType from context", () => {
    const input = buildInvokeInput(
      "Q?",
      [
        { eventId: "1", text: "fantasma", sourceType: null },
        { eventId: "2", text: "sistema ok", sourceType: "system" },
      ],
      "question-plus-recent-context",
    );
    expect(input).not.toContain("fantasma");
    expect(input).toContain("sistema ok");
  });

  it("interviewMode prefixes instruction on context mode", () => {
    const input = buildInvokeInput("Pergunta atual?", mixed, "question-plus-recent-context", {
      excludeEventId: "c",
      interviewMode: true,
    });
    expect(input.startsWith(INTERVIEW_ANSWER_INSTRUCTION)).toBe(true);
    expect(input).toContain("1ª pessoa");
  });

  it("interviewMode false has no instruction block", () => {
    const input = buildInvokeInput("Pergunta atual?", mixed, "question-plus-recent-context", {
      excludeEventId: "c",
      interviewMode: false,
    });
    expect(input).not.toContain(INTERVIEW_ANSWER_INSTRUCTION);
  });

  it("respects char budget including labels", () => {
    const huge = "x".repeat(MAX_CONTEXT_CHARS);
    const input = buildInvokeInput(
      "Q?",
      [
        { eventId: "1", text: huge, sourceType: "system" },
        { eventId: "2", text: "short", sourceType: "system" },
      ],
      "question-plus-recent-context",
    );
    expect(input).toContain("Q?");
    // labeled short should fit; huge alone may exceed with label → at least question
    expect(input).toContain(CONTEXT_LABEL_SYSTEM);
  });
});

describe("hasMetaAssistantStyle (028 FR-012)", () => {
  it("detects bad meta-assistant fixtures", () => {
    expect(hasMetaAssistantStyle("Claro! Você poderia dizer que usa Spring.")).toBe(true);
    expect(hasMetaAssistantStyle("Como candidato, você deve responder com métricas.")).toBe(true);
    expect(hasMetaAssistantStyle("Responda assim: eu lidero times.")).toBe(true);
    expect(
      hasMetaAssistantStyle("- a\n- b\n- c\n- d\nmais texto"),
    ).toBe(true);
    expect(hasMetaAssistantStyle("## Título\ntexto")).toBe(true);
  });

  it("accepts good first-person speech", () => {
    expect(
      hasMetaAssistantStyle(
        "Eu liderei a migração do monólito para serviços com Spring Boot e reduzi o tempo de deploy.",
      ),
    ).toBe(false);
    expect(hasMetaAssistantStyle("No meu último projeto usei Java e mensageria assíncrona.")).toBe(
      false,
    );
  });
});

describe("AssistantAutoController", () => {
  function controllerWithInvoke(invoke: (input: string) => Promise<InvocationResult>) {
    const controller = new AssistantAutoController({
      invoke,
      createId: (() => {
        let n = 0;
        return () => `t${++n}`;
      })(),
    });
    controller.setPrefs(systemOnlyPrefs);
    return controller;
  }

  it("auto-invokes on first question when idle and enabled", async () => {
    const invoke = vi.fn().mockResolvedValue(okResult("resposta A"));
    const controller = controllerWithInvoke(invoke);

    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Como faz A?" })]);
    await vi.waitFor(() => {
      const done = controller.getView().turns.find((t) => t.status === "done");
      expect(done?.answer).toBe("resposta A");
    });
    expect(invoke).toHaveBeenCalledOnce();
    expect(invoke).toHaveBeenCalledWith("Como faz A?");
  });

  it("does not invoke when automatic mode is disabled (default)", () => {
    const invoke = vi.fn();
    const controller = new AssistantAutoController({ invoke });
    expect(controller.getView().enabled).toBe(false);
    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Como faz?" })]);
    expect(invoke).not.toHaveBeenCalled();
    expect(controller.getView().turns).toHaveLength(0);
  });

  it("setControlsDisabled is idempotent (no re-emit / no paint loop)", () => {
    const invoke = vi.fn();
    const controller = new AssistantAutoController({ invoke });
    const onChange = vi.fn();
    controller.setOnChange(onChange);

    controller.setControlsDisabled(true, "sem sessão");
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(controller.getView().controlsDisabled).toBe(true);
    expect(controller.getView().sessionHint).toBe("sem sessão");

    // Reaplicar o mesmo estado não deve emitir (evita stack overflow no shell).
    controller.setControlsDisabled(true, "sem sessão");
    expect(onChange).toHaveBeenCalledTimes(1);

    controller.setControlsDisabled(false, null);
    expect(onChange).toHaveBeenCalledTimes(2);
    expect(controller.getView().controlsDisabled).toBe(false);
    expect(controller.getView().sessionHint).toBeNull();
  });

  it("asks for conflict when a second question arrives while busy", async () => {
    let resolveFirst!: (value: InvocationResult) => void;
    const first = new Promise<InvocationResult>((resolve) => {
      resolveFirst = resolve;
    });
    const invoke = vi
      .fn()
      .mockImplementationOnce(() => first)
      .mockResolvedValueOnce(okResult("resposta B"));

    const controller = controllerWithInvoke(invoke);

    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Pergunta um?" })]);
    expect(controller.getView().busy).toBe(true);

    controller.ingestTranscript([finalEntry({ eventId: "e2", text: "Pergunta dois?" })]);
    const conflict = controller.getView().conflict;
    expect(conflict).not.toBeNull();
    expect(conflict?.incoming.text).toBe("Pergunta dois?");
    expect(conflict?.runningQuestion).toBe("Pergunta um?");

    controller.resolveConflict("cancel");
    resolveFirst(okResult("resposta A tardia"));

    await vi.waitFor(() => {
      const answers = controller.getView().turns.filter((t) => t.status === "done").map((t) => t.answer);
      expect(answers).toContain("resposta B");
    });
    const cancelled = controller.getView().turns.filter((t) => t.status === "cancelled");
    expect(cancelled.length).toBeGreaterThanOrEqual(1);
    // late A must not appear as done answer for cancelled path overwriting B
    const doneAnswers = controller
      .getView()
      .turns.filter((t) => t.status === "done")
      .map((t) => t.answer);
    expect(doneAnswers).not.toContain("resposta A tardia");
  });

  it("wait queues the new question until the current one finishes", async () => {
    let resolveFirst!: (value: InvocationResult) => void;
    const first = new Promise<InvocationResult>((resolve) => {
      resolveFirst = resolve;
    });
    const invoke = vi
      .fn()
      .mockImplementationOnce(() => first)
      .mockResolvedValueOnce(okResult("resposta B"));

    const controller = controllerWithInvoke(invoke);

    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Pergunta um?" })]);
    controller.ingestTranscript([finalEntry({ eventId: "e2", text: "Pergunta dois?" })]);
    controller.resolveConflict("wait");
    expect(controller.getView().conflict).toBeNull();
    expect(controller.getView().turns.some((t) => t.status === "queued")).toBe(true);

    resolveFirst(okResult("resposta A"));
    await vi.waitFor(() => {
      const done = controller.getView().turns.filter((t) => t.status === "done");
      expect(done.map((t) => t.answer).sort()).toEqual(["resposta A", "resposta B"]);
    });
    expect(invoke).toHaveBeenCalledTimes(2);
  });

  it("reopens conflict when C arrives after wait while still running", async () => {
    let resolveFirst!: (value: InvocationResult) => void;
    const first = new Promise<InvocationResult>((resolve) => {
      resolveFirst = resolve;
    });
    const invoke = vi.fn().mockImplementation(() => first);

    const controller = controllerWithInvoke(invoke);
    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Pergunta um?" })]);
    controller.ingestTranscript([finalEntry({ eventId: "e2", text: "Pergunta dois?" })]);
    controller.resolveConflict("wait");
    expect(controller.getView().turns.some((t) => t.status === "queued")).toBe(true);

    controller.ingestTranscript([finalEntry({ eventId: "e3", text: "Pergunta tres?" })]);
    const conflict = controller.getView().conflict;
    expect(conflict).not.toBeNull();
    expect(conflict?.incoming.text).toBe("Pergunta tres?");
    resolveFirst(okResult("done"));
  });

  it("idempotent on same eventId", async () => {
    const invoke = vi.fn().mockResolvedValue(okResult("ok"));
    const controller = controllerWithInvoke(invoke);
    const entry = finalEntry({ eventId: "same", text: "Como repete?" });
    controller.ingestTranscript([entry]);
    await vi.waitFor(() => expect(invoke).toHaveBeenCalledTimes(1));
    controller.ingestTranscript([entry]);
    expect(invoke).toHaveBeenCalledTimes(1);
  });

  it("028: mic Final non-candidate is tracked and enters next invoke context", async () => {
    const invoke = vi.fn().mockResolvedValue(okResult("ok"));
    const controller = controllerWithInvoke(invoke);
    controller.setPrefs({
      ...systemOnlyPrefs,
      inputMode: "question-plus-recent-context",
      includeMicrophoneInContext: true,
      interviewMode: false,
    });
    // Mic speech — not a trigger with system-only origins
    controller.ingestTranscript([
      finalEntry({
        eventId: "mic1",
        text: "Eu usei Spring Boot no meu ultimo projeto",
        sourceType: "microphone",
        channelId: "mic-1",
      }),
    ]);
    expect(invoke).not.toHaveBeenCalled();
    expect(controller.getView().turns).toHaveLength(0);

    controller.ingestTranscript([
      finalEntry({
        eventId: "sys1",
        text: "Me conte sobre um projeto relevante com Java?",
        sourceType: "system",
      }),
    ]);
    await vi.waitFor(() => expect(invoke).toHaveBeenCalled());
    const input = invoke.mock.calls[0][0] as string;
    expect(input).toContain("Eu usei Spring Boot");
    expect(input).toContain(CONTEXT_LABEL_MICROPHONE);
  });

  it("028: microphone-only Final does not create turn with default origins", () => {
    const invoke = vi.fn();
    const controller = controllerWithInvoke(invoke);
    controller.ingestTranscript([
      finalEntry({
        eventId: "m1",
        text: "Como eu deveria responder essa pergunta?",
        sourceType: "microphone",
      }),
    ]);
    expect(invoke).not.toHaveBeenCalled();
    expect(controller.getView().turns).toHaveLength(0);
  });

  it("028: partial never creates turn", () => {
    const invoke = vi.fn();
    const controller = controllerWithInvoke(invoke);
    controller.ingestTranscript([
      {
        eventId: "p1",
        channelId: "sys-1",
        sourceType: "system",
        label: "Sistema",
        text: "Como funciona o garbage collector?",
        kind: "Partial",
        occurredAt: "2026-01-01T00:00:01Z",
      },
    ]);
    expect(invoke).not.toHaveBeenCalled();
    expect(controller.getView().turns).toHaveLength(0);
  });

  it("028 FR-012b: keeps raw model output even if meta style", async () => {
    const bad = "Claro! Você poderia dizer que lidera times.";
    const invoke = vi.fn().mockResolvedValue(okResult(bad));
    const controller = controllerWithInvoke(invoke);
    controller.setPrefs({ ...systemOnlyPrefs, interviewMode: true });
    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Me conte sobre lideranca?" })]);
    await vi.waitFor(() => {
      const done = controller.getView().turns.find((t) => t.status === "done");
      expect(done?.answer).toBe(bad);
    });
    expect(hasMetaAssistantStyle(bad)).toBe(true);
  });

  it("wait after A finished with dialog still open starts B (T041 / FR-009)", async () => {
    let resolveFirst!: (value: InvocationResult) => void;
    const first = new Promise<InvocationResult>((resolve) => {
      resolveFirst = resolve;
    });
    const invoke = vi
      .fn()
      .mockImplementationOnce(() => first)
      .mockResolvedValueOnce(okResult("resposta B"));

    const controller = controllerWithInvoke(invoke);
    controller.ingestTranscript([finalEntry({ eventId: "e1", text: "Pergunta um?" })]);
    controller.ingestTranscript([finalEntry({ eventId: "e2", text: "Pergunta dois?" })]);
    expect(controller.getView().conflict).not.toBeNull();

    // A conclui com o diálogo ainda aberto (drainQueue no-op por conflict)
    resolveFirst(okResult("resposta A"));
    await vi.waitFor(() => {
      expect(controller.getView().busy).toBe(false);
      expect(controller.getView().turns.some((t) => t.status === "done" && t.answer === "resposta A")).toBe(
        true,
      );
    });
    expect(controller.getView().conflict).not.toBeNull();
    expect(invoke).toHaveBeenCalledTimes(1);

    // Operador só então escolhe Aguardar → B deve iniciar sem novo diálogo
    controller.resolveConflict("wait");
    expect(controller.getView().conflict).toBeNull();
    await vi.waitFor(() => {
      const done = controller.getView().turns.filter((t) => t.status === "done");
      expect(done.map((t) => t.answer).sort()).toEqual(["resposta A", "resposta B"]);
    });
    expect(invoke).toHaveBeenCalledTimes(2);
  });
});

describe("isQuestionCandidate (FR-006 gate)", () => {
  const basePrefs: AssistantSessionPreferences = { ...systemOnlyPrefs };

  it("rejects partials even with interrogative text", () => {
    expect(
      isQuestionCandidate(
        { kind: "Partial", text: "Me conte sobre um projeto relevante com Java", sourceType: "system" },
        basePrefs,
      ),
    ).toBe(false);
  });

  it("accepts lexical interview finals (FR-002)", () => {
    expect(
      isQuestionCandidate(
        {
          kind: "Final",
          text: "Me conte sobre um projeto relevante com Java Spring",
          sourceType: "system",
        },
        basePrefs,
      ),
    ).toBe(true);
  });

  it("interviewMode accepts system Final without prefix; not microphone", () => {
    const prefs: AssistantSessionPreferences = { ...basePrefs, interviewMode: true };
    const text = "Sobre o projeto na Claro, fale do seu papel.";
    expect(
      isQuestionCandidate({ kind: "Final", text, sourceType: "system" }, prefs),
    ).toBe(true);
    expect(
      isQuestionCandidate({ kind: "Final", text, sourceType: "microphone" }, prefs),
    ).toBe(false);
    expect(
      isQuestionCandidate({ kind: "Final", text, sourceType: "system" }, basePrefs),
    ).toBe(false);
  });

  it("useProsody accepts high score when enabled; ignores when off", () => {
    const text = "Voce ja usou Spring Boot em producao";
    const entry = {
      kind: "Final",
      text,
      sourceType: "system" as const,
      prosody: { questionScore: 0.9 },
    };
    expect(isQuestionCandidate(entry, basePrefs)).toBe(false);
    expect(
      isQuestionCandidate(entry, { ...basePrefs, useProsody: true, prosodyThreshold: 0.65 }),
    ).toBe(true);
    expect(
      isQuestionCandidate(entry, { ...basePrefs, useProsody: true, prosodyThreshold: 0.95 }),
    ).toBe(false);
  });

  it("extractNewQuestions respects interviewMode", () => {
    const prefs: AssistantSessionPreferences = { ...systemOnlyPrefs, interviewMode: true };
    const entries = [
      finalEntry({
        eventId: "iv1",
        text: "Sobre o projeto na Claro, fale do seu papel.",
        sourceType: "system",
      }),
    ];
    expect(extractNewQuestions(entries, new Set(), systemOnlyPrefs)).toHaveLength(0);
    expect(extractNewQuestions(entries, new Set(), prefs)).toHaveLength(1);
  });
});
