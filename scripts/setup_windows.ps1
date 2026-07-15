$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
py -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed with exit code $LASTEXITCODE" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed with exit code $LASTEXITCODE" }
& .\.venv\Scripts\python.exe -m pip install -e '.[dev,discovery]'
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed with exit code $LASTEXITCODE" }
Write-Host 'Setup complete. Confirm explicit authorization before field discovery.'
