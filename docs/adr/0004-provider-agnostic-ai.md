# ADR-0004 — Provedores de IA abstraídos

- Status: aceito
- Data: 2026-07-16

## Contexto

Qualidade, custo, privacidade e disponibilidade variam entre modelos locais e APIs.

## Decisão

Nenhum serviço de domínio conhece SDKs específicos de fornecedores. Plugins adaptam provedores para contratos internos de chat, embeddings, visão e STT.

## Consequências

- troca e comparação de provedores;
- fallback local;
- configuração por perfil;
- maior trabalho inicial de contrato e testes de conformidade.
