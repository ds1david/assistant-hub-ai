// Seleção de sessão ativa e reconcile com list-sessions (021 / FR-001, FR-005, FR-006).

export function isSelectableSessionId(id: string): boolean {
  return id.trim().length > 0;
}

/**
 * FR-006: após listagem bem-sucedida, preserva active se ainda na lista;
 * orphan → null. MUST NOT auto-selecionar o primeiro item quando active é null.
 */
export function reconcileActiveSessionAfterList(
  activeSessionId: string | null,
  sessions: ReadonlyArray<{ id: string }>,
): string | null {
  if (activeSessionId == null || activeSessionId.trim() === "") {
    return null;
  }
  if (sessions.some((s) => s.id === activeSessionId)) {
    return activeSessionId;
  }
  return null;
}

/**
 * FR-005: create OK → ativar sem segundo clique na lista.
 * Só chama selectSession se o id for selecionável.
 */
export async function afterCreateSuccess(
  createdSessionId: string,
  selectSession: (id: string) => void | Promise<void>,
): Promise<void> {
  if (!isSelectableSessionId(createdSessionId)) {
    return;
  }
  await selectSession(createdSessionId);
}
