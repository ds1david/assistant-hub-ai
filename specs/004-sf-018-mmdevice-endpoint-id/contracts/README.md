# Contratos — SF-018 (delta)

O contrato autoritativo vive em `contracts/` na raiz do monorepo (P4). Este diretório documenta apenas o **delta** introduzido pela SF-018 — não duplica schemas.

## 1. `contracts/transcript-event.v2.schema.json` (aditivo)

Campo novo, opcional e anulável, no objeto `device`:

```json
"device": {
  "required": ["index", "name"],
  "properties": {
    "index": {"type": ["integer", "null"]},
    "name": {"type": ["string", "null"]},
    "endpointId": {"type": ["string", "null"]}
  }
}
```

- Sem bump de versão (permanece v2); `required` inalterado.
- Produtores sem endpoint conhecido (Linux, perfis legados) omitem ou enviam `null`.
- Compatibilidade verificada por teste de contrato (eventos com e sem o campo validam).

## 2. WebSocket de áudio (`services/transcription-service/app/main.py`)

Query param novo e opcional na conexão do canal:

```
ws://<host>/...?sessionId=...&channelId=...&sourceType=...&endpointId=<MMDevice id>
```

- Ausente ⇒ comportamento anterior; presente ⇒ ecoado em `device.endpointId` dos eventos v2 do canal.

## 3. Perfil YAML do agente (superfície de configuração)

Chave nova no seletor de dispositivo do canal:

```yaml
channels:
  - id: mic
    device:
      endpointId: "{0.0.1.00000000}.{...}"   # novo — prioridade máxima
      index: 3                               # opcional, coexistência p/ agentes antigos
```

- `endpointId` pode coexistir apenas com `index`; demais combinações permanecem exclusivas.
- Agentes antigos ignoram a chave desconhecida e seguem usando `index`.

## 4. CLI `list-devices`

Saída (incl. `--json`) passa a incluir `endpointId` por dispositivo quando a correlação é possível; ausente/null fora do Windows ou sem correlação.
