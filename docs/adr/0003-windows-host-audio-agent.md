# ADR-0003 — Captura de áudio Windows no host

- Status: aceito
- Data: 2026-07-16

## Contexto

Containers Linux e processos no WSL não possuem acesso direto e confiável aos endpoints de áudio do Windows. A captura do áudio reproduzido exige loopback WASAPI. O usuário pode alternar entre alto-falantes, conference cam, headset Bluetooth e microfones externos.

## Decisão

Executar um agente pequeno e nativo no Windows. Ele:

- enumera entradas e endpoints de loopback;
- permite configurar múltiplos canais lógicos por perfil YAML;
- mantém cada endpoint em conexão WebSocket independente;
- atribui `channelId`, `sourceType`, rótulo e metadados de dispositivo;
- normaliza cada fluxo para PCM mono de 16 kHz;
- reenumera e tenta reconectar quando um dispositivo desaparece.

O desenvolvimento principal permanece no WSL, mas o processo de captura é executado com Python Windows. Uma evolução futura poderá substituir o backend Python por um agente .NET/Core Audio sem alterar o contrato de rede.

## Diferenciação de canais

A separação garantida no MVP é por endpoint Windows:

- um microfone físico ou virtual gera um canal de entrada;
- o loopback de cada saída selecionada gera um canal de áudio remoto;
- vários canais podem ser capturados simultaneamente.

Não é possível separar aplicativos que reproduzem no mesmo endpoint usando o loopback tradicional. Captura por processo/aplicativo será um plugin específico.

## Seleção de dispositivo

O MVP aceita:

- índice retornado pela enumeração;
- expressão regular aplicada ao nome;
- dispositivo padrão.

Índices podem mudar após reconexão ou reinicialização. Uma release posterior adotará o endpoint ID do MMDevice e notificações nativas de hot-plug como identidade persistente.

## Consequências

- instalação local mínima é necessária no Windows;
- o serviço pesado continua isolado em Docker/WSL;
- problemas de hardware e Bluetooth ficam concentrados no agente;
- perfis diferentes podem representar conference cam, headset Bluetooth e microfones USB;
- o contrato de transcrição precisa conservar a identidade do canal e do dispositivo.
