# Research: SF-015 — Matriz manual de hardware R1

Nenhum `[NEEDS CLARIFICATION]` restou da spec ou do Technical Context do plano — as decisões abaixo documentam as escolhas feitas a partir do roadmap (issue #11) e do que já existe no repositório, sem ambiguidade que exigisse pergunta ao usuário.

## Decisão 1 — Reaproveitar a CLI existente, sem novo código

- **Decision**: Usar apenas os comandos já publicados pela SF-018 (`list-devices --json`, `probe --profile`, `run --session --profile`) para os três cenários; não escrever nenhum script ou automação nova.
- **Rationale**: A CLI já expõe tudo que os critérios de aceite exigem (enumeração, resolução por `endpointId`, captura com evento v2). Escrever ferramenta nova violaria a natureza "quase só documentação" da feature e o princípio P10 (validação manual, não automação de hardware).
- **Alternatives considered**: Um script Python que rodasse os três cenários em sequência e gerasse o Markdown automaticamente — rejeitado porque hardware físico (plugar Bluetooth, trocar conference cam) não é automatizável, e o valor de um script fino não compensa o código extra para uma feature de validação única.

## Decisão 2 — Um arquivo de evidência por cenário

- **Decision**: Criar `docs/validation/sf-015-conference-cam.md`, `docs/validation/sf-015-bluetooth-usb.md` e `docs/validation/sf-015-default-mic.md`, cada um seguindo o mesmo esqueleto de seções já usado em `docs/validation/sf-018-windows.md` (Ambiente, Dispositivos, Casos, Segurança, Resultado).
- **Rationale**: `docs/validation/sf-018-windows.md` já tem um formato validado e specificado nas checklists de device-identity (specs/004). Reaproveitar esse esqueleto por cenário mantém cada resultado PASS/FAIL/BLOCKED isolado e revisável em PR sem misturar cenários independentes num único arquivo gigante.
- **Alternatives considered**: Expandir `docs/validation/r1-audio-validation.md` (arquivo R1 genérico pré-existente) preenchendo os cenários "conference cam" e "Bluetooth" que já estão lá como placeholders. Rejeitado como único caminho porque esse arquivo não cobre o terceiro cenário (microfone default) nem a lista de casos granulares (list-devices/probe/run/reboot/hot-plug/endpoint desabilitado) que a spec exige verificar — ele é mantido como estava, e os arquivos novos por cenário são a fonte de verdade desta feature. Se desejado, uma feature futura pode consolidar ambos.

## Decisão 3 — Fechar a lacuna de evidência da SF-018 no mesmo ciclo

- **Decision**: O Cenário 3 (microfone default) reexecuta exatamente os 7 casos do template `docs/validation/sf-018-windows.md` (list-devices, probe, run, reboot/reenumeração, hot-plug parcial, endpoint desabilitado/inexistente, Bluetooth/nomes duplicados) e usa o resultado para preencher esse arquivo, além do seu próprio.
- **Rationale**: O checkpoint pós SF-018 já identificou esse arquivo como template em branco (nenhum checkbox marcado, resultado ainda `PASS | FAIL | BLOCKED` literal). Rodar os mesmos passos duas vezes seria retrabalho; a spec já assume esse reaproveitamento (FR-006, SC-003).
- **Alternatives considered**: Abrir uma sub-tarefa separada só para SF-018 antes de iniciar a SF-015 — rejeitado porque o usuário explicitamente optou por deixar a SF-015 cobrir essa lacuna retroativamente (decisão já tomada no checkpoint da conversa).

## Decisão 4 — Sem `contracts/`

- **Decision**: Esta feature não gera `contracts/`.
- **Rationale**: Não há interface nova (API, schema, comando CLI) sendo exposta ou alterada; a matriz apenas verifica contratos já publicados (evento v2, prioridade de seleção de dispositivo do ADR-0011). Documentar "contrato" aqui duplicaria o que já existe em `specs/004-sf-018-mmdevice-endpoint-id/contracts/README.md`.
- **Alternatives considered**: Copiar o contrato da SF-018 para esta pasta como referência — rejeitado por redundância; o plano linka diretamente para o contrato original.
