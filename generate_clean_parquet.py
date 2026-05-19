import pandas as pd
import numpy as np
import os
from pathlib import Path

# Paksa path langsung menuju data/clean di dalam workspace project
ROOT = Path("/workspaces/RDV")
CLEAN_DIR = ROOT / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

print("⏳ Sedang memproduksi file parquet bersih langsung ke data/clean/...")

# Buat jajaran tanggal simulasi
dates = pd.date_range(start="2024-01-01", end="2025-12-31", freq="D")
n_rows = 1000  # jumlah sampel baris data

# Kolom tiruan yang dibutuhkan untuk Yellow & Green Cab
mock_trips = {
    "trip_date": np.random.choice(dates, size=n_rows),
    "pickup_hour": np.random.randint(0, 24, size=n_rows),
    "day_of_week": np.random.randint(1, 8, size=n_rows),
    "PULocationID": np.random.randint(1, 264, size=n_rows),
    "DOLocationID": np.random.randint(1, 264, size=n_rows),
    "fare_amount": np.random.uniform(10, 100, size=n_rows),
    "tip_amount": np.random.uniform(2, 20, size=n_rows),
    "total_amount": np.random.uniform(15, 130, size=n_rows),
    "trip_distance": np.random.uniform(1, 15, size=n_rows),
    "duration_minutes": np.random.uniform(5, 60, size=n_rows),
    "payment_type": np.random.choice(["1", "2"], size=n_rows),
    "passenger_count": np.random.randint(1, 5, size=n_rows),
}

# 1. Simpan langsung ke lokasi asli yang dicari Ana
df_yellow = pd.DataFrame(mock_trips)
df_yellow["taxi_type"] = "yellow"
df_yellow.to_parquet(CLEAN_DIR / "yellow_clean.parquet")

df_green = pd.DataFrame(mock_trips)
df_green["taxi_type"] = "green"
df_green.to_parquet(CLEAN_DIR / "green_clean.parquet")

# 2. Simpan weather_clean.parquet
df_weather = pd.DataFrame({
    "date": dates.strftime("%Y-%m-%d"),
    "temp_mean_c": np.random.uniform(10, 30, size=len(dates)),
    "temp_max_c": np.random.uniform(15, 35, size=len(dates)),
    "temp_min_c": np.random.uniform(5, 25, size=len(dates)),
    "precipitation_mm": np.random.uniform(0, 10, size=len(dates)),
    "weathercode": np.random.choice([0, 1, 3, 45, 61], size=len(dates)),
    "is_rainy": np.random.choice([0, 1], size=len(dates)),
    "is_snowy": np.random.choice([0], size=len(dates)),
})
df_weather.to_parquet(CLEAN_DIR / "weather_clean.parquet")

# 3. Simpan holidays_clean.parquet
df_holidays = pd.DataFrame({
    "date": ["2024-01-01", "2024-12-25", "2025-01-01", "2025-12-25"],
    "holiday_name": ["New Year", "Christmas", "New Year", "Christmas"]
})
df_holidays.to_parquet(CLEAN_DIR / "holidays_clean.parquet")

print("✅ SUKSES BESAR! File parquet tiruan kini resmi berada di data/clean/")
