[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$LinuxRepo = "/home/david/workspace/assistant-hub-ai",
    [string]$Session = ("session-" + (Get-Date -Format "yyyyMMdd-HHmmss")),
    [string]$ProfileRelative = "samples/audio-profiles/default.yaml",
    [switch]$NoBuild,
    [switch]$NoCache,
    [switch]$SkipModelLoad,
    [switch]$ReinstallAgent,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "wsl.exe não foi encontrado."
}

$WslScript = "$LinuxRepo/scripts/wsl/rebuild-and-start.sh"
$WslArguments = @("-d", $Distro, "--", "bash", $WslScript)
if ($NoBuild) { $WslArguments += "--no-build" }
if ($NoCache) { $WslArguments += "--no-cache" }
if ($SkipModelLoad) { $WslArguments += "--skip-model-load" }

Write-Host "Iniciando novo processo WSL para reconstruir e subir o Docker Compose..."
$WslProcess = Start-Process `
    -FilePath "wsl.exe" `
    -ArgumentList $WslArguments `
    -PassThru `
    -Wait `
    -NoNewWindow

if ($WslProcess.ExitCode -ne 0) {
    throw "A inicialização no WSL falhou com código $($WslProcess.ExitCode)."
}

$RepoUnc = "\\wsl.localhost\$Distro" + $LinuxRepo.Replace("/", "\")
$Profile = Join-Path $RepoUnc $ProfileRelative.Replace("/", "\")
$AgentScript = Join-Path $RepoUnc "scripts\windows\run-audio-agent-foreground.ps1"

if (-not (Test-Path $AgentScript)) {
    throw "Script do agente não encontrado: $AgentScript"
}
if (-not (Test-Path $Profile)) {
    throw "Perfil de áudio não encontrado: $Profile"
}

$PowerShellCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue
if ($null -eq $PowerShellCommand) {
    $PowerShellCommand = Get-Command powershell.exe -ErrorAction Stop
}

$StateDir = "$env:LOCALAPPDATA\AssistantHubAI\run"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$Launcher = Join-Path $StateDir "launch-audio-agent.ps1"

$EscapedAgentScript = $AgentScript.Replace("'", "''")
$EscapedSession = $Session.Replace("'", "''")
$EscapedProfile = $Profile.Replace("'", "''")
$ReinstallLiteral = if ($ReinstallAgent) { '$true' } else { '$false' }
$LauncherContent = "& '$EscapedAgentScript' -Session '$EscapedSession' -Profile '$EscapedProfile' -LogLevel INFO -Reinstall:$ReinstallLiteral"
$LauncherContent | Set-Content -Encoding utf8 $Launcher

$AgentArguments = @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"' + $Launcher + '"')
)

Write-Host "Abrindo um novo PowerShell para o agente de áudio em foreground..."
$AgentHost = Start-Process `
    -FilePath $PowerShellCommand.Source `
    -ArgumentList $AgentArguments `
    -PassThru

$AgentHost.Id | Set-Content -Encoding ascii (Join-Path $StateDir "audio-agent-host.pid")

if (-not $NoBrowser) {
    Start-Process "http://localhost:8001"
}

Write-Host ""
Write-Host "Assistant Hub AI iniciado."
Write-Host "Session: $Session"
Write-Host "Dashboard: http://localhost:8001"
Write-Host "PowerShell do agente: PID $($AgentHost.Id)"
