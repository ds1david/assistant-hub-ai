# ADR 0011 — Identidade persistente de dispositivos via MMDevice endpoint ID

## Status

Aceito.

## Contexto

O agente Windows selecionava dispositivos por índice PortAudio, regex de nome ou default. Índices mudam após reboot, hot-plug USB, Bluetooth e atualização de driver, fazendo um perfil válido capturar o dispositivo errado. O PyAudioWPatch não expõe nenhum identificador persistente: os device info dictionaries contêm apenas índice, nome, host API, contagens de canais, taxas e flags de loopback.

O Windows já mantém uma identidade estável por endpoint de áudio: o MMDevice endpoint ID (`IMMDevice::GetId`), que sobrevive a reboot e a reconexão do dispositivo.

## Decisão

1. O agente obtém os endpoints via API MMDevice (`IMMDeviceEnumerator::EnumAudioEndpoints`, property store para FriendlyName), usando `pycaw` sobre `comtypes`, com dependência restrita a `sys_platform == 'win32'` e import tardio. Fora do Windows, um provider nulo degrada para `endpointId = null` sem quebrar nenhum comando.
2. Como o PortAudio não expõe o endpoint ID, a correlação endpoint ↔ índice é estrutural: somente host API WASAPI, por fluxo (`eCapture`/`eRender`), por FriendlyName, com a ordem de enumeração como desempate para nomes duplicados. Dispositivos `[Loopback]` do PyAudioWPatch correlacionam com o endpoint `eRender` original. Sem match confiável, o dispositivo fica sem endpoint ID — nunca um palpite silencioso.
3. O perfil aceita `device.endpointId`, com prioridade de seleção `endpointId > index > default`. Selecionar por endpoint ID resolve o índice PortAudio **atual** no início da captura e abre o stream por esse índice; não há fallback silencioso para índice ou nome quando o endpoint não resolve — o erro lista os endpoints disponíveis. `endpointId` pode coexistir com `index` no YAML: agentes antigos ignoram a chave desconhecida e seguem usando o índice.
4. **Mudança aditiva no contrato `transcript-event.v2`**: o objeto `device` ganha a propriedade opcional e anulável `endpointId`. `index` e `name` continuam obrigatórios; consumidores existentes ignoram o campo novo. A mudança preserva metadados do dispositivo ponta a ponta (agente → WebSocket de áudio → evento de transcrição) sem exigir uma v3.

## Consequências

### Positivas

- perfis sobrevivem a mudanças de índice entre sessões;
- erros acionáveis quando o endpoint não existe, está desabilitado/desconectado ou não correlaciona;
- lógica de correlação e seleção pura, testável em Linux/CI com providers falsos.

### Negativas e limitações

- a ponte PortAudio ↔ MMDevice depende de nome + posição de enumeração; nomes duplicados tornam o desempate heurístico (com `WARNING` explícito);
- endpoint IDs mudam se o driver for reinstalado;
- topologia pode mudar entre a enumeração e a abertura do stream (TOCTOU); o listener de hot-plug pertence à SF-019.
