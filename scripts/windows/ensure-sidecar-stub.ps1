# Cria um stub PE de assistant-hub-audio para empacotamento Tauri quando o agent real
# não está disponível (CI / packaging dry-run). issue #66
# NÃO use em produção — substitua pelo output de build-audio-agent-sidecar.ps1.
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
$binDir = Join-Path $RepoRoot "apps\desktop-shell\src-tauri\binaries"
$targetName = "assistant-hub-audio-x86_64-pc-windows-msvc.exe"
$outPath = Join-Path $binDir $targetName

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

$stubDir = Join-Path $env:TEMP "ah-sidecar-stub"
New-Item -ItemType Directory -Force -Path $stubDir | Out-Null
$mainRs = Join-Path $stubDir "main.rs"
@'
fn main() {
    let mut args = std::env::args().skip(1);
    match args.next().as_deref() {
        Some("--version") | Some("version") => {
            println!("assistant-hub-audio 0.0.0-ci-stub");
        }
        Some("list-devices") => {
            eprintln!("ci-stub: no devices");
            std::process::exit(0);
        }
        _ => {
            eprintln!("assistant-hub-audio ci-stub — not a real capture agent");
            std::process::exit(0);
        }
    }
}
'@ | Set-Content -Path $mainRs -Encoding utf8

Push-Location $stubDir
try {
  rustc --edition 2021 -O -o $outPath $mainRs
} finally {
  Pop-Location
}

if (-not (Test-Path $outPath)) {
  throw "falha ao gerar stub em $outPath"
}
Write-Host "stub sidecar: $outPath"
& $outPath --version
