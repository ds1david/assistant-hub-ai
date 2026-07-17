# Arquitetura futura do AI Provider Hub

```mermaid
flowchart LR
    P[Conversation Profile] --> R[Provider Router]
    R --> C[Capability Registry]
    C --> O[Ollama Adapter]
    C --> N[NVIDIA NIM Preset]
    C --> X[OpenAI-compatible Adapter]
    C --> A[Specific Adapters]
    R --> M[Metrics and Audit]
    R --> F[Fallback Policy]
    O --> LOCAL[Local Models]
    N --> NV[Hosted or self-hosted NIM]
    X --> API[Configured Endpoint]
    A --> CLOUD[Vendor APIs]
    R --> V[Secret Resolver]
    V --> ENV[WSL Environment]
    V --> OS[Windows Secure Store]
```

## Separação de responsabilidades

### Provider registry

Mantém descritores, capacidades, estado e configuração não secreta.

### Secret resolver

Resolve `secretRef` somente no momento da chamada. O valor nunca volta para o registro nem para a interface.

### Router

Escolhe provedor/modelo conforme tarefa, perfil, política e estado do circuito.

### Adapter

Converte o contrato interno no protocolo do provedor.

### Telemetria

Registra latência, resultado, modelo, tokens e erro categorizado. Não registra prompts completos por padrão nem dados de autenticação.

## Exemplo de rota

```yaml
routes:
  live-answer:
    primary: nvidia-fast
    fallbacks: [ollama-local]
  final-summary:
    primary: cloud-quality
  embeddings:
    primary: ollama-embedding
```
