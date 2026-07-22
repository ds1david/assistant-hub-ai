# Research: Memory Hub — persistência local de sessão e eventos (R3)

Nenhum item do Technical Context ficou marcado `NEEDS CLARIFICATION` — a spec já resolveu as ambiguidades relevantes em Assumptions. Este documento registra as decisões técnicas de arquitetura (Phase 0), com alternativas consideradas e rejeitadas.

## Decisão 1 — Motor de armazenamento: SQLite embarcado (`org.xerial:sqlite-jdbc`)

**Decision**: Um único arquivo `.db` SQLite por instalação do `session-core`, acessado via JDBC simples, sem servidor de banco separado.

**Rationale**: Local-first (ADR-0005, docs/vision.md) exige que a persistência funcione sem depender de um serviço remoto; um motor embarcado em arquivo único, sem processo de servidor, atende isso diretamente. SQLite oferece transações ACID reais, o que resolve a exigência de FR-009 (gravação interrompida não pode corromper dados já persistidos) sem exigir lógica própria de recuperação de arquivo. É também o formato mais compatível com o empacotamento desktop futuro (`specs/002-desktop-distribution/`), que já assume "não empacotar dependências pesadas" e prefere sidecars simples.

**Alternatives considered**:
- **H2 embarcado + Spring Data JPA**: rejeitado — adicionaria uma camada de ORM (mapeamento de entidades, `EntityManager`) desproporcional a duas tabelas simples de append/consulta; o projeto hoje não usa JPA em nenhum serviço, e introduzir esse paradigma só para esta feature contraria a preferência por mudanças pequenas e focadas.
- **Arquivo JSONL append-only por sessão + índice**: rejeitado — atingir a mesma garantia de "tudo ou nada" por evento que uma transação SQLite dá de graça exigiria lógica própria de detecção/descarte de linha truncada ao reabrir o arquivo, com mais superfície de teste e mais chance de bug sutil justamente no cenário de crash que é um requisito explícito (FR-009).
- **PostgreSQL/MySQL (cliente-servidor)**: rejeitado — introduz dependência de rede/processo externo, contrariando "local-first" e exigindo mudança de infraestrutura (`infra/compose/docker-compose.yml`) desproporcional ao escopo da issue.

## Decisão 2 — Acesso a dados: JDBC direto, sem ORM

**Decision**: Uma classe `SessionPersistenceStore` com SQL direto (via `java.sql.*`), no mesmo estilo direto já usado por `SessionRepository`/`SessionController` hoje.

**Rationale**: Duas tabelas, operações de append e consulta por `sessionId` — não há necessidade de mapeamento objeto-relacional completo. Manter o estilo direto já usado no módulo evita introduzir uma nova convenção de acesso a dados só para esta feature.

**Alternatives considered**: Spring Data JPA/Hibernate — rejeitado pelos mesmos motivos da Decisão 1 (peso desproporcional ao escopo).

## Decisão 3 — Estratégia de crash-safety

**Decision**: Cada evento é gravado em uma transação própria (uma linha por `INSERT`, commit imediato). Uma sessão criada/atualizada também é gravada transacionalmente. Não há write-ahead log nem arquivo intermediário além do próprio banco SQLite.

**Rationale**: Delegar a atomicidade ao motor transacional elimina a necessidade de lógica própria de recuperação (ex.: detectar e descartar uma última linha truncada de um arquivo). Um crash a meio de uma transação simplesmente não deixa a linha visível — o restante dos dados já commitados permanece intacto, satisfazendo FR-009 e o cenário correspondente de Edge Cases da spec.

**Alternatives considered**: Log de eventos com recuperação por truncamento de linha incompleta — rejeitado (ver Decisão 1).

## Decisão 4 — Rehydration do cache em memória na subida do processo

**Decision**: Na inicialização do `session-core`, `MemoryHubStartupRehydrator` lê todas as sessões não-expurgadas e seus eventos do SQLite e popula a mesma estrutura em memória (`Map`) que `SessionRepository` já expõe hoje. O SQLite é a fonte de verdade; a estrutura em memória continua existindo como cache de leitura rápida.

**Rationale**: Preserva a API pública de `SessionRepository` (`save`, `findById`, `append`, `events`) inalterada para os consumidores existentes (`SessionController`, o mapeador de eventos v2 de `specs/007-sf-021-session-core-events/`), minimizando o raio de mudança. Evita reescrever os pontos de chamada existentes para consultar o banco a cada leitura.

**Alternatives considered**: Consultar o SQLite diretamente a cada leitura, sem cache em memória — rejeitado nesta iteração por exigir um refactor mais amplo dos pontos de chamada e mudar o perfil de desempenho de leitura além do escopo da issue; pode ser reavaliado como simplificação futura se o cache em memória se mostrar redundante.

## Decisão 5 — Formato e aplicação da política de retenção

**Decision**: Política configurável via `application.yml` (`session-core.memory-hub.retention.max-age` e/ou `max-sessions`), aplicada em uma rotina de expurgo (`RetentionPolicy`) executada na subida do processo e reaproveitável por um agendamento periódico futuro. Por padrão (sem configuração explícita), nada é expurgado — consistente com a Assumption da spec de retenção indefinida por padrão. Apenas sessões em status terminal (`ENDED`) são elegíveis para expurgo; uma sessão ativa nunca é removida por retenção.

**Rationale**: Atende FR-004 (retenção documentada e configurável) sem exigir UI (fora de escopo, conforme a issue) e sem risco de apagar uma sessão em andamento.

**Alternatives considered**: Expurgo somente manual/administrativo — rejeitado, não atende "evitando crescimento não controlado" de forma automática quando um limite é de fato configurado.

## Decisão 6 — Local e configurabilidade do arquivo `.db`

**Decision**: Caminho padrão `data/session-core/memory-hub.db` (relativo ao diretório de trabalho do serviço), sobrescrevível por propriedade/variável de ambiente (`session-core.memory-hub.path` / `SESSION_CORE_MEMORY_HUB_PATH`), no mesmo padrão já usado por `SESSION_CORE_TRANSCRIPT_FEED_URL` em `application.yml`. O diretório é criado automaticamente na subida se não existir. O caminho padrão é adicionado ao `.gitignore` (P9 — nunca commitar dado de sessão).

**Rationale**: Mantém consistência com a convenção de configuração já usada no módulo; permite reposicionar o arquivo para outro volume/disco em ambientes diferentes (WSL/Docker/desktop futuro) sem mudança de código.

**Alternatives considered**: Caminho absoluto fixo — rejeitado, inflexível entre os ambientes-alvo já previstos (WSL, Docker, executável desktop futuro).
