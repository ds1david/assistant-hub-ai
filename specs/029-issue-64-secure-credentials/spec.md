# Feature Specification: Secure credential store no desktop (Windows / OS keyring)

**Feature Branch**: `feature/issue-64-secure-credential-store`

**GitHub Issue**: [#64](https://github.com/ds1david/assistant-hub-ai/issues/64)

**Epic**: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)

**Created**: 2026-07-26

**Status**: Draft

**Input**: Residual 002/003 — armazenamento seguro de credenciais de provedores no desktop-shell (DPAPI / OS keyring), mantendo `secretRef` e fallback `env:` no modo Developer.

**Referências**:
- Issue [#64](https://github.com/ds1david/assistant-hub-ai/issues/64) · Epic [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)
- `specs/002-desktop-distribution/tasks.md`, `specs/003-ai-provider-hub/tasks.md`
- `docs/security/provider-secrets.md` (já prevê `os:…`)
- ADR-0010 (registry e secrets)
- `specs/015-issue-37-ai-provider-hub` (hub + `env:secretRef`)
- Constituição P1, P2, P9

## Problema

Provedores usam `secretRef` com backend **`env:`** apenas. No desktop, a expectativa de produto (002/003 e docs) é armazenar chaves no **cofre do SO**, sem arquivo de texto com a chave e sem versionar segredos. Hoje o operador precisa exportar variáveis de ambiente mesmo no shell Tauri.

## Clarifications (defaults — pipeline)

| Tema | Default |
|------|---------|
| Platform v1 | Windows Credential Manager / DPAPI via crate keyring (ou API Tauri plugin); abstração `SecureSecretStore` |
| `secretRef` scheme | `os:<logical-id>` alinhado a docs (`os:assistant-hub/nvidia/default`); `env:VAR` permanece |
| Quem resolve no invoke | **session-core** continua resolvendo `env:`; para `os:` o **shell** injeta o valor só na chamada HTTP de teste/invoke **ou** session-core ganha resolver plugável — **preferência: shell resolve `os:` e envia header/auth só no request outbound, sem persistir**; plan detalha se session-core precisa do secret no servidor local |
| Fallback | Se store OS falhar / não-Windows dev: operador usa `env:` |
| Preview | Só mascarado (já existe preview parcial) |
| Listagem | IDs lógicos sem valor |

*Nota de plan*: session-core roda em WSL/localhost e hoje resolve secrets no JVM via env. Caminho mais simples e seguro: **desktop-shell** guarda `os:`; ao testar/invocar, o shell pode (a) setar env temporário no processo de invoke se o core for local, ou (b) estender API com secret one-shot **não logado**. Plan deve escolher sem violar P9.

## User Scenarios & Testing

### User Story 1 - Salvar chave no cofre do SO (Priority: P1)

Operador cadastra provedor no shell, cola a API key uma vez; o app grava no store OS e o YAML/registro fica só com `secretRef: os:…`.

**Acceptance**:

1. **Given** shell em Windows com store disponível, **When** salva chave para provider P, **Then** nenhum arquivo de config versionável contém a chave e `secretRef` aponta `os:…`.
2. **Given** a chave salva, **When** lista/preview, **Then** vê mascarado, não o valor completo.
3. **Given** delete da chave, **When** tenta invoke com o mesmo ref, **Then** erro tipado de autenticação/ausência, sem stack com secret.

### User Story 2 - Usar chave salva no teste e live-answer (Priority: P1)

Com `os:` configurado, teste de conexão e invoke `live-answer` funcionam sem `export` manual.

**Acceptance**:

1. **Given** secret no store e provider enabled, **When** test connection, **Then** sucesso ou erro tipado do provedor (não “secret missing” se a chave existe).
2. **Given** automatic Assistente on, **When** pergunta final dispara, **Then** invoke usa o secret sem logar o valor.

### User Story 3 - Developer / WSL com env (Priority: P2)

Modo Developer continua com `env:VAR` e docs claros.

**Acceptance**:

1. **Given** só `env:OPENAI_API_KEY`, **When** core no WSL, **Then** comportamento atual preservado.
2. **Given** docs, **When** operador lê provider-secrets, **Then** vê ambos os schemes e quando usar cada um.

## Edge Cases

- Store OS indisponível (CI Linux, permissões): falha clara; fallback documentado para `env:`.
- Rotação: sobrescrever mesmo `os:id` atualiza valor.
- Export de config: `secretRef` exportado; valor nunca.
- Character set / length limits do Credential Manager.
- Múltiplos providers, ids distintos.

## Requirements

- **FR-001**: Shell MUST oferecer API de store seguro: put/get/delete/list-ids para secrets de provedor.
- **FR-002**: Configuração de provider MUST continuar usando apenas `secretRef` (nunca chave em claro no perfil YAML/JSON de providers).
- **FR-003**: Scheme `os:<logical-id>` MUST ser suportado no caminho desktop documentado em provider-secrets.md.
- **FR-004**: Scheme `env:<VAR>` MUST permanecer suportado (session-core).
- **FR-005**: UI MUST permitir salvar/atualizar/remover secret associado ao provider sem exibir valor completo após save.
- **FR-006**: Logs, exceptions, métricas e exports MUST NOT incluir o valor do secret (P9).
- **FR-007**: Teste de conexão e invoke MUST funcionar com `os:` quando o store contém a chave (ambiente Windows ou fake store em teste).
- **FR-008**: Suíte automatizada MUST cobrir fake store + redaction + ausência de secret em serialização de config; CI Linux sem OS store real.
- **FR-009**: Docs MUST descrever migração env → os e limites do modo Developer.

## Success Criteria

- **SC-001**: 100% dos testes de redaction/fake-store passam no CI sem Windows.
- **SC-002**: Roteiro Windows documentado: save key → test connection OK sem env export.
- **SC-003**: Grep/export de config de provider após save não contém a chave em claro.
- **SC-004**: `env:` path regressão: testes session-core existentes de secret/env continuam verdes.

## Out of Scope

- Vault corporativo, HSM, sync multi-device
- Custo USD
- Flags privacy de perfil de conversa (#63 residual separado)
- Auto-update / instalador

## Dependencies

- desktop-shell Tauri (014)
- AI provider hub + UI (015)
- provider-secrets.md / ADR-0010
