# Panduan Pengguna Purchase Order Matching System

## 1. Tujuan sistem

Purchase Order Matching System membantu perusahaan memastikan bahwa tagihan supplier layak diproses untuk pembayaran.

Sistem membandingkan tiga dokumen:

1. **Purchase Order (PO)** — barang, kuantitas, dan harga yang dipesan perusahaan.
2. **Goods Receipt (GR)** — barang dan kuantitas yang benar-benar diterima.
3. **Invoice** — barang, kuantitas, dan harga yang ditagihkan supplier.

Proses ini disebut **3-way matching**. Tujuan akhirnya adalah menjawab pertanyaan berikut:

> Apakah barang yang ditagihkan sesuai dengan barang yang dipesan dan diterima?

Jika seluruh informasi sesuai, invoice mendapat status **Matched**. Jika tidak, sistem menunjukkan perbedaannya agar tim finance tidak memproses tagihan yang salah.

### Contoh sederhana

Perusahaan membuat PO untuk 10 laptop dengan harga Rp12.500.000 per unit. Gudang menerima 10 laptop dan supplier menagihkan 10 laptop dengan harga yang sama. Hasil transaksi adalah **Matched**.

Jika gudang baru menerima 8 laptop, hasilnya menjadi **Partial Match**. Jika supplier menagihkan harga Rp13.000.000 per unit, hasilnya menjadi **Mismatch**.

---

## 2. Jenis status

Aplikasi memiliki dua kelompok status yang berbeda: lifecycle status dan matching status.

### 2.1 Lifecycle status

Lifecycle status menjelaskan kondisi sebuah dokumen.

| Status | Arti |
|---|---|
| `Draft` | Dokumen masih dapat diedit dan belum digunakan dalam proses matching. |
| `Submitted` | Dokumen sudah dikonfirmasi, dikunci, dan dapat digunakan dalam matching. |
| `Cancelled` | Dokumen telah dibatalkan, tidak digunakan dalam proses, tetapi tetap disimpan untuk audit. |

### 2.2 Matching status

Matching status merupakan hasil perbandingan PO, goods receipt, dan invoice.

| Status | Arti |
|---|---|
| `Matched` | Seluruh informasi utama sesuai. |
| `Partial Match` | Baru sebagian barang atau dokumen yang sesuai. |
| `Mismatch` | Ditemukan perbedaan penting pada supplier, produk, kuantitas, atau harga. |
| `Pending Review` | Dokumen atau referensi transaksi belum lengkap. |
| `Not Processed` | Matching belum dijalankan, biasanya karena dokumen masih Draft atau sudah Cancelled. |

Sebuah invoice dapat memiliki lifecycle status `Submitted` dan matching status `Mismatch`. Artinya, invoice sudah dikonfirmasi tetapi isinya tidak sesuai dengan PO atau penerimaan barang.

---

## 3. Menu aplikasi

### 3.1 Overview

Overview adalah dashboard utama untuk memantau kondisi transaksi pengadaan.

Informasi yang ditampilkan:

- Jumlah purchase order.
- Jumlah invoice.
- Jumlah transaksi berhasil matched.
- Jumlah transaksi yang memerlukan perhatian.
- Persentase keberhasilan matching.
- Distribusi hasil matching.
- Daftar invoice terbaru.

Tombol yang tersedia:

- **Load demo data** membuat data contoh untuk mencoba aplikasi.
- **Run matching** menjalankan ulang validasi seluruh invoice berstatus Submitted.

### 3.2 Documents

Documents merupakan registry seluruh dokumen pengadaan. Halaman ini memiliki tiga tab:

- Purchase Orders
- Invoices
- Goods Receipts

Setiap dokumen menampilkan nomor dokumen, supplier atau PO terkait, tanggal, nilai transaksi, nomor versi, lifecycle status, dan matching status untuk invoice.

Klik nomor dokumen untuk membuka halaman **Document Control**.

### 3.3 Document Control

Document Control adalah halaman detail dan pusat pengendalian lifecycle dokumen.

Informasi yang tersedia:

- Nomor dan versi dokumen.
- Supplier atau PO terkait.
- Tanggal dokumen.
- Daftar produk.
- Kuantitas dan harga satuan.
- Lifecycle status.
- Matching status untuk invoice.
- Audit history.
- Daftar revisi yang pernah disimpan.

Tindakan yang tersedia bergantung pada status dokumen.

#### Dokumen Draft

Pengguna dapat:

- Mengubah informasi dokumen.
- Mengubah produk, kuantitas, atau harga.
- Menambahkan dan menghapus baris produk.
- Menyimpan perubahan Draft.
- Submit dokumen.
- Menghapus Draft versi pertama yang belum pernah diproses dan tidak memiliki dependensi.

#### Dokumen Submitted

Dokumen menjadi read-only. Pengguna dapat membuka revisi atau membatalkan dokumen dengan memberikan alasan.

#### Dokumen Cancelled

Dokumen tidak dapat diubah atau diproses kembali. Datanya tetap disimpan untuk kebutuhan audit.

### 3.4 Exceptions

Exceptions menampilkan transaksi yang tidak berhasil matched.

Contoh masalah yang dapat ditemukan:

- Harga invoice berbeda dari PO.
- Kuantitas invoice berbeda dari PO.
- Barang yang diterima kurang atau berlebih.
- Produk invoice tidak terdapat dalam PO.
- Produk PO tidak terdapat dalam invoice.
- Supplier invoice berbeda dari supplier PO.
- Invoice belum terhubung dengan PO yang valid.

Setiap exception menampilkan nomor invoice, supplier, PO terkait, nilai invoice, jumlah masalah, dan penjelasan setiap masalah.

### 3.5 Data Intake

Data Intake digunakan untuk memasukkan data melalui Excel atau formulir manual.

#### Excel Import

Excel Import digunakan untuk memasukkan beberapa dokumen sekaligus.

1. Klik **Download Excel Template**.
2. Isi sheet `PurchaseOrders`, `GoodsReceipts`, dan `Invoices`.
3. Jangan mengubah nama sheet atau header kolom.
4. Pilih workbook pada area upload.
5. Klik **Validate & Import**.

Sistem memeriksa struktur sheet, header, nomor dokumen, format tanggal, nilai numerik, referensi PO, supplier, SKU produk, dan dokumen duplikat.

Proses impor bersifat atomik. Jika satu baris bermasalah, seluruh workbook dibatalkan sehingga tidak ada data yang tersimpan sebagian.

Dokumen dari Excel dibuat langsung sebagai `Submitted`, kemudian matching otomatis dijalankan.

#### Manual Entry

Manual Entry digunakan untuk memasukkan data secara bertahap. Jenis data yang dapat dibuat:

- Supplier
- Product
- Purchase Order
- Goods Receipt
- Invoice

Dokumen transaksi dari formulir manual disimpan sebagai `Draft`. Pengguna harus memeriksa dan men-submit dokumen dari menu Documents.

---

## 4. Alur penggunaan dari awal sampai akhir

### Tahap 1: Membuat supplier

Buka **Data Intake → Manual Entry → Supplier**.

Isi supplier code dan supplier name, lalu klik **Save Supplier**. Supplier diperlukan sebelum membuat purchase order.

Contoh:

- Supplier code: `SUP-010`
- Supplier name: `PT Sumber Makmur`

### Tahap 2: Membuat produk

Buka **Data Intake → Manual Entry → Product**.

Isi product SKU dan product name, lalu klik **Save Product**. Produk digunakan sebagai baris transaksi dalam PO, goods receipt, dan invoice.

Contoh:

- Product SKU: `PRD-010`
- Product name: `Printer Laser`

### Tahap 3: Membuat dan submit purchase order

Buka **Data Intake → Manual Entry → Purchase Order**.

Isi:

- Nomor PO.
- Supplier.
- Produk.
- Tanggal pemesanan.
- Tanggal estimasi penerimaan.
- Kuantitas.
- Harga satuan.

Setelah disimpan, PO berstatus `Draft`.

Untuk mengaktifkannya:

1. Buka menu Documents.
2. Pilih tab Purchase Orders.
3. Klik nomor PO.
4. Periksa seluruh data.
5. Klik **Submit Document**.

PO berstatus `Submitted` dan dapat digunakan oleh goods receipt serta invoice.

### Tahap 4: Mencatat penerimaan barang

Buka **Data Intake → Manual Entry → Goods Receipt**.

Isi:

- Nomor penerimaan.
- Purchase order terkait.
- Produk.
- Tanggal penerimaan.
- Kuantitas yang diterima.

Setelah disimpan, goods receipt berstatus `Draft`. Buka dokumennya dari menu Documents, periksa data, lalu klik **Submit Document**.

Barang hanya diperhitungkan dalam matching jika goods receipt sudah berstatus `Submitted`.

### Tahap 5: Membuat invoice

Buka **Data Intake → Manual Entry → Invoice**.

Isi:

- Nomor invoice.
- Purchase order terkait.
- Produk.
- Tanggal invoice.
- Kuantitas yang ditagihkan.
- Harga satuan invoice.

Setelah disimpan, invoice berstatus `Draft`.

Untuk menjalankan matching:

1. Buka menu Documents.
2. Pilih tab Invoices.
3. Klik nomor invoice.
4. Periksa data.
5. Klik **Submit Document**.

Matching otomatis dijalankan setelah invoice disubmit.

### Tahap 6: Memeriksa hasil matching

Hasil matching dapat dilihat pada halaman detail invoice, dashboard Overview, dan menu Exceptions.

- Jika hasilnya `Matched`, data PO, penerimaan, dan invoice sesuai.
- Jika hasilnya `Partial Match` atau `Mismatch`, buka Exceptions untuk membaca penyebabnya.
- Jika hasilnya `Pending Review`, periksa kelengkapan dokumen dan referensinya.

---

## 5. Aturan matching

Sistem menjalankan pemeriksaan berikut.

### Supplier

Supplier invoice harus sama dengan supplier pada PO.

### Produk

Produk yang ditagihkan harus terdapat dalam PO.

### Kuantitas invoice

Kuantitas invoice dibandingkan dengan kuantitas pada PO.

### Harga invoice

Harga invoice dibandingkan dengan harga PO. Toleransi harga saat ini adalah **1%**. Selisih di atas 1% dianggap mismatch.

### Barang diterima

Total kuantitas goods receipt berstatus Submitted dibandingkan dengan kuantitas invoice dan PO. Beberapa goods receipt untuk satu PO dapat dijumlahkan sebagai penerimaan kumulatif.

### Contoh hasil

| PO | Diterima | Invoice | Hasil |
|---:|---:|---:|---|
| 100 unit | 100 unit | 100 unit dengan harga sesuai | `Matched` |
| 100 unit | 80 unit | 100 unit | `Partial Match` |
| 100 unit @ Rp50.000 | 100 unit | 100 unit @ Rp55.000 | `Mismatch` |

---

## 6. Memperbaiki data yang salah

Dokumen Submitted tidak dapat diedit langsung. Koreksi dilakukan melalui revisi agar versi sebelumnya tetap tersedia.

Contoh koreksi invoice:

1. Buka menu Documents.
2. Pilih tab Invoices.
3. Klik nomor invoice.
4. Isi **Revision Reason**.
5. Klik **Open Revision**.
6. Status berubah menjadi `Draft` dan nomor versi bertambah.
7. Ubah data yang salah.
8. Klik **Save Draft Changes**.
9. Periksa kembali data.
10. Klik **Submit Document**.

Sistem akan menyimpan snapshot versi sebelumnya, mencatat alasan revisi, mencatat nilai lama dan baru, membersihkan hasil matching lama, dan menjalankan matching baru setelah submit.

Audit History menampilkan perubahan dalam format yang mudah dibaca, contohnya:

> Unit price: Rp3.200.000 → Rp3.000.000

---

## 7. Membatalkan dokumen

Untuk membatalkan dokumen Submitted:

1. Buka halaman Document Control.
2. Isi **Cancellation Reason**.
3. Klik **Cancel / Void**.

Dokumen menjadi `Cancelled`. Dokumen tidak dihapus karena masih diperlukan untuk audit.

PO tidak dapat dibatalkan jika masih mempunyai invoice atau goods receipt aktif. Urutan pembatalan yang benar:

1. Cancel invoice.
2. Cancel goods receipt.
3. Cancel PO.

---

## 8. Audit History dan revisi

Audit History mencatat aktivitas seperti:

- Dokumen dibuat.
- Dokumen diimpor.
- Draft diperbarui.
- Dokumen disubmit.
- Revisi dibuka.
- Dokumen dibatalkan.
- Matching dijalankan.

Untuk perubahan Draft, sistem menampilkan field atau produk yang berubah, nilai lama, nilai baru, dan waktu perubahan.

Bagian **Stored Revisions** menyimpan versi dokumen sebelumnya beserta alasan revisi. Riwayat ini mendukung pemeriksaan internal karena perubahan tidak dilakukan secara tersembunyi.

---

## 9. Mencoba aplikasi dengan data demo

Jalankan aplikasi dari direktori proyek:

```powershell
python run.py
```

Buka `http://127.0.0.1:5000`, lalu:

1. Klik **Load demo data**.
2. Periksa ringkasan pada Overview.
3. Buka Documents untuk melihat PO, invoice, dan goods receipt.
4. Buka Exceptions untuk melihat transaksi bermasalah.
5. Klik nomor dokumen untuk melihat detail dan Audit History.
6. Coba buka revisi pada invoice.
7. Ubah harga atau kuantitas.
8. Submit kembali dan periksa hasil matching baru.

---

## 10. Ringkasan alur utama

```text
Buat supplier dan produk
        ↓
Buat PO sebagai Draft
        ↓
Periksa dan Submit PO
        ↓
Catat Goods Receipt sebagai Draft
        ↓
Periksa dan Submit Goods Receipt
        ↓
Buat Invoice sebagai Draft
        ↓
Periksa dan Submit Invoice
        ↓
Sistem menjalankan 3-way matching
        ↓
Matched → transaksi dapat dilanjutkan
Mismatch → periksa menu Exceptions
        ↓
Jika data salah, buka Revision
        ↓
Edit, Submit ulang, dan Match ulang
```

Inti aplikasi adalah memastikan perusahaan hanya melanjutkan invoice yang sesuai dengan pesanan dan barang yang benar-benar diterima.

---

## 11. Fitur yang belum tersedia

Versi aplikasi saat ini belum menyediakan:

- Login dan autentikasi.
- Role Administrator, Finance, Procurement, dan Warehouse.
- Approval invoice.
- Status dan proses pembayaran.
- Ekspor laporan CSV atau Excel.
- Lampiran dokumen asli.
- Preview data Excel sebelum konfirmasi impor.
- CRUD lengkap untuk master supplier dan produk.
- Pencarian, filter, dan pagination.
- Notifikasi.
- Dashboard grafik lanjutan.

Hard delete sudah dibatasi berdasarkan kondisi dokumen, tetapi belum berdasarkan peran Administrator karena autentikasi belum dibangun.

