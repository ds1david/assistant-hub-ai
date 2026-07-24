// Texto de transcrição e metadados de sessão vêm de fala transcrita / entrada do operador —
// nunca interpolar sem escapar antes de injetar em innerHTML.
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
