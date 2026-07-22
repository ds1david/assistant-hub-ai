# G2 Plan Gate Checklist: Janela adaptativa de áudio com base em métricas (SF-022)

**Purpose**: Gate humano G2 (Plan/Analyze) da constituição — validar se `spec.md` + `plan.md` (com `research.md`/`data-model.md`) estão maduros o bastante para autorizar `/speckit-tasks`/Implement. Foco combinado: política adaptativa e histerese, contrato/isolamento, e testabilidade sem GPU/hardware.
**Created**: 2026-07-22
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [research.md](../research.md) · [data-model.md](../data-model.md)

**Note**: Este checklist testa a qualidade dos requisitos (completude, clareza, consistência, medibilidade, cobertura) — não testa se a implementação funciona.

## Requirement Completeness

- [ ] CHK001 - Estão documentados os valores numéricos concretos (limiares de latência, piso, passo, período de estabilidade, amostras mínimas) em algum artefato da feature, e não apenas "parâmetros configuráveis razoáveis"? [Completeness, Spec Assumptions, Plan/research.md §6]
- [ ] CHK002 - Existe um requisito (ou nota) que exija atualizar a documentação do endpoint `GET /v1/sessions/{sessionId}/metrics` (ex.: `docs/validation/sf-016-latency-metrics.md` ou equivalente) para refletir o novo campo `windowMs`? [Gap, Plan/research.md §4]
- [ ] CHK003 - É exigido, em algum requisito, registrar em log a mudança de janela (valor anterior/novo/direção), ou isso fica só como decisão de plano sem respaldo em FR? [Completeness, Spec FR-007, Plan/research.md §4]

## Requirement Clarity

- [ ] CHK004 - O comportamento ao **retornar** à zona saudável durante um encolhimento/crescimento já em curso está definido de forma inequívoca — basta uma única avaliação saudável para parar o movimento, ou isso também deveria exigir confirmação por N avaliações, como a ativação inicial? [Ambiguity, Spec FR-003, Plan/research.md §3]
- [ ] CHK005 - "Passo controlado" (FR-004) está associado a um valor explícito e único, ou a spec permite mais de uma leitura sobre se o passo é fixo ou proporcional à distância até o limite? [Clarity, Spec FR-004]
- [ ] CHK006 - O relacionamento entre o novo piso adaptativo (`adaptive_window_min_seconds`) e o `whisper_min_audio_seconds` já existente (que também define um mínimo de áudio, para fins de flush) está explicitado, ou fica implícito que são conceitos independentes? [Clarity, Spec Edge Cases, Plan Technical Context]
- [ ] CHK007 - Está claro, sem precisar ler `research.md`, o que exatamente conta como "amostras suficientes" (FR-008) — a spec define isso qualitativamente e delega o número a outro artefato; isso está declarado explicitamente como decisão adiada, ou pode ser lido como uma lacuna? [Clarity, Spec FR-008]

## Requirement Consistency

- [ ] CHK008 - A afirmação da spec de que "não existe um máximo configurável separado maior que o padrão" (Clarifications) está refletida de forma consistente em todos os FRs que mencionam limites (FR-002, FR-004), sem nenhum resquício de linguagem sugerindo um teto distinto? [Consistency, Spec Clarifications, FR-002]
- [ ] CHK009 - O papel exclusivamente observacional de `p50Ms` (Clarifications) está consistente entre o texto das User Stories, os FRs (FR-001) e a descrição da entidade "Snapshot de latência" — nenhum FR ou cenário reintroduz `p50Ms` como porta de decisão? [Consistency, Spec FR-001, Key Entities]
- [ ] CHK010 - O texto de FR-003 (histerese como propriedade de "mudança de direção") e o Edge Case de silêncio prolongado (avaliação orientada a evento) são consistentes entre si quanto a **quando** uma avaliação "conta" para a confirmação — uma avaliação sem dado suficiente (FR-008) consome ou não um slot de confirmação? [Consistency, Spec FR-003/FR-008, Plan/research.md §3]

## Acceptance Criteria Quality (Measurability)

- [ ] CHK011 - SC-001/SC-002 falam em "número fixo e documentado de avaliações" — esse número (ou a fórmula para derivá-lo a partir de piso/passo/confirmação) está de fato documentado em algum artefato, tornando o critério verificável como um limite superior duro, e não apenas qualitativo? [Measurability, Spec SC-001/SC-002, Plan/research.md §6]
- [ ] CHK012 - SC-007 ("comportamento idêntico ao anterior com a flag desabilitada") tem um critério objetivo de "idêntico" (ex.: mesmos bytes de janela aplicados, mesma ausência de campo `windowMs`), ou depende de interpretação para saber o que exatamente comparar? [Measurability, Spec SC-007, FR-011]
- [ ] CHK013 - SC-004 ("100% dos ajustes... permanecem isolados ao canal de origem") tem uma forma objetiva de verificação dado o desenho de estado por conexão (Plan/data-model.md), ou a métrica de "isolamento" carece de um sinal observável concreto para além da inspeção de teste? [Measurability, Spec SC-004, Plan/data-model.md]

## Scenario & Edge Case Coverage

- [ ] CHK014 - Existe um requisito ou nota cobrindo o que acontece quando duas conexões para o **mesmo** `channelId` coexistem brevemente (ex.: corrida de reconexão), cada uma com seu próprio estado de ajuste, escrevendo no mesmo registro de observabilidade — o valor relatado em `windowMs` nesse intervalo está definido (ex.: last-write-wins) ou é uma lacuna? [Gap, Plan/research.md §1, data-model.md]
- [ ] CHK015 - O Edge Case de canal com amostras insuficientes (FR-008) resolve explicitamente se `active_direction`/`pending_count` são preservados ou reiniciados durante o intervalo sem dado suficiente, ou isso fica implícito na leitura do algoritmo do plano? [Edge Case, Spec Edge Cases, Plan/data-model.md]
- [ ] CHK016 - Está coberto o cenário em que a flag `adaptive_window_enabled` é alternada (ligada→desligada ou vice-versa) **durante** uma sessão já em andamento com canais ativos, ou a spec assume implicitamente que a flag só muda entre reinicializações do serviço? [Gap, Spec FR-011]

## Contract & Isolation Safety

- [ ] CHK017 - FR-006 (contrato `transcript-event.v2` inalterado) tem um critério de verificação explícito e testável (ex.: validação contra o schema em 100% dos eventos gerados com janela ajustada), e não apenas uma afirmação de intenção? [Measurability, Spec FR-006, SC-003]
- [ ] CHK018 - A distinção entre "contrato versionado" (`transcript-event.v2`, protegido por P4) e "endpoint de observabilidade não-versionado" (`/metrics`, onde `windowMs` é adicionado) está documentada de forma que um revisor não familiarizado com o histórico da SF-016 consiga confirmar que a mudança não infringe P4? [Clarity, Plan Constitution Check P4]
- [ ] CHK019 - FR-005 (isolamento por sessão/canal) está redigido de forma que cubra tanto a decisão (estado por conexão) quanto a observabilidade (registro compartilhado por app) — ou o requisito, lido isoladamente, parece garantir isolamento só na camada de decisão, deixando a camada de observabilidade sem cobertura explícita? [Consistency, Spec FR-005, Plan/data-model.md]

## Testability & Determinism

- [ ] CHK020 - FR-009 lista os comportamentos a testar (redução, recuperação, histerese, limites, isolamento) de forma que cada item tenha um teste planejado correspondente e nomeado (`plan.md`/`quickstart.md`), fechando o rastreamento de ponta a ponta? [Traceability, Spec FR-009, Plan Project Structure, quickstart.md]
- [ ] CHK021 - Está definido, em algum artefato, quantos ciclos de avaliação sintética (eventos de transcrição concluída) um teste de integração precisa simular para provar SC-001/SC-002 de forma determinística, sem depender de tempo real de processamento? [Gap, Measurability, Plan/quickstart.md]
- [ ] CHK022 - A dependência entre os testes desta feature e o `LatencyMetricsRegistry` pré-populado via `create_app(metrics_registry=...)` está documentada como uma capacidade já existente e suficiente, ou a spec/plano assumem, sem confirmar, que essa via de injeção cobre todos os cenários de teste necessários (inclusive múltiplos canais simultâneos)? [Assumption, Plan Technical Context, quickstart.md]

## Dependencies & Assumptions

- [ ] CHK023 - A assunção de que `LatencyMetricsRegistry` (SF-016) não precisa de nenhuma alteração está validada contra o custo de chamar `session_snapshot()` uma vez por transcrição concluída (não só uma vez por requisição HTTP como hoje) — existe algum requisito ou nota reconhecendo esse novo padrão de uso? [Assumption, Spec Assumptions, Plan/research.md §1]
- [ ] CHK024 - A dependência desta feature em relação à SF-016 (métricas já existentes) e à SF-019 (hot-plug, para o edge case de reconexão) está referenciada de forma rastreável em `spec.md`/`plan.md`, permitindo a um revisor confirmar que ambas já estão implementadas e estáveis antes deste gate? [Dependency, Spec Referências]

## Ambiguities & Conflicts

- [ ] CHK025 - Existe alguma leitura da spec em que "sinal equivalente já exposto" (linguagem original da issue #17) poderia ser interpretado como permitindo um sinal diferente de `p95Ms` no futuro, e isso está reconciliado com a decisão fechada nas Clarifications (p95 como único sinal de decisão)? [Ambiguity, Spec Input/Clarifications]

## Notes

- Itens marcados [Gap] ou [Ambiguity] sem resolução até o gate G2 devem virar tarefas explícitas em `tasks.md` (ex.: decisão de design a registrar) ou clarificações adicionais antes do Implement — não devem ser resolvidos silenciosamente durante a codificação.
- Foco desta rodada: política adaptativa/histerese, contrato/isolamento e testabilidade sem GPU/hardware (conforme selecionado). Configuração/flag/observabilidade recebeu cobertura mais leve (CHK002, CHK003, CHK016) e pode justificar uma rodada dedicada futura se o gate identificar lacunas ali.
