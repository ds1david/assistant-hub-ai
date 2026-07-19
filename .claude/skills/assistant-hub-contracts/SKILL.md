---
name: assistant-hub-contracts
description: Contratos versionados, schemas JSON e compatibilidade aditiva do Assistant Hub AI.
---

# Assistant Hub — Contratos

## Quando usar

Alterações em `contracts/**`, eventos de transcript, perfis de provider, ou qualquer payload compartilhado entre agent, serviço e futuros plugins.

## Ler primeiro

- Constituição (P4, P5)
- `contracts/transcript-event.v2.schema.json`
- ADR relacionado à mudança
- Spec ativa da feature

## Regras

1. Preferir campos **aditivos opcionais/anuláveis** até migração completa.
2. Breaking change exige ADR, versão de contrato e plano de migração explícitos.
3. Preservar `sessionId`, `channelId`, `sourceType`, `label` e `device` ponta a ponta.
4. Atualizar testes de contrato e samples no mesmo PR.
5. Não logar payload completo com conteúdo sensível.

## Checklist rápido

- [ ] Schema atualizado
- [ ] Testes produtor/consumidor
- [ ] Samples / docs
- [ ] ADR se estrutural
- [ ] Compatibilidade descrita na PR
