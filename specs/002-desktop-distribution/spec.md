# Feature 002 — Desktop Distribution

- Status: futura
- Release alvo: R5
- Prioridade: média

## Objetivo

Distribuir o Assistant Hub AI como aplicação Windows instalável, sem exigir que o usuário final conheça WSL, Python, Docker ou comandos de terminal para os fluxos básicos.

## Problema

O ambiente atual é excelente para desenvolvimento, mas depende de WSL, Docker Desktop e de um agente Python instalado no Windows. Isso aumenta a barreira para uso cotidiano e impede uma experiência semelhante a um produto desktop.

## Resultado esperado

O usuário poderá instalar, atualizar, iniciar e remover o Assistant Hub AI por meio de um instalador Windows. A aplicação oferecerá uma interface única para sessões, áudio, provedores de IA, diagnóstico e atualização.

## Escopo funcional

1. Executável desktop com ícone na bandeja do Windows.
2. Instalador por usuário, sem privilégios administrativos por padrão.
3. Opção de instalação por máquina quando explicitamente selecionada.
4. Inicialização e encerramento coordenados dos processos auxiliares.
5. Diagnóstico de microfone, loopback, GPU, rede e dependências.
6. Atualização automática assinada, com canal estável e canal de testes.
7. Exportação e importação de configuração sem segredos.
8. Logs acessíveis pela interface, com redação de tokens e conteúdo sensível.
9. Modo desenvolvedor que continua suportando WSL e Docker.

## Estratégia de empacotamento

### Shell desktop

A direção preferencial é Tauri 2 para produzir um executável leve e instaladores Windows MSI/NSIS.

### Processos auxiliares

- `assistant-hub-audio.exe`: captura WASAPI, empacotado como sidecar.
- `assistant-hub-provider-gateway.exe`: roteamento de provedores, empacotado como sidecar ou serviço local.
- runtime de transcrição:
  - modo remoto/API;
  - modo local CPU empacotado;
  - modo local GPU via runtime opcional, inicialmente Docker Desktop;
  - modo futuro nativo CUDA, se a manutenção justificar.

## Edições previstas

### Developer

- WSL + Docker Compose;
- código-fonte e ferramentas de desenvolvimento;
- comportamento atual preservado.

### Desktop Lite

- instalador Windows;
- áudio nativo;
- provedores remotos ou modelos locais leves;
- sem dependência obrigatória de WSL.

### Desktop GPU

- instalador Windows;
- integração opcional com Docker Desktop ou runtime GPU suportado;
- diagnóstico de driver, VRAM e compatibilidade antes do download de modelos.

## Critérios de aceite

1. O instalador cria e remove a aplicação sem deixar processos órfãos.
2. O executável inicia o dashboard e o agente de áudio sem terminal visível.
3. A aplicação informa claramente quando uma dependência opcional está ausente.
4. Nenhuma chave de API é armazenada em arquivo de texto pelo instalador.
5. A desinstalação oferece preservar ou remover sessões e modelos.
6. O build é reproduzível em CI Windows e gera checksum e artefatos assináveis.
7. O modo Developer continua funcionando após a introdução do desktop shell.

## Fora do escopo inicial

- Microsoft Store;
- instalação silenciosa corporativa;
- suporte macOS/Linux desktop;
- empacotar modelos GPU grandes dentro do instalador;
- instalar WSL ou Docker sem consentimento explícito.
