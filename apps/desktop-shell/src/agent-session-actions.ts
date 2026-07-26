// Ações de agent testáveis sem Tauri (020 / 021 FR-008–FR-011).
// onSessionSelected: 020 FR-009 / 021 FR-011 (select ≠ restart).

export interface AgentProcessActions {
  start: (sessionId: string, profilePath: string) => Promise<unknown>;
  stop: () => Promise<unknown>;
}

/**
 * Reinicia o agent controlado (Direct) com a sessão ativa — sem diálogo de confirmação.
 * Guided / sem sessão: lança erro descritivo (não force-kill).
 */
export async function restartAgentWithActiveSession(
  activeSessionId: string | null,
  controlMode: "Direct" | "Guided",
  running: boolean,
  profilePath: string,
  actions: AgentProcessActions,
): Promise<void> {
  if (!activeSessionId) {
    throw new Error("selecione ou crie uma sessão ativa antes de reiniciar o agent");
  }
  if (controlMode !== "Direct") {
    throw new Error(
      "agent em modo guiado (iniciado fora do shell) — pare manualmente e inicie com o sessionId da UI",
    );
  }
  if (running) {
    await actions.stop();
  }
  await actions.start(activeSessionId, profilePath);
}

/**
 * Seleção de sessão na lista (FR-009 / FR-011(f)): atualiza só o id ativo de UI.
 * MUST NOT chamar stop/start/restart no agent — a assinatura não recebe AgentProcessActions
 * de propósito, para que a troca de sessão não possa reiniciar o processo.
 */
export function onSessionSelected(
  nextSessionId: string,
  setActiveSessionId: (id: string) => void,
): void {
  setActiveSessionId(nextSessionId);
}
