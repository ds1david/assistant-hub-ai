# Visão do produto

## Posicionamento

**Assistant Hub AI** é uma plataforma extensível de inteligência contextual para conversas.

Ela transforma streams de áudio, vídeo, tela e eventos em sessões pesquisáveis, com contexto, decisões, tarefas, participantes, respostas sugeridas e memória de longo prazo.

## Problema

Ferramentas de reunião normalmente tratam a gravação como produto final. O Assistant Hub AI trata a gravação como uma fonte de eventos e conhecimento que pode alimentar diferentes assistentes.

## Conceitos principais

### Sessão

Unidade temporal de uma conversa. Possui perfil, participantes, fontes, artefatos e eventos.

### Fonte

Origem de dados: microfone, áudio de sistema, câmera, tela, arquivo, chat ou integração externa.

### Perfil

Composição declarativa de plugins, personas, políticas e prompts para um contexto específico.

Exemplos:

- entrevista técnica;
- entrevista comportamental;
- refinamento de produto;
- alinhamento de feature;
- mentoria;
- estudo;
- atendimento.

### Plugin

Capacidade isolada e substituível: captura, STT, LLM, resumo, memória, detecção de tarefas, gravação de tela, OCR ou integração.

### Assistente/persona

Papel de raciocínio ou resposta dentro de um perfil: recrutador, arquiteto, product owner, tech lead, facilitador ou observador.

## Princípios

1. Local-first, com provedores remotos opcionais.
2. Consentimento e controle de dados por padrão.
3. Core pequeno; capacidades em plugins.
4. Contratos versionados e eventos auditáveis.
5. Separação das origens antes de qualquer mixagem.
6. Perfis compõem comportamento sem recompilar o core.
7. Latência mensurável é requisito funcional.

## Não objetivos do MVP

- substituir plataformas de videoconferência;
- fazer reconhecimento facial;
- gravar silenciosamente sem conhecimento dos participantes;
- construir uma solução corporativa multi-tenant completa;
- fornecer resposta automática invisível em processos seletivos reais.

O MVP é uma ferramenta de desenvolvimento e treino sob controle do usuário.
