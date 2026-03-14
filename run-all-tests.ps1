param(
  [string]$PyFunctionBaseUrl = "http://127.0.0.1:5001/coach-app-demo-3132026/us-central1"
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "== Python tests ==" -ForegroundColor Cyan
& (Join-Path $repoRoot 'run-python-tests.ps1')

Write-Host "== Node (Express) tests ==" -ForegroundColor Cyan
$env:PY_FUNCTION_BASE_URL = $PyFunctionBaseUrl

Push-Location (Join-Path $repoRoot 'coach-mini-app\server')
try {
  if (-not (Test-Path (Join-Path (Get-Location) 'node_modules'))) {
    npm install
  }
  npm test
}
finally {
  Pop-Location
}
