$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:PYTHONPATH = $repoRoot
uvicorn dashboard_server:app --reload --host 0.0.0.0 --port 8000
