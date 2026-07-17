# Feature 003 — AI Provider Hub

- Status: futura
- Release alvo: R6
- Prioridade: alta

## Objetivo

Permitir que o usuário configure, teste, altere e combine motores de IA sem recompilar o Assistant Hub AI.

A plataforma deverá aceitar chaves próprias, endpoints locais e serviços hospedados com camadas gratuitas ou de avaliação, incluindo o catálogo NVIDIA NIM, sem acoplar o domínio a um fornecedor específico.

## Capacidades

1. Cadastro de múltiplos provedores.
2. Configuração de endpoint, modelo, timeout, streaming e parâmetros de geração.
3. Referência segura a chaves, sem gravá-las no YAML.
4. Teste de conexão e descoberta opcional de modelos.
5. Seleção por perfil, persona e capacidade.
6. Fallback ordenado entre provedores.
7. Políticas de custo, privacidade, latência e disponibilidade.
8. Métricas por provedor e modelo.
9. Compatibilidade com APIs OpenAI-like e adaptadores específicos.
10. Importação/exportação de configuração sem segredos.

## Provedores iniciais planejados

- Ollama local;
- endpoint genérico OpenAI-compatible;
- OpenAI;
- Anthropic Claude;
- Google Gemini;
- xAI/Grok;
- NVIDIA NIM hospedado;
- NVIDIA NIM auto-hospedado;
- endpoint customizado HTTP compatível com o contrato interno.

A disponibilidade de modelos gratuitos, cotas e limites pertence ao provedor e pode mudar. A interface deve exibir o estado retornado pela API e nunca prometer gratuidade permanente.

## Tipos de capacidade

- `chat`;
- `responses`;
- `embeddings`;
- `vision`;
- `audio-input`;
- `tool-calling`;
- `structured-output`;
- `streaming`.

## Roteamento

O perfil de conversa poderá mapear tarefas para rotas diferentes:

```text
resposta em tempo real -> modelo de baixa latência
resumo final           -> modelo de maior qualidade
embeddings             -> modelo local
visão de tela           -> modelo multimodal
fallback                -> Ollama local
```

## Segurança

1. Chaves não entram no Git, logs, eventos ou exports.
2. No desktop, segredos usam o armazenamento seguro do sistema operacional.
3. No modo WSL Developer, segredos usam variáveis de ambiente ou arquivo local ignorado.
4. A UI mostra apenas prefixo/sufixo mascarado.
5. O botão de teste não imprime headers de autenticação.
6. Perfis podem proibir envio remoto de áudio, tela ou transcrição.

## Configurações editáveis

- nome e tipo do provedor;
- URL base;
- modelo padrão e modelos por capacidade;
- referência do segredo;
- headers adicionais permitidos;
- organização/projeto quando aplicável;
- temperatura, top-p, limite de tokens;
- timeout, tentativas e backoff;
- streaming;
- proxy;
- orçamento e limite por sessão;
- prioridade e fallback;
- política de dados por perfil.

## Critérios de aceite

1. Um novo endpoint OpenAI-compatible pode ser adicionado sem alterar código do core.
2. O usuário alterna entre Ollama e NVIDIA NIM por configuração.
3. Um perfil pode usar provedores diferentes para chat e embeddings.
4. Falha ou rate limit aciona fallback apenas quando a política permitir.
5. O teste de conexão informa autenticação, modelo inexistente e timeout de forma distinta.
6. Segredos nunca aparecem em logs, respostas da API ou arquivos exportados.
7. Métricas registram provedor, modelo, latência e uso, sem registrar a chave.
8. A aplicação permite desativar totalmente provedores remotos.

## Fora do escopo inicial

- marketplace comercial de chaves;
- revenda de créditos;
- escolha automática baseada somente em ranking público;
- upload automático de conversas para treinamento de terceiros;
- suporte a APIs sem autenticação ou TLS em ambientes não locais.
