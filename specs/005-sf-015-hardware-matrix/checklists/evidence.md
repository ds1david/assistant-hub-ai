# Evidence & Device-Identity Checklist: SF-015 — Matriz manual de hardware R1

**Purpose**: Validar a qualidade dos requisitos de `spec.md` nas quatro dimensões escolhidas: critério de evidência PASS/FAIL/BLOCKED, não-regressão de identidade de dispositivo, limites de escopo vs SF-018/SF-019, e segurança/privacidade da evidência. Não testa se o hardware funciona — testa se o texto da spec está completo, claro e consistente o suficiente para alguém executar a matriz sem ambiguidade.
**Created**: 2026-07-20
**Feature**: [spec.md](../spec.md)

**Note**: Revisão padrão pelo próprio autor antes do Gate G2/G3 — não é um gate formal de release revisado por terceiros.

## Evidência e critério PASS/FAIL/BLOCKED

- [ ] CHK001 - É explícito o que distingue um resultado BLOCKED de um FAIL quando um cenário não pode ser executado por falta de hardware? [Clarity, Spec §FR-008]
- [ ] CHK002 - Estão definidos os campos mínimos que um registro de validação precisa ter para ser considerado "completo" (ambiente, dispositivos, casos, resultado)? [Completeness, Spec §FR-002/FR-004/FR-005]
- [ ] CHK003 - É mensurável a condição de "sucesso" de SC-001 (três cenários com resultado registrado em uma única sessão), ou "uma única sessão" fica sem limite objetivo (ex.: pode se estender por dias sem violar o critério)? [Measurability, Spec §SC-001]
- [ ] CHK004 - A spec define o que fazer se um cenário obtiver resultado PASS mas com uma limitação/ressalva relevante — isso é permitido, e como é registrado? [Gap]
- [ ] CHK005 - Está claro quantas frases de referência por cenário (FR-005) são necessárias para considerar a correlação canal↔dispositivo validada — "ao menos uma" é suficiente para um resultado PASS? [Ambiguity, Spec §FR-005]
- [ ] CHK006 - A condição de reabertura de um registro já concluído (quando uma regressão futura é encontrada) está descrita de forma consistente entre `data-model.md` e `spec.md`, ou só existe em um dos dois? [Consistency, Spec §SC-003]

## Não-regressão de identidade de dispositivo

- [ ] CHK007 - Os requisitos de "sem regressão de channelId/sourceType/endpointId" (FR-002) fazem referência a um critério objetivo e verificável (contratos das SF-016/017/018), ou dependem de julgamento subjetivo do executor? [Clarity, Spec §FR-002]
- [ ] CHK008 - "Fallback silencioso" (SC-002, FR-002) está definido com exemplos concretos do que conta como silencioso vs. explícito, de forma consistente com o ADR-0011/P7 já referenciado no plano? [Ambiguity, Spec §SC-002]
- [ ] CHK009 - Os requisitos de não-regressão são igualmente específicos para os três cenários (conference cam, Bluetooth+USB, microfone default), ou algum cenário tem critério de identidade menos detalhado que os outros? [Consistency, Spec §User Story 1-3]
- [ ] CHK010 - Existe requisito claro para o caso em que o mesmo `endpointId` aparece com nomes amigáveis diferentes entre sessões (driver reinstalado, firmware atualizado)? [Edge Case, Gap]
- [ ] CHK011 - O comportamento esperado durante reconexão Bluetooth em andamento (Edge Cases, User Story 2) é especificado como requisito testável, ou fica apenas como pergunta aberta sem critério de aceite associado? [Coverage, Spec §Edge Cases]

## Limites de escopo vs SF-018 / SF-019

- [ ] CHK012 - A spec delimita claramente até onde vai o "fechamento retroativo" da evidência SF-018 (FR-006) — todos os 7 casos do template, ou um subconjunto? [Clarity, Spec §FR-006]
- [ ] CHK013 - Está explícito que a cobertura de hot-plug nesta feature é apenas parcial e que o listener completo é escopo da SF-019, evitando que alguém interprete FR-006/User Story 3 como substituto da SF-019? [Scope Boundary, Spec §User Story 3]
- [ ] CHK014 - Se o fechamento retroativo da SF-018 (FR-006) falhar ou ficar BLOCKED, a spec define se isso bloqueia o resultado geral da SF-015 ou é tratado como um item independente? [Gap, Spec §FR-006/SC-003]
- [ ] CHK015 - Os critérios de "sem regressão" desta matriz (FR-002) referenciam explicitamente que os contratos avaliados vêm de SF-016/017/018 e não introduzem novos critérios próprios da SF-015? [Consistency, Spec §FR-002]

## Segurança e privacidade da evidência

- [ ] CHK016 - Há um requisito explícito na spec (não só no template de `docs/validation/`) proibindo áudio bruto, segredos ou tokens nos registros de evidência desta feature? [Gap, Spec §Requirements]
- [ ] CHK017 - As "frases de referência" exigidas por FR-005 têm alguma restrição de conteúdo especificada (ex.: não usar dados pessoais reais de terceiros ao ditar frases de teste)? [Gap]
- [ ] CHK018 - Está definido quem revisa a evidência antes do commit para garantir ausência de dados sensíveis, ou isso fica implícito apenas na constituição (P9) sem menção na spec? [Traceability, Assumption]

## Dependências e suposições

- [ ] CHK019 - A suposição de disponibilidade de hardware (conference cam, Bluetooth, microfone USB) documenta o que acontece se **nenhum** dos três estiver disponível na sessão, além do caso de um único cenário faltante? [Assumption, Spec §Assumptions]
- [ ] CHK020 - A dependência dos contratos de SF-016/017/018 como "referência de não-regressão" está validada — ou seja, a spec confirma que esses contratos já estão estáveis e não sujeitos a mudança concorrente durante a execução da matriz? [Dependency, Spec §Assumptions]

## Ambiguidades e conflitos

- [ ] CHK021 - "Latência percebida" (FR-004) é registrada como métrica qualitativa por design, ou a ausência de uma escala/unidade padronizada é uma lacuna não intencional? [Ambiguity, Spec §FR-004]
- [ ] CHK022 - Existe conflito entre FR-007 ("MUST NOT depender de automação de hardware no CI") e algum critério de sucesso que implicitamente exigiria repetibilidade automatizada? [Conflict Check, Spec §FR-007]

## Notes

- Escopo desta rodada: todos os 4 focos escolhidos pelo usuário (evidência/PASS-FAIL-BLOCKED, identidade de dispositivo, limites SF-018/SF-019, segurança/privacidade), profundidade padrão para revisão do próprio autor.
- Itens sem referência de seção específica usam `[Gap]`/`[Ambiguity]`/`[Assumption]` porque apontam para algo ausente da spec, não para um trecho existente.
- Se algum item aqui revelar uma lacuna real, o conserto é editar `spec.md` (não este arquivo) e então marcar o item como resolvido.
