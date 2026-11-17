# Automobile Data Pipeline Assignment

## 1. Deskripsi dan sumber dataset
Dataset berisi atribut kendaraan, spesifikasi mesin, konsumsi bahan bakar, dan harga. File sumber yang digunakan adalah `automobileEDA_dirty_training.csv` yang disediakan untuk assignment ini.

## 2. Struktur project
```text
data-pipeline-assignment/
├── data/
│   ├── raw/automobileEDA_dirty_training.csv
│   └── processed/automobileEDA_processed.csv
├── src/pipeline.py
├── documentation/data-flow-diagram.png
├── README.md
└── requirements.txt
```

## 3. Kondisi awal dataset
Hasil inspeksi Pandas pada file sumber:
- Ukuran awal: **205 baris × 30 kolom**.
- Missing values: **17 sel** pada 7 kolom: `transaction_date` (2), `make` (2), `num-of-doors` (2), `stroke` (4), `horsepower` (3), `price` (3), dan `horsepower-binned` (1).
- Duplicate records: **4 baris**.
- `transaction_date` bertipe `object`, padahal semestinya tanggal (`datetime`).
- Kategori memiliki variasi kapitalisasi/spasi, misalnya `make` (`ALFA-ROMERO`, `Audi`, `dodge  `), `body-style` (`sedan`, `SEDAN`, `Sedan`), `drive-wheels` (`rwd`, `RWD`, `AWD`), dan `fuel-system` (`mpfi`, `MPFI`, `Mpfi`).
- Format `transaction_date` bercampur (ISO, angka dengan slash/hyphen, dan nama bulan).

## 4. Data cleaning dan alasan
Cleaning dilakukan pada salinan DataFrame; file di `data/raw/` tidak diubah.
- Kolom teks kategorikal di-trim dan diubah ke lowercase agar spasi dan kapitalisasi seragam.
- Tanggal di-parse ke datetime dengan penanganan format ISO, angka slash/hyphen, dan nama bulan. Dua tanggal yang memang kosong tetap `NaT` karena tanggal tidak boleh direka. Format angka yang ambigu ditafsirkan dengan aturan parser yang dijelaskan di fungsi `parse_mixed_dates`.
- Empat baris duplikat dihapus setelah normalisasi teks.
- Missing `make`, `num-of-doors`, dan `horsepower-binned` diisi modus (kategori paling sering).
- Missing `normalized-losses`, `stroke`, `horsepower`, dan `price` diisi median agar tidak terlalu sensitif terhadap nilai ekstrem.
- Missing `transaction_date` dipertahankan sebagai `NaT`; tidak ada dasar untuk menebak tanggal transaksi.
- Nilai kategori `AWD` dipertahankan sebagai kategori berbeda dari `4wd`; penyamaan makna tanpa konfirmasi domain tidak dilakukan.

## 5. Data transformation
- `price` dinormalisasi dengan Min-Max Scaling ke kolom baru `price_minmax`, menggunakan rumus `(x - min) / (max - min)`. Kolom harga asli tetap dipertahankan.
- `body-style` di-encode menggunakan One-Hot Encoding (`pandas.get_dummies`) menjadi kolom seperti `body_style_sedan` dan `body_style_hatchback`. Kolom kategori aslinya juga dipertahankan.

Contoh ilustratif dari record pertama (nilai aktual dihitung ulang saat pipeline dijalankan):

| Kolom | Sebelum | Sesudah |
|---|---:|---:|
| `price` | 13495 | `price_minmax` = (13495 - harga minimum) / (harga maksimum - harga minimum) |
| `body-style` | convertible | `body_style_convertible` = 1; kategori body-style lain = 0 |

## 6. Hasil jumlah data
- Sebelum cleaning: **205 baris**.
- Sesudah penghapusan duplikat: **201 baris**.
- Sesudah penghapusan 4 duplikat, tersisa **201 baris**. Missing values setelah cleaning adalah **2**, keduanya pada `transaction_date`; tanggal tidak diketahui sengaja dipertahankan sebagai `NaT`.

## 7. Instalasi dependency
```bash
python -m pip install -r requirements.txt
```

## 8. Menjalankan pipeline
Dari direktori utama project:
```bash
python src/pipeline.py
```

## 9. Alur ETL
- **Extract:** membaca CSV dari `data/raw/`.
- **Transform:** inspeksi, cleaning, normalisasi harga, dan encoding kategori.
- **Load:** menyimpan hasil ke `data/processed/automobileEDA_processed.csv`.

## 10. Lokasi output
`data/processed/automobileEDA_processed.csv`

## 11. Catatan
Raw dataset tidak ditimpa. Pipeline menghasilkan processed dataset secara otomatis.
