[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$LinuxRepo = "/home/david/workspace/assistant-hub-ai"
)

$ErrorActionPreference = "Stop"
$StateDir = "$env:LOCALAPPDATA\AssistantHubAI\run"
$PidFile = Join-Path $StateDir "audio-agent-host.pid"

if (Test-Path $PidFile) {
    $AgentPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($AgentPid -and (Get-Process -Id $AgentPid -ErrorAction SilentlyContinue)) {
        & taskkill.exe /PID $AgentPid /T /F | Out-Null
        Write-Host "Agente Windows encerrado. PID=$AgentPid"
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$StopCommand = "cd '$LinuxRepo' && docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.gpu.yml down --remove-orphans"
& wsl.exe -d $Distro -- bash -lc $StopCommand
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao encerrar o Docker Compose no WSL."
}
Write-Host "Assistant Hub AI encerrado."
