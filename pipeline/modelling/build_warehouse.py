"""
pipeline/modelling/build_warehouse.py
Membangun star schema warehouse ke dalam DuckDB dari data clean.
Output: data/final/warehouse.duckdb

Star Schema:
  fact_trips        — tabel fakta utama
  dim_location      — zona NYC (download dari TLC)
  dim_time          — kalender + flag weekend & holiday
  dim_weather       — cuaca harian NYC
  dim_taxi_type     — metadata tipe taksi
"""

import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
FINAL_DIR = ROOT / "data" / "final"
FINAL_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = FINAL_DIR / "warehouse.duckdb"
ZONE_LOOKUP = RAW_DIR / "taxi_zone_lookup.csv"

YELLOW_CLEAN = CLEAN_DIR / "yellow_clean.parquet"
GREEN_CLEAN = CLEAN_DIR / "green_clean.parquet"
WEATHER_CLEAN = CLEAN_DIR / "weather_clean.parquet"
HOLIDAYS_CLEAN = CLEAN_DIR / "holidays_clean.parquet"

required = {
    "yellow_clean.parquet": YELLOW_CLEAN,
    "green_clean.parquet": GREEN_CLEAN,
    "weather_clean.parquet": WEATHER_CLEAN,
    "holidays_clean.parquet": HOLIDAYS_CLEAN,
}
missing = [name for name, path in required.items() if not path.exists()]
if missing:
    raise FileNotFoundError(
        f"File berikut tidak ditemukan di data/clean/:\n  " + "\n  ".join(missing)
    )

print("=" * 60)
print("  BUILD WAREHOUSE — NYC Taxi Star Schema")
print("=" * 60)

con = duckdb.connect(str(DB_PATH))

# dim_location
print("\n[1/5] dim_location ...")

ZONE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
try:
    zone_source = ZONE_LOOKUP if ZONE_LOOKUP.exists() else ZONE_URL
    zones = pd.read_csv(zone_source)
    zones.columns = ["location_id", "borough", "zone_name", "service_zone"]
    print(f"      Source OK: {zone_source} ({len(zones)} zona)")
except Exception as e:
    print(f"      [WARN] Gagal baca zona: {e}")
    print("      Membuat fallback dim_location minimal...")
    # Fallback: hanya location_id 1-263 tanpa nama
    zones = pd.DataFrame(
        {
            "location_id": range(1, 264),
            "borough": ["Unknown"] * 263,
            "zone_name": [f"Zone {i}" for i in range(1, 264)],
            "service_zone": ["Unknown"] * 263,
        }
    )

con.execute("CREATE OR REPLACE TABLE dim_location AS SELECT * FROM zones")
n = con.execute("SELECT COUNT(*) FROM dim_location").fetchone()[0]
print(f"      [OK] dim_location: {n} baris")

# dim_weather
print("\n[2/5] dim_weather ...")

con.execute(f"""
    CREATE OR REPLACE TABLE dim_weather AS
    SELECT
        CAST(date AS DATE)          AS date,
        temp_mean_c,
        temp_max_c                  AS temp_max,
        temp_min_c                  AS temp_min,
        precipitation_mm            AS precipitation,
        CAST(weathercode AS INTEGER) AS weathercode,
        CAST(is_rainy    AS BOOLEAN) AS is_rainy,
        CAST(is_snowy    AS BOOLEAN) AS is_snowy,
        -- weather_category: derived dari is_snowy, is_rainy, weathercode
        CASE
            WHEN is_snowy = 1                        THEN 'Snowy'
            WHEN is_rainy = 1                        THEN 'Rainy'
            WHEN weathercode IN (1, 2, 3, 45, 48)   THEN 'Cloudy'
            ELSE                                          'Clear'
        END                         AS weather_category
    FROM read_parquet('{WEATHER_CLEAN}')
""")
n = con.execute("SELECT COUNT(*) FROM dim_weather").fetchone()[0]
print(f"      [OK] dim_weather: {n} baris")

# dim_time
print("\n[3/5] dim_time ...")

# Kumpulkan semua trip_date dari kedua tabel
con.execute(f"""
    CREATE OR REPLACE TABLE dim_time AS
    SELECT DISTINCT
        trip_date                                        AS date,
        YEAR(trip_date)                                  AS year,
        MONTH(trip_date)                                 AS month,
        DAY(trip_date)                                   AS day,
        DAYOFWEEK(trip_date)                             AS day_of_week,
        DAYNAME(trip_date)                               AS day_name,
        CASE WHEN DAYOFWEEK(trip_date) IN (0, 6)
             THEN TRUE ELSE FALSE END                    AS is_weekend,
        FALSE                                            AS is_holiday,
        CAST(NULL AS INTEGER)                            AS hour      -- per-date dim; hour ada di fact
    FROM (
        SELECT trip_date FROM read_parquet('{YELLOW_CLEAN}')
        UNION
        SELECT trip_date FROM read_parquet('{GREEN_CLEAN}')
    ) dates
    ORDER BY date
""")

# tandai hari libur dari holidays_clean
holidays_df = pd.read_parquet(HOLIDAYS_CLEAN)[["date"]].copy()
holidays_df["date"] = pd.to_datetime(holidays_df["date"]).dt.date

holiday_dates = holidays_df["date"].astype(str).tolist()
if holiday_dates:
    placeholders = ", ".join(f"DATE '{d}'" for d in holiday_dates)
    con.execute(f"""
        UPDATE dim_time
        SET    is_holiday = TRUE
        WHERE  date IN ({placeholders})
    """)
    updated = con.execute(
        f"SELECT COUNT(*) FROM dim_time WHERE is_holiday = TRUE"
    ).fetchone()[0]
    print(f"      Hari libur ditandai: {updated} hari")

n = con.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0]
print(f"      [OK] dim_time: {n} baris (tanggal unik)")

# dim_taxi_type
print("\n[4/5] dim_taxi_type ...")

con.execute("""
    CREATE OR REPLACE TABLE dim_taxi_type AS
    SELECT * FROM (VALUES
        ('yellow', 'Yellow Cab',  'Manhattan & all boroughs'),
        ('green',  'Green Cab',   'Outer boroughs & upper Manhattan')
    ) t(taxi_type, description, coverage_area)
""")
print("      [OK] dim_taxi_type: 2 baris")

# fact_trips
print("\n[5/5] fact_trips ...")

con.execute(f"""
    CREATE OR REPLACE TABLE fact_trips AS
    SELECT
        ROW_NUMBER() OVER ()            AS trip_id,
        trip_date,
        CAST(pickup_hour AS INTEGER)    AS pickup_hour,
        CAST(day_of_week AS INTEGER)    AS day_of_week,
        PULocationID,
        DOLocationID,
        taxi_type,
        fare_amount,
        tip_amount,
        total_amount,
        trip_distance,
        CAST(duration_minutes AS FLOAT) AS duration_minutes,
        CAST(payment_type AS VARCHAR)   AS payment_type,
        passenger_count
    FROM (
        SELECT * FROM read_parquet('{YELLOW_CLEAN}')
        UNION ALL
        SELECT * FROM read_parquet('{GREEN_CLEAN}')
    ) combined
""")

n = con.execute("SELECT COUNT(*) FROM fact_trips").fetchone()[0]
print(f"      [OK] fact_trips: {n:,} trip total")

print("\n" + "=" * 60)
print("  VALIDASI JOIN")
print("=" * 60)

# dim_location
join_loc = con.execute("""
    SELECT COUNT(*) FROM fact_trips f
    JOIN dim_location l ON f.PULocationID = l.location_id
""").fetchone()[0]
print(f"  fact <-> dim_location  : {join_loc:,} baris (PULocationID match)")

# dim_time
join_time = con.execute("""
    SELECT COUNT(*) FROM fact_trips f
    JOIN dim_time t ON f.trip_date = t.date
""").fetchone()[0]
print(f"  fact <-> dim_time      : {join_time:,} baris")

# dim_weather
join_weather = con.execute("""
    SELECT COUNT(*) FROM fact_trips f
    JOIN dim_weather w ON f.trip_date = w.date
""").fetchone()[0]
print(f"  fact <-> dim_weather   : {join_weather:,} baris")

# dim_taxi_type
join_taxi = con.execute("""
    SELECT COUNT(*) FROM fact_trips f
    JOIN dim_taxi_type tt ON f.taxi_type = tt.taxi_type
""").fetchone()[0]
print(f"  fact <-> dim_taxi_type : {join_taxi:,} baris")

# summary
print("\n" + "=" * 60)
print("  RINGKASAN TABEL")
print("=" * 60)

tables = ["fact_trips", "dim_location", "dim_time", "dim_weather", "dim_taxi_type"]
for tbl in tables:
    cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    cols = [r[0] for r in con.execute(f"DESCRIBE {tbl}").fetchall()]
    print(f"\n  {tbl}")
    print(f"    Baris  : {cnt:,}")
    print(f"    Kolom  : {cols}")

con.close()

print(f"\n{'=' * 60}")
print(f"  [DONE] Warehouse tersimpan di: {DB_PATH}")
print(f"{'=' * 60}\n")
