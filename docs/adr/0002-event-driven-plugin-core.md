# ADR-0002 — Core orientado a eventos e plugins

- Status: aceito
- Data: 2026-07-16

## Contexto

O produto precisa evoluir de áudio para vídeo, tela, memória e diferentes provedores sem tornar o core um conjunto de condicionais.

## Decisão

O core gerencia sessões, perfis, registro de plugins e eventos. Capacidades específicas ficam em plugins que publicam e consomem contratos versionados.

## Consequências

- plugins podem evoluir com maior independência;
- eventos fornecem auditoria e replay;
- contratos e compatibilidade exigem disciplina desde o início.
