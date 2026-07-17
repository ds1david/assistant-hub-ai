# Plano — Streaming Foundation

## Incremento A — WSL-first

- documentar a fronteira WSL/Windows;
- adicionar `CLAUDE.md` e instruções de VS Code WSL;
- executar serviços e builds dentro do WSL;
- manter ambiente virtual exclusivo para o agente Windows.

## Incremento B — Perfis de áudio

- criar schema YAML simples;
- permitir canais `input` e `loopback`;
- resolver por dispositivo padrão, índice ou expressão regular;
- adicionar `list-devices --json` e `probe`;
- fornecer perfis de exemplo.

## Incremento C — Streaming multicanal

- uma conexão WebSocket por `channelId`;
- metadados do dispositivo no handshake;
- downmix e resample por canal;
- gravação WAV por canal;
- reconexão com nova resolução do endpoint.

## Incremento D — STT e visualização

- carga preguiçosa do modelo;
- janelas sobrepostas por canal;
- VAD;
- eventos `transcript.*.v2`;
- dashboard dinâmico.

## Incremento E — Qualidade de hardware

- testes manuais com conference cam e Bluetooth;
- testes unitários de perfis e conversão;
- teste de contrato WebSocket;
- métricas p50/p95;
- troubleshooting de hot-plug e Bluetooth.

## Decisões técnicas

- WebSocket binário para PCM no MVP;
- 16 kHz mono para reduzir banda e adequar a entrada do modelo;
- uma conexão por canal para preservar origem sem envelope binário adicional;
- perfis YAML para alterar hardware sem recompilar;
- CPU como padrão e GPU por override do Compose;
- endpoint ID persistente e captura por processo ficam para plugins posteriores.
