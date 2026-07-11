$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:PYTHONPATH = $repoRoot
$python = 'E:/Python/python.exe'
& $python -c "from app.application import app; import httpx; import asyncio; from fastapi.testclient import TestClient; client=TestClient(app); print(client.get('/health').json())"
