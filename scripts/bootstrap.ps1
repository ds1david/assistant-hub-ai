[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$LinuxRepo = "/home/david/workspace/assistant-hub-ai",
    [string]$Session = ("session-" + (Get-Date -Format "yyyyMMdd-HHmmss")),
    [switch]$NoCache
)

$StartScript = Join-Path $PSScriptRoot "windows\start-assistant-hub.ps1"
& $StartScript `
    -Distro $Distro `
    -LinuxRepo $LinuxRepo `
    -Session $Session `
    -ReinstallAgent `
    -NoCache:$NoCache
