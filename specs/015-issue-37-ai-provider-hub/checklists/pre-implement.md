# Pre-Implement Checklist: AI Provider Hub — registro e invocação de provedores pluggable (R6)

**Purpose**: Validar a qualidade dos requisitos (completude, clareza, consistência, cobertura) em `spec.md` antes de iniciar `/speckit-implement` — autoavaliação do autor, cobertura geral, profundidade padrão.
**Created**: 2026-07-24
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)

**Note**: Este checklist testa os requisitos escritos, não a implementação — cada item pergunta se algo está bem especificado na spec, não se o código funciona.

## Requirement Completeness

- [ ] CHK001 Estão definidos requisitos para o que acontece quando o `type` de um provedor é válido pelo schema mas não tem adaptador implementado (`anthropic`, `gemini`, `custom-http`) no momento da invocação, além da nota em Edge Cases? [Completeness, Spec §Edge Cases]
- [ ] CHK002 Estão definidos requisitos de autorização/autenticação para quem pode chamar os novos endpoints de CRUD/teste/invocação (`POST /api/ai-providers/invoke` etc.), ou isso é explicitamente fora de escopo? [Gap]
- [ ] CHK003 Está definido o comportamento quando o arquivo de perfil é editado manualmente em disco enquanto o processo está rodando, já que FR-015 só descreve hot-reload "via configuração, UI desktop ou API"? [Completeness, Spec §FR-015]
- [ ] CHK004 Estão definidos requisitos para escritas concorrentes/conflitantes no perfil de provedores (duas chamadas de API mutando ao mesmo tempo)? [Gap]
- [ ] CHK005 Está definido um limite máximo de provedores/rotas suportado, ou isso é intencionalmente ilimitado? [Gap]
- [ ] CHK006 Estão definidos requisitos de migração do perfil se o schema `ai-provider-profile.v1` evoluir para v2 dentro do ciclo de vida desta feature? [Gap]

## Requirement Clarity

- [ ] CHK007 "Integração mínima com sessão/eventos" (Input da spec, do escopo da issue #37) está traduzida em um conjunto específico e inequívoco de campos de sessão/evento que a invocação deve ler, além de "channelId, sourceType e conteúdo de texto/mensagens" do FR-004? [Clarity, Spec §FR-004]
- [ ] CHK008 "Sem interrupção não planejada do session-core" (SC-002) está definida com precisão suficiente para ser testável objetivamente (qual sinal observável conta como "interrupção")? [Measurability, Spec §SC-002]
- [ ] CHK009 "Imediatamente" no Acceptance Scenario 1 da US3 ("pode ser testado imediatamente... sem reiniciar o serviço") está quantificado com algum limite, ou fica como afirmação qualitativa? [Clarity, Spec §US3]
- [ ] CHK010 A distinção entre "erro de autenticação" e "segredo inválido ou ausente" (US5 AC3) está clara — mapeiam para o mesmo `InvocationErrorType`, ou são categorias diferentes que a spec confunde? [Clarity, Spec §US5]

## Requirement Consistency

- [ ] CHK011 O FR-005 (gatilhos de fallback) e os Acceptance Scenarios da US4 listam consistentemente as mesmas três condições (falha, timeout, rate limit), sem nenhum cenário omitir ou acrescentar uma silenciosamente? [Consistency, Spec §FR-005]
- [ ] CHK012 Os cinco tipos de erro do FR-006 são referenciados de forma consistente em todo lugar que a spec fala de "erro tipado" (SC-005, US2, US3, US4), sem nenhum acceptance scenario mencionar só um subconjunto? [Consistency]
- [ ] CHK013 A lista de capacidades usada pelo FR-010 (incompatibilidade de capacidade) é consistente com o enum `capabilities` já definido no contrato referenciado, sem introduzir um termo ausente do schema? [Consistency, Spec §FR-010]

## Acceptance Criteria Quality (Measurability)

- [ ] CHK014 O SC-006 ("cadastrar, testar e invocar um provedor inteiramente pela UI") pode ser verificado objetivamente sem também depender do sucesso do caminho de API do SC-007, dado que a US3 depende da US2 como transporte? [Measurability, Spec §SC-006]
- [ ] CHK015 Os limiares de "100%" em SC-002/SC-003/SC-004/SC-005 vêm acompanhados de uma população de teste definida (ex.: "todos os cenários de falha exercitados em teste"), ou isso fica a critério de quem implementa decidir o que conta como "exercitado"? [Measurability, Spec §SC-002]

## Scenario Coverage

- [ ] CHK016 Estão definidos requisitos de recuperação para uma mutação de perfil parcialmente aplicada (ex.: escrita da API bem-sucedida, mas o hot-reload do registry em memória falha)? [Gap, Recovery Flow]
- [ ] CHK017 Estão definidos requisitos de fluxo de exceção para a UI desktop quando a própria API do `session-core` está inacessível durante uma ação de teste/invocação (distinto do provedor em si falhar)? [Gap, Exception Flow, Spec §US3]
- [ ] CHK018 Estão definidos requisitos de fluxo alternativo para invocar uma capacidade que não tem nenhuma `route` configurada (diferente de uma rota cujo primário falha)? [Coverage, Spec §FR-005]
- [ ] CHK019 Estão definidos requisitos não funcionais (ex.: orçamento mínimo/máximo de latência de invocação além do `timeoutMs` do próprio provedor) para a camada de API/UI em si? [Gap, Non-Functional]

## Edge Case Coverage

- [ ] CHK020 Está especificado o comportamento quando `Route.primary` ou um item de `fallbacks` referencia um `Provider.id` que existia no momento da validação mas foi removido depois (referência pendente após uma mutação posterior)? [Gap, Edge Case]
- [ ] CHK021 Está especificado o comportamento quando `secretRef` resolve para uma string vazia (variável de ambiente definida mas vazia) versus não definida — são tratados como a mesma falha? [Gap, Edge Case]
- [ ] CHK022 Está especificado o comportamento de uma invocação cujo `input` excede o limite de tokens/contexto do provedor — é um tipo de erro distinto ou cai em `GENERIC`? [Gap, Edge Case]
- [ ] CHK023 Está especificado o comportamento quando o `sessionId` usado em `POST /api/ai-providers/invoke` não existe ou pertence a uma sessão já `ENDED`? [Gap, Edge Case]

## Non-Functional Requirements

- [ ] CHK024 Os requisitos de privacidade do `SecretPreview`/exibição mascarada cobrem exposição acidental via devtools/aba de rede do webview desktop, ou isso é considerado fora de escopo dado o limite do comando Tauri? [Gap, Non-Functional, Spec §US5]
- [ ] CHK025 Estão definidos requisitos de confiabilidade para o que acontece com invocações em andamento quando um hot-reload (FR-015) substitui o perfil de provedores no meio de uma requisição? [Gap, Non-Functional]
- [ ] CHK026 Os requisitos de observabilidade (FR-008) são específicos o suficiente sobre retenção/volume do log por invocação para evitar crescimento ilimitado, ou isso fica explicitamente adiado? [Gap, Non-Functional]

## Dependencies & Assumptions

- [ ] CHK027 A suposição de que `specs/013` (Memory Hub) já expõe o contexto de sessão/transcript "que o AI Provider Hub pode ler" está validada contra o que `specs/013` de fato implementou (não só o que foi planejado)? [Assumption, Spec §Assumptions]
- [ ] CHK028 A suposição de que `specs/014` (shell desktop) hospedar o painel novo desta feature é compatível com seu próprio FR-013 explícito ("AI Provider Hub fora de escopo") está reconciliada formalmente, além de uma linha de Assumption aqui? [Assumption, Spec §Assumptions]
- [ ] CHK029 A decisão em aberto "Gemini vs. GPT" (Clarifications Q4) tem responsável e prazo definidos antes de bloquear o entregável "1 provider real", ou fica só registrada como "em aberto até o /speckit-plan"? [Assumption, Spec §Clarifications]

## Ambiguities & Conflicts

- [ ] CHK030 "Sem exigir edição manual de arquivos de configuração" (FR-013) entra em conflito com a Assumption de que o perfil subjacente continua sendo um arquivo YAML editável manualmente, ou a edição manual é só "não exigida", não "proibida"? [Ambiguity, Spec §FR-013]
- [ ] CHK031 Há conflito entre o FR-001 ("sem exigir alteração de código do core para adicionar um novo endpoint OpenAI-compatible") e o FR-009 ("no mínimo, um adaptador real") — adicionar um segundo `type` (ex.: um futuro `gemini`) conta como "alteração de código do core", e se sim, isso contradiz a promessa de pluggability do FR-001? [Ambiguity]
- [ ] CHK032 "Metadados de proveniência" (`providerId`, modelo, latência) na US2 AC2 é uma lista exaustiva, ou um consumidor futuro poderia razoavelmente esperar campos adicionais (ex.: qual passo de fallback foi usado) que a spec não compromete nem descarta? [Ambiguity, Spec §US2]

## Traceability

- [ ] CHK033 Existe um esquema de ID de requisito/critério de aceite (FR-###, SC-###, US#) já estabelecido e aplicado consistentemente por toda a spec, sem lacunas na numeração? [Traceability]

## Notes

- Marque itens como concluídos com `[x]` conforme forem investigados; adicione achados inline (ex.: "resolvido — ver FR-016 adicionado").
- Este checklist não substitui `checklists/requirements.md` (gerado no `/speckit-specify`, foco em completude básica dos templates) — aqui a cobertura é mais ampla e explicitamente pensada para o gate G2 (Plan/Analyze) da constituição, antes do `/speckit-implement`.
- Itens sem referência a `Spec §` usam os marcadores `[Gap]`/`[Ambiguity]`/`[Assumption]`/`[Traceability]` para indicar que apontam para algo ausente ou não resolvido no texto atual, não para uma seção existente.
