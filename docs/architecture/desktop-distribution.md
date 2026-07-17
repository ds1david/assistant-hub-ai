# Arquitetura futura de distribuição desktop

```mermaid
flowchart LR
    U[Usuário Windows] --> D[Assistant Hub AI Desktop\nTauri 2]
    D --> A[Audio Agent Sidecar\nWASAPI]
    D --> G[Provider Gateway Sidecar]
    D --> T[Transcription Runtime]
    G --> L[Modelos locais]
    G --> C[APIs de IA]
    T --> CPU[CPU empacotada]
    T --> GPU[Docker/GPU opcional]
    D --> S[Secure Credential Store]
    D --> DB[Sessões e configurações]
```

## Princípios

- o shell não implementa regras de domínio;
- sidecars têm health check e encerramento coordenado;
- segredos ficam fora dos arquivos de configuração;
- WSL permanece ambiente de desenvolvimento, não requisito universal do produto;
- modelos grandes são baixados sob demanda, nunca embutidos no instalador;
- o instalador deve ser pequeno e explicar dependências opcionais.

## Diretórios futuros

```text
apps/desktop-shell/
packages/provider-sdk-java/
services/provider-gateway/
packaging/windows/
```
