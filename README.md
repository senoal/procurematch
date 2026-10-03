# Purchase Order Matching System

MVP aplikasi web untuk 3-way matching Purchase Order, Invoice, dan Goods Receipt.

Panduan penggunaan lengkap tersedia di [`docs/PANDUAN_PENGGUNA.md`](docs/PANDUAN_PENGGUNA.md).

## Menjalankan aplikasi

```powershell
python -m pip install -r requirements.txt
python run.py
```

Buka `http://127.0.0.1:5000`, lalu klik **Load demo data** untuk membuat contoh transaksi.

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
python -m pytest
```

Database SQLite dibuat otomatis di `instance/purchase_matching.sqlite`.
