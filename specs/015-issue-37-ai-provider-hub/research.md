# Research: AI Provider Hub — registro e invocação de provedores pluggable (R6)

Nenhum item do Technical Context ficou marcado `NEEDS CLARIFICATION` — as ambiguidades relevantes já foram resolvidas em `/speckit-clarify` (seção `## Clarifications` de `spec.md`) e em Assumptions. Este documento registra as decisões técnicas de arquitetura (Phase 0), com alternativas consideradas e rejeitadas.

## Decisão 1 — Sem SDK de provedor: HTTP genérico via JDK `HttpClient`

**Decision**: O adaptador real (`OpenAiCompatibleAdapter`) fala HTTP diretamente com `java.net.http.HttpClient` (JDK 21, zero dependência nova) + Jackson (já transitivo) para serializar/desserializar o payload `chat/completions`-like.

**Rationale**: ADR-0010 e a constituição (P2) exigem que nenhum serviço de domínio importe SDK de fornecedor externo. Um adaptador `openai-compatible` genérico, guiado só por `baseUrl`/`headers`/`authentication` do perfil, é literalmente o que FR-001 pede ("adicionar um novo endpoint OpenAI-compatible sem alterar código do core") — qualquer provedor que fale esse wire format (Ollama, OpenAI, NVIDIA NIM hosted, endpoint custom) funciona com o mesmo adaptador, mudando só a configuração.

**Alternatives considered**:
- **SDK oficial por fornecedor (`openai-java`, Google GenAI Java, etc.)**: rejeitado — viola P2 diretamente, e cada SDK traria sua própria forma de configurar timeout/retry/auth, fragmentando o comportamento isolado exigido por FR-003.
- **Spring `WebClient` (reativo)**: rejeitado — exigiria `spring-webflux` como dependência nova só para chamadas síncronas e isoladas por invocação; o `HttpClient` da JDK já suporta timeout por requisição sem essa dependência extra, mantendo o estilo direto já usado no módulo (JDBC direto em `SessionPersistenceStore`, sem ORM).

## Decisão 2 — Perfil declarativo em arquivo YAML, não em tabela SQLite

**Decision**: O perfil de provedores (`Provider`/`ProviderProfile`/rotas) vive em um arquivo YAML local (`config/ai-providers.yaml` — caminho já reservado por uma entrada de `.gitignore` desde o bootstrap do repo, "AI provider local configuration and secrets"), validado contra `contracts/ai-provider-profile.v1.schema.json` a cada carga e a cada escrita. Um `ProviderRegistry` em memória é a fonte de leitura rápida, recarregado a cada escrita bem-sucedida (FR-015) — sem reiniciar o processo.

**Rationale**: A spec chama isso explicitamente de "perfil declarativo" (FR-001), e `samples/ai-providers/providers.example.yaml` já estabelece o formato YAML como a convenção do projeto para esse contrato. Um arquivo mantém a feature alinhada ao caminho futuro de importação/exportação de configuração de `specs/003-ai-provider-hub/` (exportar = copiar o arquivo com `secretRef` como placeholder; nada disso é natural com uma tabela relacional). Diferente do Memory Hub (`specs/013`), que precisa de append/consulta transacional de alto volume, o perfil de provedores é um documento pequeno, reescrito por completo a cada mutação — SQLite não traria vantagem, só acoplaria dois domínios de dado distintos ao mesmo arquivo `.db`.

**Alternatives considered**:
- **Nova tabela no `memory-hub.db` já existente**: rejeitado — acoplaria o schema de configuração de provedores ao armazenamento de sessão/evento de uma feature diferente (`specs/013`), dificultando evoluir os dois independentemente; e a natureza "documento versionado completo" do perfil (FR-002, `version: 1`) se encaixa melhor em um arquivo do que em linhas de tabela.
- **Banco de dados dedicado (nova tabela em novo arquivo `.db`)**: rejeitado — complexidade desproporcional a um documento pequeno, reescrito por completo a cada mutação; um arquivo YAML com escrita atômica (arquivo temporário + rename) já garante que uma escrita nunca deixa o arquivo em estado parcialmente corrompido.

## Decisão 3 — Validação reaproveitando `json-schema-validator` já existente

**Decision**: `ProviderProfileValidator` usa `com.networknt:json-schema-validator` (já dependência do módulo) contra `contracts/ai-provider-profile.v1.schema.json`, copiado para o classpath pelo `pom.xml` no mesmo padrão já usado para `transcript-event.v2.schema.json`.

**Rationale**: Zero dependência nova; reaproveita exatamente o padrão já testado em produção pelo módulo (`TranscriptEventValidator`), incluindo o princípio P4 de nunca duplicar a regra do contrato em código Java — o schema continua sendo a fonte única de verdade.

**Alternatives considered**: Validação manual campo a campo em Java — rejeitada, duplicaria regras já expressas no schema (P4) e teria mais superfície de bug em casos como o `allOf`/`if`/`then` de `authentication.secretRef`.

## Decisão 4 — Resolução de segredo: interface `SecretResolver`, só `env:` implementado nesta fatia

**Decision**: Uma interface `SecretResolver` resolve `secretRef` em tempo de invocação, sem nunca logar o valor. Nesta fatia, só `EnvSecretResolver` (formato `env:VAR`) é implementado, cobrindo o ambiente WSL Developer. `os:...` (armazenamento seguro do Windows) fica como ponto de extensão documentado, não implementado agora — consistente com a Assumption da spec e com `docs/security/provider-secrets.md`.

**Rationale**: A cobertura automatizada de testes deste R6 roda no WSL (P3); implementar `os:...` exigiria integração com Windows Credential Manager, fora do alcance de teste determinístico no WSL e melhor endereçado junto de `specs/002-desktop-distribution/`, que já é dona do empacotamento Windows.

**Alternatives considered**: Resolver `os:...` já nesta fatia com um stub/no-op — rejeitado, criaria uma falsa sensação de suporte completo sem cobertura de teste real; melhor deixar o contrato (`secretRef` aceita `os:...` pelo schema) intacto e implementar quando houver um ambiente Windows para testar de verdade.

## Decisão 5 — Adaptador real desta fatia: `openai-compatible` (cobre Ollama e, se escolhido, GPT)

**Decision**: O único adaptador real implementado nesta fatia é `OpenAiCompatibleAdapter` (`type: openai-compatible`). Ele atende tanto Ollama local quanto OpenAI (GPT) — a decisão entre Gemini e GPT do operador (`## Clarifications`) permanece em aberto, mas qualquer uma das duas opções "GPT" funciona com este adaptador sem mudança de código, bastando `baseUrl`/`model`/`secretRef` no perfil. Um adaptador `GeminiAdapter` dedicado (wire format diferente do OpenAI-compatible) fica fora desta fatia até a decisão ser fechada, e pode ser adicionado depois via `ProviderAdapterFactory` sem tocar `InvocationService`/`ProviderRegistry`.

**Rationale**: Minimiza o risco de implementar um adaptador para um provedor que acabe não sendo o escolhido; `openai-compatible` é o único `type` do schema que atende ambos os candidatos plausíveis ("Ollama local" citado nas Assumptions e "GPT" citado pelo operador), satisfazendo FR-009 ("no mínimo, um adaptador real") sem apostar na decisão Gemini-vs-GPT ainda em aberto.

**Alternatives considered**:
- **Implementar `GeminiAdapter` agora**: rejeitado — a decisão do operador ainda não fechou entre Gemini e GPT; implementar os dois adaptadores nesta fatia expandiria o escopo além do "1 provider real" pedido pela issue #37.
- **Adiar todo adaptador real para uma fase futura**: rejeitado — violaria FR-009 e o critério de aceite explícito da issue #37 ("1 provider real + 1 fake").

## Decisão 6 — Taxonomia de erro: enum `InvocationErrorType` mapeado a partir do status HTTP

**Decision**: `InvocationErrorType` tem os valores `AUTHENTICATION`, `MODEL_NOT_FOUND`, `TIMEOUT`, `RATE_LIMITED`, `GENERIC`. O adaptador mapeia a resposta do provedor: 401/403 → `AUTHENTICATION`; 404 ou corpo indicando modelo inexistente → `MODEL_NOT_FOUND`; 429 → `RATE_LIMITED`; estouro do `timeoutMs` do provedor (exceção de timeout do `HttpClient`) → `TIMEOUT`; qualquer outra falha → `GENERIC`.

**Rationale**: Atende FR-006/FR-010/SC-005 diretamente e ao gatilho de fallback do FR-005 (falha, timeout ou rate limit acionam fallback; os demais casos genéricos não, por padrão, a menos que a rota tenha fallback configurado igualmente — FR-005 não distingue rate limit de outras falhas para fins de "quando" o fallback é permitido, só exige que o tipo seja identificável no resultado).

**Alternatives considered**: Repassar a exceção HTTP crua ao chamador — rejeitado, obrigaria cada consumidor (API, UI, testes) a reimplementar a mesma lógica de classificação, contrariando FR-006 ("o sistema DEVE distinguir").

## Decisão 7 — Métricas de invocação via log estruturado, não uma tabela nova

**Decision**: `InvocationService` registra uma linha de log estruturado (SLF4J) por invocação — `providerId`, `model`, `capability`, `sessionId`, `channelId`, `latencyMs`, resultado (sucesso/tipo de erro) — sem nenhum campo de segredo. Nenhuma tabela ou serviço de métricas novo é introduzido.

**Rationale**: FR-008 exige "registrar métricas/eventos por invocação", não uma UI de dashboard ou consulta histórica — que pertence ao escopo mais amplo de `specs/003-ai-provider-hub/` ("Métricas por provedor e modelo"), explicitamente fora desta fatia R6. Log estruturado é o menor mecanismo que atende ao requisito, sem introduzir armazenamento novo (contido pelo Constitution Check, "integração mínima" da issue #37).

**Alternatives considered**: Nova tabela `ai_provider_invocations` no `memory-hub.db` — rejeitada por ora como prematura para o escopo mínimo desta fatia; pode ser revisitada se uma feature futura de dashboard de métricas precisar de consulta histórica.

## Decisão 8 — Testes determinísticos: servidor HTTP fake local via `com.sun.net.httpserver`

**Decision**: Os testes de `OpenAiCompatibleAdapter` (timeout, erro tipado, fallback) rodam contra um servidor HTTP local iniciado em processo com `com.sun.net.httpserver.HttpServer` (já na JDK, zero dependência nova) — nenhuma chamada de rede real na suíte padrão. Um teste de integração opcional contra o provedor remoto real de referência é marcado com `@Tag("real-provider")`, pulado por padrão (`mvn test` não o executa), só rodando quando a credencial correspondente está configurada via variável de ambiente.

**Rationale**: Atende P10 (determinístico, sem GPU/hardware) e P3 (WSL-first, suíte padrão não depende de rede externa nem de custo de API paga) simultaneamente, mantendo ainda assim uma via de validação manual/opt-in real, no mesmo espírito de `docs/validation/` já usado por `specs/014` para o que só pode ser confirmado em ambiente real.

**Alternatives considered**: Biblioteca de mock HTTP dedicada (MockWebServer/WireMock) — rejeitada por introduzir uma dependência nova só de teste quando a JDK já resolve o caso de uso sem ela.

## Decisão 9 — Desktop: `ai_provider_client.rs` espelha `session_core_client.rs`, sem chamada de rede no webview

**Decision**: Toda chamada HTTP aos novos endpoints do `session-core` fica em `ai_provider_client.rs` (Rust, `src-tauri`), exposta ao frontend só via comandos Tauri (`invoke`), no mesmo padrão já registrado em `specs/014-issue-35-desktop-tauri-shell-local/plan.md` (`session_core_client.rs`, `api-client.ts` — "nunca `fetch` direto no webview").

**Rationale**: Mantém a regra arquitetural já estabelecida (evita expor a URL do `session-core` e problemas de CORS/CSP ao conteúdo web) e reaproveita `reqwest` já presente em `Cargo.toml`, sem dependência nova.

**Alternatives considered**: Chamar o `session-core` diretamente do webview via `fetch` — rejeitado, contraria a decisão já tomada e registrada em `specs/014`, que esta feature não deve reabrir.
