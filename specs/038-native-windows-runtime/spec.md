# Feature Specification: Runtime nativo Windows para captura e STT

**Feature Branch**: feat/native-windows-runtime

**Created**: 2026-09-18

**Status**: Draft — aguardando Gate G1 (Spec)

**Input**: Permitir que o produto final rode integralmente no Windows 11 sem exigir WSL ou Docker em runtime, preservando WSL/Docker como ambiente de desenvolvimento enquanto for útil.

**Referências**:
- specs/002-desktop-distribution
- specs/025-r5-audio-agent-sidecar
- specs/035-realtime-stt-low-latency-pipeline
- specs/036-speech-aware-chunking-vad
- ADR-0007, ADR-0011
- Constituição P3, P8, P9 e P10

## Problema

O runtime atual depende de Windows para WASAPI e de WSL/Docker para transcription-service e session-core. Para uso diário como aplicativo Windows, essa topologia aumenta startup, troubleshooting e dependências externas.

O objetivo desta feature é uma edição desktop native-first: captura, STT e session-core executados no Windows e orquestrados pelo desktop shell, sem reescrever os componentes em outra linguagem.

## Decision Gate

Esta feature altera uma fronteira arquitetural importante. Antes de implementação MUST existir ADR aprovando o modo Windows nativo e esclarecendo a convivência com o princípio WSL-first da constituição. WSL-first continua válido para desenvolvimento até decisão explícita em contrário.

## User Scenarios & Testing

### User Story 1 - Usuário inicia o produto sem WSL/Docker (Priority: P1)

1. Given Windows 11 suportado, When o usuário inicia o desktop, Then audio agent, transcription-service e session-core podem iniciar como processos/sidecars locais.
2. Given WSL e Docker desligados, Then a edição Windows nativa continua funcional.
3. Given falha de um sidecar, Then o desktop mostra estado degradado e ação de diagnóstico/restart.

### User Story 2 - GPU local é detectada de forma explícita (Priority: P1)

1. Given NVIDIA/CUDA compatível, Then STT usa o perfil GPU configurado.
2. Given GPU indisponível, Then o runtime detecta capacidade e aplica fallback suportado ou informa claramente que o SLA realtime não pode ser garantido.
3. O produto não afirma estar usando CUDA quando estiver em CPU.

### User Story 3 - Encerramento é coordenado (Priority: P1)

Ao fechar o desktop, captura para, buffers/finais são drenados conforme política, SQLite é sincronizado e processos filhos encerram sem órfãos.

## Requirements

- **FR-001**: O runtime desktop MUST funcionar no Windows 11 x64 sem WSL/Docker.
- **FR-002**: windows-audio-agent MUST continuar Python nativo Windows e preservar isolamento por endpoint.
- **FR-003**: transcription-service MUST poder rodar Python nativo Windows com faster-whisper e CUDA quando disponível.
- **FR-004**: session-core MUST poder rodar nativamente no Windows com Java runtime suportado.
- **FR-005**: desktop-shell MUST orquestrar start, health, restart e stop dos sidecars.
- **FR-006**: Serviços MUST escutar apenas em interfaces locais por default.
- **FR-007**: Portas MUST ser configuráveis e conflitos devem gerar diagnóstico acionável.
- **FR-008**: Startup MUST verificar versão/health de cada sidecar antes de declarar Ready.
- **FR-009**: Shutdown MUST ser coordenado e respeitar finalização de transcript antes de kill forçado, dentro de timeout explícito.
- **FR-010**: Modelos grandes MUST NOT ser embutidos obrigatoriamente no instalador; cache/download deve ser gerenciado separadamente.
- **FR-011**: Ambientes Python Windows e WSL MUST permanecer independentes.
- **FR-012**: Segredos e tokens MUST usar mecanismos já aprovados de secure credentials.
- **FR-013**: WSL/Docker MAY permanecer como Developer Mode e não deve ser removido por esta feature.
- **FR-014**: A distribuição MUST registrar logs estruturais e health sem áudio bruto ou transcript sensível.
- **FR-015**: Testes automatizados de orquestração MUST usar sidecars fake; validação CUDA/WASAPI real pertence a docs/validation conforme P10.

## Success Criteria

- **SC-001**: Fluxo start → call → transcript → persist → stop funciona com WSL e Docker desligados em validação Windows.
- **SC-002**: Desktop detecta e reporta corretamente health/version de todos os sidecars.
- **SC-003**: Zero processo órfão após encerramento normal em 20 ciclos consecutivos.
- **SC-004**: Em host homologado com NVIDIA, health confirma engine CUDA e o benchmark das specs 035/036 mantém seus SLAs.
- **SC-005**: Falha deliberada do STT ou session-core gera estado degradado e recuperação/restart sem travar o desktop.
- **SC-006**: CI não depende de GPU, WASAPI físico nem Windows real para os testes de domínio/orquestração; validação manual Windows fica registrada.

## Assumptions

- Linguagens atuais são preservadas: Python para áudio/STT, Java para session-core e Tauri/TypeScript/Rust shell para desktop.
- O objetivo é remover dependência de runtime WSL/Docker, não reescrever o produto.
- O hardware alvo inicial é Windows 11 desktop/notebook moderno.

## Out of Scope

- macOS/Linux como produto final.
- Rewrite do STT em Rust.
- Embutir modelos grandes no instalador.
- Atualização automática assinada, exceto integração com infraestrutura já prevista na spec 002.
