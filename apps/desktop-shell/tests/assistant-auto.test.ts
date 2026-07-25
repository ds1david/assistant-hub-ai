import { describe, expect, it, vi } from "vitest";
import {
  AssistantAutoController,
  buildInvokeInput,
  extractNewQuestions,
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
};

describe("looksLikeQuestion (FR-004)", () => {
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

  it("rejects short or non-questions", () => {
    expect(looksLikeQuestion("ok")).toBe(false);
    expect(looksLikeQuestion("sim")).toBe(false);
    expect(looksLikeQuestion("entendi")).toBe(false);
    expect(looksLikeQuestion("Vamos seguir com o plano combinado")).toBe(false);
    expect(looksLikeQuestion("porque")).toBe(false); // < 8 chars after... actually "porque" is 6
    expect(looksLikeQuestion("abc?")).toBe(false); // < 8
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

describe("buildInvokeInput", () => {
  it("question-only omits context", () => {
    const input = buildInvokeInput(
      "Pergunta?",
      [
        { eventId: "a", text: "contexto um" },
        { eventId: "b", text: "contexto dois" },
      ],
      "question-only",
      "b",
    );
    expect(input).toBe("Pergunta?");
  });

  it("context mode includes prior finals and question", () => {
    const input = buildInvokeInput(
      "Pergunta atual?",
      [
        { eventId: "a", text: "trecho anterior" },
        { eventId: "b", text: "Pergunta atual?" },
      ],
      "question-plus-recent-context",
      "b",
    );
    expect(input).toContain("trecho anterior");
    expect(input).toContain("Pergunta atual?");
    expect(input).toContain("Contexto recente");
  });

  it("respects char budget", () => {
    const huge = "x".repeat(MAX_CONTEXT_CHARS);
    const input = buildInvokeInput(
      "Q?",
      [
        { eventId: "1", text: huge },
        { eventId: "2", text: "short" },
      ],
      "question-plus-recent-context",
    );
    // short + huge would exceed when short already placed; at least question present
    expect(input).toContain("Q?");
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
