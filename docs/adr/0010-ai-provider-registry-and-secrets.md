# ADR-0010 — Registro de provedores de IA e segredos externos

- Status: proposto
- Data: 2026-07-17

## Contexto

A plataforma precisa alternar entre modelos locais e APIs remotas, permitir chaves próprias e suportar endpoints compatíveis sem espalhar SDKs de fornecedores pelo domínio.

## Decisão proposta

Criar um AI Provider Hub com:

- contrato interno por capacidades;
- adaptador genérico OpenAI-compatible;
- adaptadores específicos apenas quando necessário;
- configuração declarativa versionada;
- `secretRef` em vez de chaves no arquivo;
- armazenamento seguro no desktop e variáveis de ambiente no WSL;
- roteamento e fallback por perfil.

NVIDIA NIM hosted será tratado como preset OpenAI-compatible com URL e modelo configuráveis, não como dependência rígida do core.

## Consequências

- facilidade para adicionar provedores;
- menor lock-in;
- comparação e fallback;
- mais responsabilidade de validação, segurança e testes de conformidade;
- a interface precisa deixar claros custo, privacidade e disponibilidade.
