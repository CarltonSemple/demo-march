param(
  [switch]$UnitOnly,
  [switch]$IntegrationOnly
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$functionsDir = Join-Path $repoRoot 'cloud-functions\functions'
$pythonExe = Join-Path $functionsDir 'venv\Scripts\python.exe'

if (-not (Test-Path $functionsDir)) {
  throw "Expected Functions directory at: $functionsDir"
}

if (-not (Test-Path $pythonExe)) {
  throw "Python venv not found at: $pythonExe`nCreate it under cloud-functions/functions/venv first."
}

Push-Location $functionsDir
try {
  & $pythonExe -m pip install -q -r requirements-dev.txt

  if ($UnitOnly -and $IntegrationOnly) {
    throw "Choose only one of -UnitOnly or -IntegrationOnly"
  }

  if ($UnitOnly) {
    & $pythonExe -m pytest -q -m "not integration"
  } elseif ($IntegrationOnly) {
    & $pythonExe -m pytest -q -m integration -rs
  } else {
    & $pythonExe -m pytest -q
  }
}
finally {
  Pop-Location
}
