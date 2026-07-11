$ErrorActionPreference = 'Stop'
$envPath = Join-Path $PSScriptRoot '..' 'config.env'
if (-not (Test-Path $envPath)) {
    Write-Host 'config.env not found. Copy config.env.example to config.env and fill values.'
    exit 1
}
Write-Host "Verified config at $envPath"
