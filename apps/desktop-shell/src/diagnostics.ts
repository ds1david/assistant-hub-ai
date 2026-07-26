// Diagnóstico unificado do shell (issue #67) — puro, testável sem Tauri.
// Nunca inclui secrets, transcript ou tokens no relatório.

export type CheckStatus = "up" | "down" | "unknown" | "degraded";

export interface DiagnosticCheck {
  id: string;
  label: string;
  status: CheckStatus;
  detail: string;
  /** Operator-facing next step when not up. */
  nextStep?: string;
}

export interface DiagnosticSnapshot {
  generatedAt: string;
  sessionCoreBaseUrl: string;
  sttBaseUrl: string;
  activeSessionId: string | null;
  checks: DiagnosticCheck[];
}

export interface ProbeInput {
  sessionCoreBaseUrl: string;
  sttBaseUrl: string;
  activeSessionId: string | null;
  sessionCore: { ok: boolean; detail: string };
  stt: { ok: boolean; detail: string };
  agent: {
    running: boolean;
    healthy?: boolean | null;
    binarySource?: string | null;
    binaryPath?: string | null;
    agentVersion?: string | null;
    agentSessionId?: string | null;
    lastError?: string | null;
  };
  /** Shell is running ⇒ WebView host is usable. */
  shellRunning: boolean;
}

const REDACT_KEYS = /secret|token|password|authorization|api[_-]?key|bearer/i;

/** Strip keys that look sensitive from a flat JSON-ish detail string. */
export function redactDetail(detail: string): string {
  // Never allow long free-form blobs (transcript risk).
  const trimmed = detail.length > 400 ? `${detail.slice(0, 400)}…` : detail;
  return trimmed.replace(
    /(secret|token|password|authorization|api[_-]?key)\s*[:=]\s*\S+/gi,
    "$1=[redacted]",
  );
}

export function buildDiagnosticSnapshot(input: ProbeInput, now = new Date()): DiagnosticSnapshot {
  const checks: DiagnosticCheck[] = [];

  checks.push({
    id: "shell-webview",
    label: "Shell / WebView",
    status: input.shellRunning ? "up" : "unknown",
    detail: input.shellRunning
      ? "Shell em execução (WebView2/host OK se a janela abriu)"
      : "Estado do shell desconhecido",
    nextStep: input.shellRunning
      ? undefined
      : "Abra o desktop-shell (cargo tauri dev --features gui)",
  });

  checks.push({
    id: "session-core",
    label: "session-core",
    status: input.sessionCore.ok ? "up" : "down",
    detail: redactDetail(
      `${input.sessionCoreBaseUrl} — ${input.sessionCore.detail}`,
    ),
    nextStep: input.sessionCore.ok
      ? undefined
      : "Suba o session-core (./scripts/wsl/start-assistant-hub.sh ou start-session-core) e confira sessionCoreBaseUrl no shell-config.json",
  });

  checks.push({
    id: "stt",
    label: "transcription-service (STT)",
    status: input.stt.ok ? "up" : "down",
    detail: redactDetail(`${input.sttBaseUrl} — ${input.stt.detail}`),
    nextStep: input.stt.ok
      ? undefined
      : "Suba o STT (compose transcription) e confira http://localhost:8001/health",
  });

  const bin = input.agent.binarySource ?? "missing";
  const agentRunning = input.agent.running;
  const agentHealthy = input.agent.healthy !== false;
  let agentStatus: CheckStatus = "down";
  if (agentRunning && agentHealthy && bin !== "missing") {
    agentStatus = "up";
  } else if (agentRunning && !agentHealthy) {
    agentStatus = "degraded";
  } else if (bin === "missing") {
    agentStatus = "down";
  } else if (!agentRunning) {
    agentStatus = "unknown";
  }

  const agentDetailParts = [
    agentRunning ? "running" : "stopped",
    `binarySource=${bin}`,
    input.agent.agentVersion ? `version=${input.agent.agentVersion}` : null,
    input.agent.binaryPath ? `path=${input.agent.binaryPath}` : null,
    input.agent.agentSessionId ? `agentSession=${input.agent.agentSessionId}` : null,
    input.agent.lastError ? `lastError=${input.agent.lastError}` : null,
  ].filter(Boolean);

  checks.push({
    id: "agent",
    label: "Windows audio agent",
    status: agentStatus,
    detail: redactDetail(agentDetailParts.join(" · ")),
    nextStep:
      bin === "missing"
        ? "Instale/resolva assistant-hub-audio (sidecar, PATH ou ASSISTANT_HUB_AUDIO_BIN)"
        : !agentRunning
          ? "Inicie o agent no painel Agent (modo Direct) com o sessionId da UI"
          : !agentHealthy
            ? "Reinicie o agent; confira logs e versão do binário"
            : undefined,
  });

  if (input.activeSessionId) {
    checks.push({
      id: "session",
      label: "Sessão ativa (UI)",
      status: "up",
      detail: `sessionId=${input.activeSessionId}`,
    });
  } else {
    checks.push({
      id: "session",
      label: "Sessão ativa (UI)",
      status: "unknown",
      detail: "Nenhuma sessão selecionada",
      nextStep: "Crie ou selecione uma sessão no painel de sessões",
    });
  }

  return {
    generatedAt: now.toISOString(),
    sessionCoreBaseUrl: input.sessionCoreBaseUrl,
    sttBaseUrl: input.sttBaseUrl,
    activeSessionId: input.activeSessionId,
    checks,
  };
}

/** Plain-text report for clipboard — no secrets by construction. */
export function formatDiagnosticReport(snapshot: DiagnosticSnapshot): string {
  const lines: string[] = [
    "Assistant Hub AI — diagnóstico",
    `generatedAt: ${snapshot.generatedAt}`,
    `sessionCoreBaseUrl: ${snapshot.sessionCoreBaseUrl}`,
    `sttBaseUrl: ${snapshot.sttBaseUrl}`,
    `activeSessionId: ${snapshot.activeSessionId ?? "(none)"}`,
    "",
    "checks:",
  ];
  for (const c of snapshot.checks) {
    lines.push(`- [${c.status.toUpperCase()}] ${c.label}: ${c.detail}`);
    if (c.nextStep) {
      lines.push(`    next: ${c.nextStep}`);
    }
  }
  lines.push("");
  lines.push("(Relatório redigido — sem secrets, tokens ou transcript.)");
  // Safety net: reject accidental secret-like lines
  return lines
    .map((line) => (REDACT_KEYS.test(line) && /[:=]\s*\S{8,}/.test(line) ? redactDetail(line) : line))
    .join("\n");
}

export const DEFAULT_STT_BASE_URL = "http://localhost:8001";
