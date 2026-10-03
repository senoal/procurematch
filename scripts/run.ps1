$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment belum tersedia. Jalankan .\scripts\setup.ps1 terlebih dahulu."
}

Set-Location $ProjectRoot
& $Python run.py
