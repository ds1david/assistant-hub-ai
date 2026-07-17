# ADR-0009 — Executável desktop e instalador Windows

- Status: proposto
- Data: 2026-07-17

## Contexto

O fluxo WSL-first é adequado ao desenvolvimento, mas não oferece uma experiência de produto para usuários que esperam instalar e iniciar a aplicação pelo Windows.

## Decisão proposta

Adotar Tauri 2 como shell desktop e gerar instaladores Windows NSIS como distribuição principal, mantendo MSI como alternativa. Processos nativos, como o agente WASAPI, serão empacotados como sidecars.

O modo de desenvolvimento WSL/Docker continuará suportado e não será substituído pelo desktop shell.

## Consequências

### Positivas

- executável leve;
- integração nativa com bandeja, janelas e ciclo de vida;
- empacotamento de sidecars;
- instaladores padronizados;
- fronteira clara entre interface e runtimes de IA.

### Negativas

- novo toolchain Rust/Node;
- build e assinatura Windows no CI;
- necessidade de coordenar atualizações de vários binários;
- runtime GPU continuará opcional e mais complexo que o modo Lite.

## Alternativas consideradas

- Electron: mais simples para equipes web, porém mais pesado;
- JavaFX: integração natural com Java, porém menos conveniente para sidecars e distribuição moderna;
- manter apenas WSL: rejeitado para distribuição a usuários finais.
