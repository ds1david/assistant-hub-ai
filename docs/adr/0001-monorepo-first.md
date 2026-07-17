# ADR-0001 — Monorepo nos primeiros ciclos

- Status: aceito
- Data: 2026-07-16

## Contexto

A plataforma terá tecnologias e tempos de execução diferentes. Separar tudo em repositórios agora aumentaria versionamento, coordenação e trabalho de CI antes de as fronteiras estarem comprovadas.

## Decisão

Usar monorepo até pelo menos a conclusão da R2, com módulos independentes e contratos explícitos.

## Consequências

### Positivas

- mudanças atômicas;
- contexto simples para desenvolvimento assistido;
- documentação central;
- setup único.

### Negativas

- pipeline precisa filtrar módulos;
- risco de dependências indevidas, mitigado por regras e testes arquiteturais.
