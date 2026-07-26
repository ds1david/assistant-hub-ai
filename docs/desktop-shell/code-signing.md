# Code signing — preparação (R5 / issue #66)

Este repositório **não** contém certificados, chaves privadas nem senhas de assinatura.
O pipeline e o runbook geram artefatos e **checksums**; a assinatura é opcional e externa.

## Objetivos

1. Artefatos MSI/NSIS reproduzíveis via `cargo tauri build --features gui`.
2. Arquivo `SHA256SUMS` (hashes SHA-256) ao lado dos instaladores.
3. Quando houver certificado de code signing Windows, assinar **depois** do build e regenerar checksums.

## Sem certificado (default open-source / CI)

- CI (`desktop-release.yml`) e `scripts/windows/release-desktop-shell.ps1` publicam:
  - instaladores (quando o build Windows completa);
  - `SHA256SUMS`.
- **Não falhar** o release se `SIGN_*` secrets estiverem ausentes.

## Com certificado (operador / org)

### Pré-requisitos

- Certificado Authenticode (`.pfx` ou token HSM/USB) da autoridade de confiança.
- Windows SDK `signtool.exe` (Windows SDK / Build Tools).
- Secrets **apenas** no ambiente local ou no GitHub Actions **encrypted secrets** (nunca no git):
  - `WINDOWS_CERTIFICATE` (base64 do PFX) ou path local
  - `WINDOWS_CERTIFICATE_PASSWORD`

### Passos sugeridos (local)

```powershell
# 1. Build + checksums
.\scripts\windows\release-desktop-shell.ps1 -UseRealSidecar

# 2. Assinar cada artefato (exemplo — ajuste paths)
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
Get-ChildItem dist\desktop-release\*.msi, dist\desktop-release\*.exe | ForEach-Object {
  & $signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
    /f $env:WINDOWS_CERT_PATH /p $env:WINDOWS_CERT_PASSWORD $_.FullName
}

# 3. Regenerar checksums após assinatura
# (no WSL, a partir da raiz do monorepo)
# ./scripts/release/checksum-artifacts.sh dist/desktop-release
```

### CI (futuro, opcional)

Se secrets `WINDOWS_CERTIFICATE` e `WINDOWS_CERTIFICATE_PASSWORD` existirem no repositório:

1. Importar PFX no store do runner.
2. Passar configuração de assinatura ao Tauri (`tauri.conf.json` / env `TAURI_*`) **ou** `signtool` pós-build.
3. Regenerar `SHA256SUMS`.

Enquanto secrets não existirem, o job **não** tenta assinar (residual documentado).

## Verificação de integridade (usuário)

```bash
# Linux/macOS/WSL
cd dist/desktop-release   # ou pasta de download
sha256sum -c SHA256SUMS
```

```powershell
# Windows
Get-FileHash -Algorithm SHA256 .\Assistant*.msi
# comparar com a linha em SHA256SUMS
```

## Relação com auto-update

Assinatura de instalador **não** é o mesmo que update automático assinado (fora de #66).
Ver `specs/002-desktop-distribution/` para a visão completa.
