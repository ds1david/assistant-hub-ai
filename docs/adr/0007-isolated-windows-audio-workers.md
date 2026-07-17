# ADR 0007 — Isolar cada endpoint WASAPI em processo próprio

## Status

Aceito.

## Contexto

A captura simultânea de microfone e loopback em threads que compartilham o mesmo runtime PortAudio apresentou encerramentos nativos silenciosos no Windows. O sintoma observado foi o comando `assistant-hub-audio run` retornar ao PowerShell depois de poucos segundos, sem traceback Python e com apenas um canal conectado.

Drivers de conference cams, Bluetooth e endpoints WASAPI heterogêneos não oferecem estabilidade suficiente para compartilhar estado nativo de PortAudio no mesmo processo.

## Decisão

O comando `run` será um supervisor foreground. Para cada canal habilitado ele inicia um subprocesso Python independente por meio de:

```text
python -m assistant_hub_audio.main _worker ...
```

Cada worker:

- inicializa sua própria instância de PyAudio/PortAudio;
- resolve exatamente um endpoint;
- abre exatamente um stream;
- mantém uma conexão WebSocket própria;
- grava um WAV próprio, quando habilitado.

O supervisor:

- inicia os workers de forma escalonada;
- permanece ativo até `Ctrl+C`;
- verifica continuamente os códigos de saída;
- encerra os outros workers quando um canal falha;
- apresenta canal, PID e código de saída nativo.

## Consequências

### Positivas

- isolamento de falhas nativas por endpoint;
- diagnóstico explícito de access violations e falhas de driver;
- nenhuma dependência do mecanismo `multiprocessing spawn` do launcher instalado;
- preservação da separação lógica por `channelId`.

### Negativas

- maior consumo de memória;
- logs intercalados de múltiplos processos;
- encerramento e observabilidade exigem um supervisor.

## Operação

`run` é foreground por padrão. Execução desacoplada do terminal usa os scripts PowerShell em `scripts/windows/`, que mantêm PID e logs.
