param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$SetupTemp = Join-Path $ProjectRoot ".setup-tmp"
New-Item -ItemType Directory -Force -Path $SetupTemp | Out-Null
$env:TEMP = $SetupTemp
$env:TMP = $SetupTemp

Write-Host "[1/4] Memeriksa Python 3.12..." -ForegroundColor Cyan
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 --version
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 tidak ditemukan. Instal Python 3.12 lalu jalankan ulang." }
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Pembuatan virtual environment gagal." }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($Version -ne "3.12") { throw "Ditemukan Python $Version. Proyek ini direkomendasikan menggunakan Python 3.12." }
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Pembuatan virtual environment gagal." }
} else {
    throw "Python tidak ditemukan. Instal Python 3.12 dan aktifkan opsi Add Python to PATH."
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
Write-Host "[2/4] Memperbarui pip..." -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Pembaruan pip gagal." }

Write-Host "[3/4] Menginstal dependensi..." -ForegroundColor Cyan
& $Python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Instalasi dependensi gagal." }

if (-not $SkipTests) {
    Write-Host "[4/4] Menjalankan pengujian..." -ForegroundColor Cyan
    & $Python -m pytest -q -p no:tmpdir -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw "Pengujian gagal. Periksa output di atas." }
} else {
    Write-Host "[4/4] Pengujian dilewati." -ForegroundColor Yellow
}

Write-Host "`nSetup selesai. Jalankan aplikasi dengan:" -ForegroundColor Green
Write-Host "  .\scripts\run.ps1"
