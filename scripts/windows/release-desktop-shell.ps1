# Release local do desktop-shell: tauri build + SHA256SUMS.
# Host Windows nativo (não WSL). issue #66 / specs/031
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [switch]$UseRealSidecar,
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$shell = Join-Path $RepoRoot "apps\desktop-shell"
$srcTauri = Join-Path $shell "src-tauri"
$bundleRoot = Join-Path $srcTauri "target\release\bundle"
$outDir = Join-Path $RepoRoot "dist\desktop-release"

Write-Host "==> desktop-shell release (repo: $RepoRoot)"

if (-not $UseRealSidecar) {
  Write-Host "==> ensuring sidecar stub (use -UseRealSidecar after build-audio-agent-sidecar.ps1)"
  & (Join-Path $PSScriptRoot "ensure-sidecar-stub.ps1") -RepoRoot $RepoRoot
} else {
  $sidecar = Join-Path $srcTauri "binaries\assistant-hub-audio-x86_64-pc-windows-msvc.exe"
  if (-not (Test-Path $sidecar)) {
    throw "sidecar real ausente: $sidecar — rode build-audio-agent-sidecar.ps1"
  }
}

if (-not $SkipBuild) {
  Push-Location $shell
  try {
    npm ci
    npm test
    npm run build
    cargo tauri build --features gui
  } finally {
    Pop-Location
  }
}

if (-not (Test-Path $bundleRoot)) {
  throw "bundle não encontrado: $bundleRoot (rode sem -SkipBuild)"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
# Copia MSI/NSIS se existirem
Get-ChildItem -Path $bundleRoot -Recurse -Include *.msi,*.exe -ErrorAction SilentlyContinue |
  ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $outDir $_.Name) -Force
    Write-Host "copiado: $($_.Name)"
  }

# Checksums via Git Bash / WSL sha256sum se disponível; senão Get-FileHash
$sums = Join-Path $outDir "SHA256SUMS"
$files = Get-ChildItem -Path $outDir -File | Where-Object { $_.Name -ne "SHA256SUMS" -and $_.Name -ne "SHA256SUMS.txt" }
if ($files.Count -eq 0) {
  throw "nenhum instalador em $outDir"
}

$lines = foreach ($f in $files) {
  $hash = (Get-FileHash -Algorithm SHA256 -Path $f.FullName).Hash.ToLowerInvariant()
  "{0}  {1}" -f $hash, $f.Name
}
$lines | Set-Content -Path $sums -Encoding ascii
Write-Host "==> $sums"
Get-Content $sums
Write-Host "Release artifacts em: $outDir"
Write-Host "Assinatura: veja docs/desktop-shell/code-signing.md (não embutida neste script)."
