# Fluxo de trabalho com Codex

## Estratégia

Use o monorepo durante os primeiros ciclos para reduzir coordenação e permitir alterações atômicas entre contratos, serviço e documentação. Extraia repositórios apenas quando uma fronteira tiver ciclo de release, equipe ou requisitos operacionais realmente independentes.

## Preparação

1. Abra o repositório na raiz.
2. Confirme que `AGENTS.md` foi carregado.
3. Peça ao agente para resumir a spec ativa e os ADRs relacionados.
4. Trabalhe em uma tarefa da lista por vez.

## Prompt recomendado

```text
Leia AGENTS.md, docs/vision.md, os ADRs relevantes e a spec ativa.
Antes de editar, apresente:
1. objetivo da tarefa;
2. arquivos que pretende alterar;
3. contratos afetados;
4. testes que executará.
Implemente apenas a tarefa solicitada.
No final, execute os testes, atualize a documentação e mostre riscos ou pendências.
```

## Divisão futura de repositórios

Separar somente depois da R2, quando houver evidência de fronteiras estáveis:

- `assistant-hub-core`;
- `assistant-hub-plugin-sdk`;
- `assistant-hub-audio-agent-windows`;
- `assistant-hub-transcription`;
- `assistant-hub-ui`;
- `assistant-hub-plugins`;
- `assistant-hub-deployment`;
- `assistant-hub-architecture`.

Até lá, módulos Maven, pacotes Python e diretórios de deploy oferecem isolamento suficiente com menor custo operacional.
