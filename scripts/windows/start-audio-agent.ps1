[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Session,

    [Parameter(Mandatory = $true)]
    [string]$Profile,

    [string]$Server = "ws://127.0.0.1:8001",
    [string]$RecordDir = "$env:USERPROFILE\AssistantHubAI\recordings",
    [string]$Venv = "$env:LOCALAPPDATA\AssistantHubAI\audio-agent-venv",
    [string]$StateDir = "$env:LOCALAPPDATA\AssistantHubAI\run"
)

$ErrorActionPreference = "Stop"
$Executable = Join-Path $Venv "Scripts\assistant-hub-audio.exe"
if (-not (Test-Path $Executable)) {
    throw "Audio agent executable was not found: $Executable"
}
if (-not (Test-Path $Profile)) {
    throw "Audio profile was not found: $Profile"
}

New-Item -ItemType Directory -Force -Path $RecordDir | Out-Null
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

$PidFile = Join-Path $StateDir "audio-agent.pid"
$OutLog = Join-Path $StateDir "audio-agent.out.log"
$ErrLog = Join-Path $StateDir "audio-agent.err.log"

if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ExistingPid -and (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue)) {
        throw "Audio agent is already running with PID $ExistingPid"
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$Arguments = @(
    "--log-level", "INFO",
    "run",
    "--session", $Session,
    "--server", $Server,
    "--profile", $Profile,
    "--record-dir", $RecordDir
)

$Process = Start-Process `
    -FilePath $Executable `
    -ArgumentList $Arguments `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog

$Process.Id | Set-Content -Encoding ascii $PidFile
Start-Sleep -Seconds 2

if ($Process.HasExited) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    throw "Audio agent exited during startup. Inspect $ErrLog and $OutLog"
}

Write-Host "Audio agent started in background. PID=$($Process.Id)"
Write-Host "stdout: $OutLog"
Write-Host "stderr: $ErrLog"
