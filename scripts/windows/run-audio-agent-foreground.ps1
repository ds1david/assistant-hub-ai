[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Session,

    [Parameter(Mandatory = $true)]
    [string]$Profile,

    [string]$Server = "ws://127.0.0.1:8001",
    [string]$RecordDir = "$env:USERPROFILE\AssistantHubAI\recordings",
    [string]$Venv = "$env:LOCALAPPDATA\AssistantHubAI\audio-agent-venv",
    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR")]
    [string]$LogLevel = "INFO",
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$AgentSource = Join-Path $RepoRoot "agents\windows-audio-agent"
$Python = Join-Path $Venv "Scripts\python.exe"
$Executable = Join-Path $Venv "Scripts\assistant-hub-audio.exe"

if (-not (Test-Path $Profile)) {
    throw "Perfil de áudio não encontrado: $Profile"
}
if (-not (Test-Path $AgentSource)) {
    throw "Código do agente não encontrado: $AgentSource"
}

if (-not (Test-Path $Python)) {
    Write-Host "Criando ambiente Python do agente em $Venv"
    $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -eq $PyLauncher) {
        throw "Python Launcher (py.exe) não encontrado no Windows."
    }
    & $PyLauncher.Source -3.12 -m venv $Venv
    $Reinstall = $true
}

if ($Reinstall -or -not (Test-Path $Executable)) {
    Write-Host "Instalando/atualizando agente Windows em modo editable"
    & $Python -m pip install --upgrade pip
    & $Python -m pip install --force-reinstall --editable $AgentSource
}

New-Item -ItemType Directory -Force -Path $RecordDir | Out-Null

Write-Host ""
Write-Host "Assistant Hub AI audio agent"
Write-Host "Session : $Session"
Write-Host "Profile : $Profile"
Write-Host "Server  : $Server"
Write-Host "Log     : $LogLevel"
Write-Host "O processo permanece em foreground. Pressione Ctrl+C para parar."
Write-Host ""

& $Executable `
    --log-level $LogLevel `
    run `
    --session $Session `
    --server $Server `
    --profile $Profile `
    --record-dir $RecordDir

if ($LASTEXITCODE -ne 0) {
    throw "O agente de áudio terminou com código $LASTEXITCODE"
}
