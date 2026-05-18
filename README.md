# 🚕 NYC Taxi Analysis — Kelompok 4
> Analisis Pendapatan & Operasional Taxi NYC  
> Mata Kuliah Rekayasa Data dan Visualisasi

**Anggota:** Ana Zahratul Firdausi · Aisha Maryam · Aufii Fathin Nabila · Dwi Cahya Maulani · Afifah Nabila Devi · Gladys Abel

---

## 📁 Struktur Folder

```
RDV/
│
├── dashboard/                          # Step 5 — Streamlit Dashboard 
│   ├── app.py                          # Entry point utama Streamlit
│   └── pages/
│       ├── overview.py                 # Halaman ringkasan & KPI
│       ├── revenue_region.py           # Halaman peta choropleth & analisis zona
│       └── time_external.py            # Halaman heatmap, cuaca & hari libur
│
├── pipeline/
│   ├── ingestion/                      # Step 1 — Data Ingestion 
│   │   ├── download_tlc.py             # Download Yellow & Green Taxi dari NYC TLC
│   │   ├── fetch_external.py           # Fetch cuaca (Open-Meteo) & holiday (Nager.Date)
│   │   ├── flow_ingestion.py           # Prefect flow — orkestrasi & scheduling
│   │   └── verify_download.py          # Verifikasi kelengkapan file hasil download
│   │
│   ├── cleaning/                       # Step 2 — Preprocessing & Cleaning 
│   │   ├── clean_tlc.py                # Cleaning Yellow & Green Taxi (anomali + derived columns)
│   │   └── clean_external.py           # Cleaning data cuaca & hari libur
│   │
│   └── modelling/                      # Step 3 — Storage & Data Modelling 
│       └── build_warehouse.py          # Bangun star schema di DuckDB (fact + 4 dim tables)
│
├── analysis/                           # Step 4 — Analytical Queries 
│   └── run_analysis.py                 # Buat semua analytical views di warehouse.duckdb
│
├── data/
│   ├── raw/                            # Output Step 1 — data mentah (di-gitignore)
│   │   ├── yellow/                     # yellow_YYYY_MM.parquet (39 file)
│   │   ├── green/                      # green_YYYY_MM.parquet (39 file)
│   │   └── external/
│   │       ├── weather.csv
│   │       └── holidays.json
│   │
│   ├── clean/                          # Output Step 2 — data bersih (di-gitignore)
│   │   ├── yellow_clean.parquet
│   │   ├── green_clean.parquet
│   │   ├── weather_clean.parquet
│   │   └── holidays_clean.parquet
│   │
│   └── final/                          # Output Step 3 — database warehouse (di-gitignore)
│       └── warehouse.duckdb
│
├── docs/                               # Dokumentasi proyek
│   ├── DECISIONS.md                    # Catatan keputusan teknis (threshold, pilihan library, dll.)
│   └── schema_diagram.png              # Diagram star schema (buat manual / draw.io)
│
├── .gitignore
├── prefect.yaml                        # Konfigurasi deployment Prefect
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

## Menjalankan Pipeline Cleaning

Jalankan cleaning TLC dan external data:
```bash
python pipeline/cleaning/flow_cleaning.py
```

Output utama ada di folder `data/clean/`.

## Menjalankan Pipeline dari Awal

Untuk menjalankan ingestion lalu cleaning secara berurutan:
```bash
python pipeline/pipeline.py
```

Urutan proses: download/fetch data mentah -> cleaning data TLC dan external.

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
