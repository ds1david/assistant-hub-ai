# Assistant Hub AI — instruções para agentes

## Objetivo

Construir uma plataforma local-first, modular e extensível para captura, transcrição, contexto e assistência em conversas.

## Ambiente

- workspace no filesystem Linux do WSL;
- Claude Code, Git, SDKMAN, Java, Maven, Gradle e Docker dentro do WSL;
- captura WASAPI somente no Windows;
- Python Windows e Python Linux em ambientes separados;
- fronteira local padrão em `ws://127.0.0.1:8001`.

## Arquitetura

- core independente de fornecedores de STT e LLM;
- plugins dependem do SDK, nunca o contrário;
- contratos e eventos são versionados;
- canais não são misturados antes da persistência;
- preserve `channelId`, `sourceType`, label e dispositivo;
- não registre tokens, áudio bruto ou conteúdo sensível em logs;
- capture cada endpoint WASAPI em processo isolado;
- trate saída inesperada do supervisor como erro explícito.

## Áudio e transcrição

- `run` usa log `INFO` por padrão;
- `processing.noiseGateDb` deve continuar opcional e configurável;
- o serviço pode suprimir transcrição de microfone semelhante ao áudio remoto recente;
- não suprima fala local não relacionada;
- hotwords devem ser configuráveis sem alteração de código;
- seleção de dispositivo prioriza `endpointId` MMDevice sobre índice e default (ADR-0011); índice permanece como compatibilidade;
- defaults GPU: `small`, `cuda`, `float16`.

## Qualidade

- Java: alvo Java 21, JUnit 5;
- Python: type hints, pytest e funções pequenas;
- mudanças de contrato exigem ADR/spec/testes;
- execute testes do módulo alterado.

## Comandos WSL

```bash
sdk current
mvn test
python3 -m compileall services/transcription-service/app
python3 -m compileall agents/windows-audio-agent/src
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```

## Comandos Windows

```powershell
assistant-hub-audio list-devices
assistant-hub-audio probe --profile <perfil.yaml>
assistant-hub-audio run --session teste --profile <perfil.yaml>
```

## Distribuição desktop futura

- preserve o modo WSL/Docker para desenvolvimento;
- o executável Windows será um shell, não um novo monólito de domínio;
- sidecars devem ter health check, versão e encerramento coordenado;
- não empacote modelos grandes dentro do instalador;
- instaladores e updates devem ser verificáveis e preparados para assinatura.

## Provedores de IA futuros

- configuração nunca contém a chave em claro; use `secretRef`;
- implemente primeiro um adaptador OpenAI-compatible genérico;
- NVIDIA NIM deve ser um preset configurável, não uma dependência do core;
- rotas e fallbacks pertencem ao perfil/política;
- disponibilidade gratuita, cotas e preços são metadados externos e mutáveis;
- redija authorization headers e secrets em qualquer log ou exceção.
