# Plano — AI Provider Hub

## Fase 1 — Contratos

- definir `AiProvider`, `ModelDescriptor`, `InferenceRequest` e `InferenceResult`;
- versionar schema de configuração;
- implementar validação e redação de segredos;
- adicionar testes de conformidade.

## Fase 2 — Gateway

- criar provider gateway independente do domínio;
- implementar streaming, timeout, retry e circuit breaker;
- publicar métricas e eventos de auditoria;
- suportar fallback orientado por política.

## Fase 3 — Adaptadores

- Ollama;
- OpenAI-compatible genérico;
- NVIDIA NIM hosted;
- adaptadores específicos somente quando houver diferença real de contrato.

## Fase 4 — Interface

- lista de provedores;
- editor de configuração;
- seletor de modelos;
- teste de conexão;
- visualização de capacidades, latência e falhas;
- mapeamento por perfil/persona.

## Fase 5 — Segurança e distribuição

- integração com armazenamento seguro no desktop;
- suporte `env:` no WSL;
- exportação sem segredos;
- migração segura entre versões do schema.
