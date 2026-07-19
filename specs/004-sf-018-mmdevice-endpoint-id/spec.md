# SF-018 — Identidade persistente via MMDevice endpoint ID

**Issue:** #8 (ou equivalente)  
**Umbrella:** `specs/001-streaming-foundation/`  
**ADR:** `docs/adr/0011-mmdevice-endpoint-identity.md`  
**Status:** implementação presente no código; validação Windows e formalização SDD pendentes

## Problema

Índices PortAudio mudam após reboot, hot-plug, Bluetooth e atualização de driver. Perfis baseados só em `index` / `nameRegex` / `default` podem capturar o dispositivo errado sem erro explícito.

## Objetivo

Permitir que canais de áudio sejam resolvidos de forma estável pelo MMDevice endpoint ID do Windows, preservando compatibilidade com seletores antigos e propagando `endpointId` no contrato `transcript-event.v2`.

## Escopo

- Provider MMDevice (`pycaw`/`comtypes`) apenas em Windows; provider nulo fora do Windows.
- Correlação estrutural endpoint ↔ índice PortAudio (WASAPI, fluxo, FriendlyName, ordem de enumeração).
- Seletor de perfil `device.endpointId` com prioridade sobre `index` e `default`/`nameRegex`.
- Campo aditivo opcional/anulável `device.endpointId` no evento v2 e no WebSocket de áudio.
- Erros distintos e acionáveis: endpoint inexistente, inativo, fluxo incompatível, ativo sem correlação.
- Testes unitários em Linux com fakes; validação manual Windows documentada.

## Fora de escopo

- Listener de hot-plug nativo (SF-019).
- Captura por processo/aplicativo (SF-020).
- Breaking change do schema (v3).
- Fallback silencioso de `endpointId` para `index`/`name` quando a resolução falha.

## Requisitos funcionais

1. `list-devices` inclui `endpointId` correlacionado quando possível.
2. Perfil com `endpointId` resolve o índice PortAudio **atual** no início da captura.
3. Loopback usa o endpoint `eRender` original (dispositivo `[Loopback]` correlaciona ao render).
4. Perfis legados (`index`, `nameRegex`, `default`) continuam válidos.
5. `endpointId` pode coexistir com `index` no YAML (agentes antigos ignoram a chave nova).
6. Evento v2 e query do WebSocket transportam `endpointId` quando conhecido.

## Requisitos não funcionais

- Sem dependência de hardware nos testes CI Linux.
- Dependência `pycaw` restrita a `sys_platform == 'win32'`.
- Logs sem segredos; mensagens de erro com alternativas úteis (`list-devices --json`).

## Critérios de aceite

- [ ] `endpointId` é usado para abrir o stream (não apenas metadado decorativo).
- [ ] ID inexistente, endpoint inativo e endpoint ativo sem correlação produzem mensagens distintas.
- [ ] Loopback seleciona pelo endpoint render original.
- [ ] Perfis antigos permanecem funcionais.
- [ ] Schema v2 permanece compatível (campo opcional/anulável).
- [ ] Provider Windows falha de modo explícito quando `endpointId` foi pedido e não resolve.
- [ ] Testes automatizados não dependem de dispositivo físico.
- [ ] Evidência Windows em `docs/validation/sf-018-windows.md` com PASS.

## Riscos

- Correlação por nome + ordem é heurística; nomes duplicados geram WARNING e desempate por enumeração.
- Endpoint ID pode mudar se o driver for reinstalado.
- TOCTOU entre enumeração e abertura do stream (mitigação parcial na SF-019).
