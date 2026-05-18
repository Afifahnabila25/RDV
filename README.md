# 🚕 NYC Taxi Analysis — Kelompok 4
> Analisis Pendapatan & Operasional Taxi NYC  
> Mata Kuliah Rekayasa Data dan Visualisasi

**Anggota:** Ana Zahratul Firdausi · Aisha Maryam · Aufii Fathin Nabila · Dwi Cahya Maulani · Afifah Nabila Devi · Gladys Abel

---

## 📁 Struktur Folder

```
RDV/
├── data/
│   ├── raw/
│   │   ├── yellow/        # Parquet Yellow Taxi (tidak di-push ke GitHub)
│   │   ├── green/         # Parquet Green Taxi (tidak di-push ke GitHub)
│   │   └── external/      # Data cuaca & hari libur
│   └── final/
│       └── warehouse.duckdb
├── pipeline/
│   └── ingestion/
│       ├── download_tlc.py       # Download dataset TLC dari NYC
│       ├── fetch_external.py     # Download cuaca & hari libur
│       ├── flow_ingestion.py     # Prefect flow (orkestrasi pipeline)
│       └── verify_download.py    # Verifikasi hasil download
├── dashboard/
│   ├── app.py                    # Entry point Streamlit
│   └── pages/
│       ├── overview.py
│       ├── revenue_region.py
│       └── time_external.py
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup Awal

**1. Clone repository**
```bash
git clone <url-repo>
cd RDV
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

---

## 🔄 Menjalankan Pipeline Ingestion

Pipeline ingestion menggunakan **Prefect** untuk orkestrasi otomatis.  
Satu perintah akan menjalankan semua proses: download TLC + cuaca + hari libur.

### Opsi A — Jalankan langsung (tanpa monitoring UI)
```bash
python pipeline/ingestion/flow_ingestion.py
```

### Opsi B — Jalankan dengan Prefect UI (monitoring real-time)

**Terminal 1** — Start Prefect server:
```bash
python -m prefect server start
```

Buka browser ke **http://127.0.0.1:4200** untuk lihat dashboard monitoring.

**Terminal 2** — Jalankan flow:
```bash
python pipeline/ingestion/flow_ingestion.py
```

Di Prefect UI kamu bisa melihat:
- Status tiap task (running / completed / failed)
- Log output per task
- Retry otomatis jika ada task yang gagal

### Verifikasi hasil download
```bash
python pipeline/ingestion/verify_download.py
```
Output: jumlah file, ukuran, dan sampel isi data yang sudah ter-download.

---

## 📊 Menjalankan Dashboard Streamlit

Pastikan `data/final/warehouse.duckdb` sudah tersedia (dibuat oleh tim Storage/Ana).

```bash
streamlit run dashboard/app.py
```

Buka browser ke **http://localhost:8501**

### Fitur Dashboard
| Halaman | Isi |
|---|---|
| Overview | Total trip, total revenue, perbandingan Yellow vs Green |
| Revenue & Region | Analisis pendapatan per wilayah & zona |
| Time & External | Pola waktu, pengaruh cuaca & hari libur |

Gunakan **sidebar** untuk filter jenis taksi (Yellow/Green) dan tahun.

---

## 📦 Dataset

| Sumber | Periode | Keterangan |
|---|---|---|
| NYC TLC Yellow Taxi | Jan 2023 – Maret 2026 | Download via `download_tlc.py` |
| NYC TLC Green Taxi | Jan 2023 – Maret 2026 | Download via `download_tlc.py` |
| Open-Meteo Historical API | Jan 2023 – Maret 2026 | Cuaca harian NYC |
| Nager.Date API | 2023 – 2026 | Hari libur nasional AS |

> ⚠️ Folder `data/` tidak di-push ke GitHub karena ukurannya besar.  
> Download ulang dengan menjalankan pipeline ingestion di atas.

---

## 🛠️ Tech Stack

`Python` `DuckDB` `Prefect` `Streamlit` `Pandas` `Requests`
