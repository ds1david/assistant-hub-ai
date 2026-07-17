# Feature 001 — Streaming Foundation

## Objetivo

Validar que o Assistant Hub AI, desenvolvido dentro do WSL, captura no Windows e transcreve em paralelo múltiplos endpoints de áudio com diferenciação de canal e latência utilizável.

## Histórias

### US-1 — Captura multicanal

Como usuário, quero configurar microfones e saídas diferentes, mantendo cada fluxo identificado por um `channelId` lógico.

### US-2 — Perfis de hardware

Como usuário, quero alternar entre conference cam, headset Bluetooth, alto-falantes e microfones externos sem alterar código.

### US-3 — Transcrição visual

Como usuário, quero ver um painel por canal com rótulo, dispositivo, horário e latência.

### US-4 — Evidência reproduzível

Como desenvolvedor, quero um WAV separado por canal para comparar áudio original e transcrição.

### US-5 — Diagnóstico

Como desenvolvedor, quero listar dispositivos em texto ou JSON e validar um perfil antes de iniciar a captura.

### US-6 — Desenvolvimento WSL-first

Como desenvolvedor, quero trabalhar com Claude Code e VS Code dentro do WSL, mantendo apenas a captura como processo Windows.

## Critérios de aceite

1. O agente abre uma conexão WebSocket independente por canal habilitado.
2. O áudio transmitido é PCM signed 16-bit, mono, 16 kHz.
3. O serviço retorna eventos v2 com `sessionId`, `channelId`, `sourceType`, `device`, `text` e `latencyMs`.
4. O dashboard cria painéis dinamicamente por `channelId`.
5. A gravação gera um WAV válido para cada canal quando `--record-dir` é informado.
6. A perda temporária do serviço não encerra o agente; ele tenta reconectar.
7. Ao reconectar, o dispositivo do canal é resolvido novamente.
8. O comando `probe` falha para seletores ausentes ou ambíguos.
9. Nenhuma chave ou conteúdo de áudio aparece em logs.
10. O endpoint `/health` informa se o processo está ativo e se o modelo foi carregado.
11. A documentação distingue claramente comandos WSL e Windows.
12. `run` permanece em foreground e utiliza `INFO` por padrão.
13. O canal de microfone aceita noise gate configurável por perfil.
14. Transcrições de microfone semelhantes ao áudio remoto recente podem ser suprimidas sem eliminar fala local não relacionada.
15. O vocabulário Whisper pode ser ampliado por arquivo de hotwords.
16. Um script PowerShell reconstrói e inicia o Compose no WSL e abre o agente Windows em novo processo.

## Cenários obrigatórios de validação

1. microfone padrão + saída padrão;
2. microfone da conference cam + saída da conference cam;
3. saída Bluetooth + microfone USB/conference cam separado;
4. troca ou desconexão de um dispositivo durante a execução;
5. duas entradas simultâneas com WAVs e painéis separados.

## Métricas

- latência p50 e p95 por canal;
- uso de CPU/GPU;
- taxa de trechos vazios;
- duplicações por minuto;
- tempo de recuperação após desconexão;
- quantidade de falhas de resolução de dispositivo;
- divergência entre canal esperado e dispositivo efetivamente selecionado.

## Fora de escopo

- resposta por LLM;
- detecção definitiva de fim de pergunta;
- diarização entre pessoas no mesmo canal;
- separação de aplicativos que usam o mesmo endpoint;
- identidade persistente por MMDevice endpoint ID;
- persistência em banco;
- captura de tela.
