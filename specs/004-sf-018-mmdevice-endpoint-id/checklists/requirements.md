# Checklist — SF-018

## Requisitos

- [ ] endpointId resolve índice atual na captura
- [ ] erros distintos (missing / inactive / uncorrelated / kind mismatch)
- [ ] loopback via endpoint render
- [ ] legados index/nameRegex/default
- [ ] schema v2 aditivo
- [ ] sem fallback silencioso

## Segurança / privacidade

- [ ] sem segredos em logs
- [ ] mensagens de erro sem dados sensíveis de usuário

## Compatibilidade

- [ ] consumidores antigos ignoram endpointId
- [ ] YAML com endpointId+index aceito

## Documentação

- [ ] ADR-0011 coerente com o código
- [ ] evidência Windows preenchida
- [ ] samples/perfis exemplo (se aplicável)

## Testes

- [ ] pytest agent Linux
- [ ] contrato transcription com endpointId
- [ ] CI unit agent + smoke windows-latest
