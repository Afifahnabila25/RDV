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
│   └── pages/
│       ├── overview.py                 # Halaman ringkasan & KPI
│       ├── prediction.py               # Halaman prediksi demand
│       ├── revenue_region.py           # Halaman peta & analisis zona
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
│   │   ├── clean_external.py           # Cleaning data cuaca & hari libur
│   │   └── flow_cleaning.py            # Orkestrasi cleaning data
│   │
│   ├── modelling/                      # Step 3 — Storage & Data Modelling
│   │   └── build_warehouse.py          # Bangun star schema di DuckDB (fact + dim tables)
│   │
│   └── pipeline.py                     # Orchestrator utama (ingestion → cleaning → modelling)
│
├── analysis/                           # Step 4 — Analytical Queries
│   └── run_analysis.py                 # Buat semua analytical views di warehouse.duckdb
│
├── data/
│   ├── raw/                            # Output Step 1 — data mentah (di-gitignore)
│   │   ├── yellow/                     # yellow_tripdata_YYYY-MM.parquet
│   │   ├── green/                      # green_tripdata_YYYY-MM.parquet
│   │   └── external/
│   │       ├── weather.parquet
│   │       └── holidays.parquet
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
│   ├── DECISIONS.md                    # Catatan keputusan teknis
│   └── schema_diagram.png              # Diagram star schema
│
├── .streamlit/
│   └── config.toml                     # Konfigurasi tampilan Streamlit
│
├── prefect/                            # Konfigurasi & deployment Prefect
│
├── .gitignore
├── app.py                              # Entry point utama Streamlit
├── prefect.yaml                        # Konfigurasi deployment Prefect
├── requirements.txt
├── setup_struktur.sh                   # Script setup struktur folder proyek
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

## 🔄 Menjalankan Pipeline

Pipeline menggunakan **Prefect** untuk orkestrasi. Jalankan satu perintah untuk menjalankan semua proses: download → cleaning → build warehouse.

### Langkah 1 — Start Prefect Server (Terminal 1)

```bash
prefect server start
```

Biarkan terminal ini tetap berjalan. Buka **http://127.0.0.1:4200** untuk monitoring real-time.

### Langkah 2 — Jalankan Pipeline (Terminal 2)

```bash
python pipeline/pipeline.py
```

Urutan proses yang dijalankan otomatis:
1. Download data Yellow & Green Taxi dari NYC TLC
2. Fetch data cuaca (Open-Meteo) & hari libur (Nager.Date)
3. Cleaning & validasi data TLC dan external
4. Build warehouse DuckDB dengan star schema

### Langkah 3 — Buat Analytical Views

```bash
python analysis/run_analysis.py
```

Membuat semua view agregasi yang dibutuhkan dashboard (wajib dijalankan setelah pipeline selesai).

### Langkah 4 — Jalankan Dashboard

```bash
streamlit run app.py
```

Buka browser ke **http://localhost:8501**

---

## 🗄️ Isi Warehouse DuckDB

File `data/final/warehouse.duckdb` dibangun dengan model **star schema**.

| Tabel | Tipe | Kolom Utama | Deskripsi |
|---|---|---|---|
| `fact_trips` | Fact | `trip_id`, `trip_date`, `pickup_hour`, `PULocationID`, `DOLocationID`, `taxi_type`, `fare_amount`, `tip_amount`, `total_amount`, `trip_distance`, `duration_minutes`, `payment_type`, `passenger_count` | Seluruh trip Yellow & Green Taxi yang sudah dibersihkan (±43 juta baris) |
| `dim_location` | Dimension | `location_id`, `borough`, `zone_name`, `service_zone` | Lookup zona NYC TLC — menghubungkan location ID ke borough dan nama zona |
| `dim_time` | Dimension | `date`, `year`, `month`, `day`, `day_of_week`, `day_name`, `is_weekend`, `is_holiday`, `hour` | Dimensi kalender harian, termasuk flag weekend dan hari libur nasional AS |
| `dim_weather` | Dimension | `date`, `temp_mean_c`, `precipitation`, `weathercode`, `is_rainy`, `is_snowy`, `weather_category` | Data cuaca harian NYC dari Open-Meteo |
| `dim_taxi_type` | Dimension | `taxi_type`, `description`, `coverage_area` | Metadata jenis taxi (Yellow Cab & Green Cab) |

---

## 📊 Fitur Dashboard

| Halaman | Isi |
|---|---|
| Overview | Total trip, total revenue, tip, market share Yellow vs Green, tren bulanan |
| Prediction | Prediksi demand berdasarkan pola historis |
| Revenue & Region | Analisis pendapatan per wilayah & zona, peta choropleth |
| Time & External | Pola waktu, pengaruh cuaca & hari libur terhadap demand |

Gunakan **sidebar** untuk filter jenis taksi (Yellow/Green) dan tahun.

---

## 📦 Dataset

| Sumber | Periode | Keterangan |
|---|---|---|
| NYC TLC Yellow Taxi | Jan 2025 – Des 2025 | Download via `download_tlc.py` |
| NYC TLC Green Taxi | Jan 2025 – Des 2025 | Download via `download_tlc.py` |
| Open-Meteo Historical API | Jan 2025 – Des 2025 | Cuaca harian NYC |
| Nager.Date API | 2025 | Hari libur nasional AS |

> ⚠️ Folder `data/` tidak di-push ke GitHub karena ukurannya besar.  
> Download ulang dengan menjalankan pipeline ingestion di atas.

---

## 🛠️ Tech Stack

`Python` `DuckDB` `Prefect` `Streamlit` `Pandas` `Plotly` `Folium` `Requests`

---