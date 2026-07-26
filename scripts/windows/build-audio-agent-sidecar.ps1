#Requires -Version 5.1
<#
.SYNOPSIS
  Prepares the Windows audio agent binary for Tauri externalBin packaging (R5 / 025).

.DESCRIPTION
  1. Ensures a venv with assistant-hub-audio installed (editable).
  2. Optionally builds a one-file exe with PyInstaller if available.
  3. Copies the result to apps/desktop-shell/src-tauri/binaries/ with the
     target-triple name expected by Tauri 2 externalBin.

  Run on a Windows host (not WSL). See docs/desktop-shell/packaging.md.

.PARAMETER UsePyInstaller
  If set, try `pyinstaller` one-file build. Default: copy venv Scripts launcher.

.PARAMETER TargetTriple
  Rust/Tauri target triple suffix. Default: x86_64-pc-windows-msvc
#>
param(
    [switch]$UsePyInstaller,
    [string]$TargetTriple = "x86_64-pc-windows-msvc"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$AgentDir = Join-Path $RepoRoot "agents\windows-audio-agent"
$BinariesDir = Join-Path $RepoRoot "apps\desktop-shell\src-tauri\binaries"
$VenvDir = Join-Path $env:LOCALAPPDATA "AssistantHubAI\audio-agent-venv"
$OutName = "assistant-hub-audio-$TargetTriple.exe"
$OutPath = Join-Path $BinariesDir $OutName

Write-Host "Repo: $RepoRoot"
Write-Host "Output: $OutPath"

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null

if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    Write-Host "Creating venv at $VenvDir"
    py -3.12 -m venv $VenvDir
}

$Pip = Join-Path $VenvDir "Scripts\pip.exe"
$Python = Join-Path $VenvDir "Scripts\python.exe"
& $Pip install -U pip
& $Pip install -e $AgentDir

$Launcher = Join-Path $VenvDir "Scripts\assistant-hub-audio.exe"
if (-not (Test-Path $Launcher)) {
    throw "Expected launcher not found: $Launcher"
}

if ($UsePyInstaller) {
    & $Pip install pyinstaller
    $Entry = Join-Path $AgentDir "src\assistant_hub_audio\main.py"
    $Work = Join-Path $env:TEMP "assistant-hub-audio-pyinstaller"
    New-Item -ItemType Directory -Force -Path $Work | Out-Null
    Push-Location $Work
    try {
        & $Python -m PyInstaller --onefile --name assistant-hub-audio --clean $Entry
        $Built = Join-Path $Work "dist\assistant-hub-audio.exe"
        if (-not (Test-Path $Built)) { throw "PyInstaller did not produce $Built" }
        Copy-Item -Force $Built $OutPath
    } finally {
        Pop-Location
    }
} else {
    Write-Host "Copying venv launcher (Developer-like). For a self-contained exe, re-run with -UsePyInstaller."
    Copy-Item -Force $Launcher $OutPath
}

# Also place un-suffixed name for local non-bundle experiments
Copy-Item -Force $OutPath (Join-Path $BinariesDir "assistant-hub-audio.exe")

Write-Host "Done. Verify:"
& $OutPath --version
Write-Host "Next: cd apps\desktop-shell && cargo tauri build --features gui"
