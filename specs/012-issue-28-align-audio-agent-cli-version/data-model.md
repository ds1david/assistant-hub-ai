# Data Model: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

N/A — esta correção não introduz nem altera nenhuma entidade de domínio, schema de evento ou dado
persistido. O único "dado" envolvido é a string de versão do pacote (`assistant_hub_audio.__version__`),
tratada como metadado de build, não como entidade — ver `research.md` (Decisões 1 e 2) para onde essa
string passa a ser mantida e `spec.md` (Key Entities) para a descrição não-técnica da "fonte única de
versão" e da "versão reportada do audio-agent".
