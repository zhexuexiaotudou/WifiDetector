$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path .venv\Scripts\python.exe) {
  & .\.venv\Scripts\python.exe -m app.cli doctor
} else {
  py -m app.cli doctor
}
