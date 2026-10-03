# Purchase Order Matching System

Aplikasi web untuk 3-way matching Purchase Order, Invoice, dan Goods Receipt. Dibangun dengan Python, Flask, dan SQLite.

Panduan penggunaan lengkap tersedia di [`docs/PANDUAN_PENGGUNA.md`](docs/PANDUAN_PENGGUNA.md).

## Kebutuhan sistem

- Git
- Python 3.12
- Koneksi internet saat instalasi dependensi pertama
- Windows 10/11, macOS, atau Linux

Node.js tidak diperlukan untuk menjalankan aplikasi. Workbook template Excel sudah disertakan di repository.

## Instalasi di laptop baru

### Windows PowerShell

```powershell
git clone https://github.com/senoal/procurematch.git
cd procurematch
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\run.ps1
```

### macOS atau Linux

```bash
git clone https://github.com/senoal/procurematch.git
cd procurematch
chmod +x scripts/setup.sh scripts/run.sh
./scripts/setup.sh
./scripts/run.sh
```

Buka `http://127.0.0.1:5000`. Gunakan **Load demo data** untuk membuat transaksi contoh.

Endpoint `http://127.0.0.1:5000/health` dapat digunakan untuk memastikan aplikasi dan database sudah aktif.

## Instalasi manual

Jika tidak menggunakan skrip setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
python run.py
```

## Database dan konfigurasi

- Database SQLite dibuat otomatis di `instance/purchase_matching.sqlite` saat aplikasi pertama kali berjalan.
- Database lokal tidak disimpan di GitHub. Setiap laptop memperoleh database baru.
- Data demo dapat dibuat dari dashboard dengan tombol **Load demo data**.
- Untuk penggunaan selain development, salin `.env.example` menjadi `.env` atau tetapkan environment variable `SECRET_KEY` dengan nilai acak. Aplikasi membaca `SECRET_KEY` dari environment sistem.
- Jangan commit file `.env` atau database SQLite yang berisi data transaksi.

## Lifecycle dokumen

- Input manual dibuat sebagai `Draft` dan dapat diedit.
- Draft dapat dihapus selama belum pernah diproses dan tidak memiliki dokumen turunan.
- `Submit` mengunci dokumen dan menjalankan matching yang relevan.
- Koreksi dokumen Submitted dilakukan melalui `Open revision`; snapshot versi sebelumnya disimpan.
- `Cancel / Void` menonaktifkan dokumen tanpa menghapus riwayat audit.
- Impor Excel dianggap sebagai data tervalidasi dan dibuat langsung sebagai `Submitted`.

Menu **Documents** menyediakan halaman detail, kontrol lifecycle, versi revisi, dan audit history.

## Pengujian

```powershell
python -m pytest -q
```

Semua dependensi runtime dipin versinya di `requirements.txt`. Dependensi pengujian terdapat di `requirements-dev.txt`.

## Struktur penting

```text
app/                 kode aplikasi, template, CSS, JavaScript, dan skema database
app/static/templates template Excel yang dapat diunduh pengguna
docs/                panduan pengguna
instance/            database lokal (tidak di-commit)
scripts/             setup dan launcher lintas laptop
tests/               automated tests
run.py               entry point aplikasi
```
