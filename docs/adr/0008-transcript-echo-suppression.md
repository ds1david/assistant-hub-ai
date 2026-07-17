# ADR 0008 — Supressão de eco na camada de transcrição

## Status

Aceito para a Streaming Foundation.

## Contexto

Microfones integrados a conference cams podem captar fisicamente o áudio emitido pelos próprios alto-falantes. O resultado é a mesma fala chegando em dois canais:

- `remote_audio`, pelo WASAPI loopback;
- `local_microphone`, pelo microfone físico.

Uma implementação completa de AEC acústico exige referência temporal de áudio, calibração e uma biblioteca nativa adequada. Isso adicionaria risco prematuro ao agente Windows.

## Decisão

Aplicar duas camadas simples e configuráveis:

1. `noiseGateDb` no canal de microfone, ainda no agente Windows;
2. deduplicação de transcrições no serviço, comparando o texto do microfone com textos recentes do canal `system` da mesma sessão.

A transcrição do loopback é considerada fonte de verdade para áudio remoto. Um texto de microfone suficientemente parecido dentro da janela temporal é descartado do feed.

## Consequências

- reduz duplicidade no dashboard sem acoplar os processos WASAPI;
- mantém suporte a fala simultânea, embora exista risco configurável de falso positivo;
- não remove o eco do arquivo WAV bruto;
- headsets continuam sendo a solução física mais confiável;
- uma futura implementação de AEC nativo pode substituir esta estratégia sem alterar os contratos de evento.
