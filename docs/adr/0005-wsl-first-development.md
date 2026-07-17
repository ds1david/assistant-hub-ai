# ADR-0005 — Ambiente de desenvolvimento WSL-first

- Status: aceito
- Data: 2026-07-16

## Contexto

O desenvolvimento será feito com VS Code e Claude Code, usando toolchains Linux, enquanto a captura real depende das APIs de áudio do Windows.

## Decisão

- manter o repositório no sistema de arquivos Linux do WSL;
- executar Claude Code, Java, Maven, serviços Python e Docker dentro do WSL;
- executar somente o agente de captura como processo nativo do Windows;
- comunicar Windows e WSL por contratos de rede em `localhost`;
- manter ambientes virtuais Python separados para Windows e Linux.

## Consequências

- o ciclo de desenvolvimento principal fica consistente e rápido;
- a fronteira Windows/WSL torna-se explícita e testável;
- testes de hardware exigem um processo Windows separado;
- scripts e documentação devem indicar claramente em qual ambiente cada comando roda.
