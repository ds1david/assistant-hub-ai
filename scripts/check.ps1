$ErrorActionPreference = "Stop"

Write-Host "Checking Python syntax..."
python -m compileall services/transcription-service/app
python -m compileall agents/windows-audio-agent/src

if (Get-Command mvn -ErrorAction SilentlyContinue) {
  Write-Host "Running Maven tests..."
  mvn test
} else {
  Write-Warning "Maven não encontrado; testes Java não executados."
}
