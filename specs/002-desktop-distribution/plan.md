# Plano — Desktop Distribution

## Fase 1 — Shell e ciclo de vida

- criar `apps/desktop-shell` com Tauri 2;
- abrir o dashboard local;
- iniciar e encerrar sidecars;
- adicionar ícone de bandeja e tela de diagnóstico.

## Fase 2 — Empacotamento do áudio

- gerar `assistant-hub-audio.exe` reproduzível;
- assinar e verificar o binário;
- empacotar como sidecar por arquitetura;
- mover perfis de áudio para diretório de dados do usuário.

## Fase 3 — Runtime de serviços

- empacotar o provider gateway;
- definir modo remoto, CPU e GPU;
- implementar health checks e recuperação controlada;
- impedir múltiplas instâncias conflitantes.

## Fase 4 — Instalador e atualização

- gerar NSIS como alvo principal;
- manter MSI como alternativa empresarial;
- adicionar upgrade, rollback e desinstalação;
- preparar assinatura de código e publicação no GitHub Releases.

## Fase 5 — Testes

- instalação limpa;
- upgrade entre duas versões;
- desinstalação preservando dados;
- execução sem WSL;
- execução com Docker GPU;
- dispositivos Bluetooth desconectados e reconectados.
