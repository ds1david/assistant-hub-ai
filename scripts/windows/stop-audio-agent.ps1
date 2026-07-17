[CmdletBinding()]
param(
    [string]$StateDir = "$env:LOCALAPPDATA\AssistantHubAI\run"
)

$ErrorActionPreference = "Stop"
$PidFile = Join-Path $StateDir "audio-agent.pid"
if (-not (Test-Path $PidFile)) {
    Write-Host "No audio-agent PID file was found."
    exit 0
}

$AgentPid = Get-Content $PidFile -ErrorAction Stop
$Process = Get-Process -Id $AgentPid -ErrorAction SilentlyContinue
if ($null -eq $Process) {
    Remove-Item $PidFile -Force
    Write-Host "The recorded process is no longer running. PID file removed."
    exit 0
}

# Kill the supervisor and all isolated channel workers in its process tree.
& taskkill.exe /PID $AgentPid /T /F | Out-Null
Remove-Item $PidFile -Force
Write-Host "Audio agent stopped. PID=$AgentPid"
