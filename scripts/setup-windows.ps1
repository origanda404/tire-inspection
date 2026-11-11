$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    py -3.14 -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create .venv. Install Python 3.14 or select a compatible Python explicitly.' }
}
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements-windows.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $venvPython (Join-Path $projectRoot 'scripts/verify-workspace.py')
if ($LASTEXITCODE -ne 0) { throw 'Workspace verification failed.' }
