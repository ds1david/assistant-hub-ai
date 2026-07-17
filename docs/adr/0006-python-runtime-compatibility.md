# ADR 0006 — Compatibilidade do runtime Python do serviço de transcrição

## Status

Aceito.

## Contexto

A imagem CPU usa Python 3.11, enquanto a imagem GPU é baseada em Ubuntu 22.04 e instala o Python 3.10 pelos repositórios da distribuição. O uso de `datetime.UTC`, disponível somente a partir do Python 3.11, causava falha durante a importação da aplicação na imagem GPU.

## Decisão

O serviço de transcrição deve permanecer compatível com Python 3.10 e 3.11. APIs exclusivas de versões posteriores não devem ser usadas sem uma camada explícita de compatibilidade.

Datas UTC devem ser produzidas com:

```python
from datetime import datetime, timezone

datetime.now(timezone.utc)
```

O CI deve instalar as dependências e importar `app.main` em Python 3.10 e 3.11. Apenas executar `compileall` não é suficiente, porque ele não valida símbolos importados em tempo de execução.

## Consequências

- a mesma base de código roda nas imagens CPU e GPU;
- regressões de compatibilidade são detectadas antes do merge;
- uma futura atualização da imagem CUDA pode elevar a versão mínima do Python mediante novo ADR.
