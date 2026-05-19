"""
analysis/run_analysis.py
Membuat semua analytical views di dalam warehouse.duckdb.

Views yang dibuat:
  1. agg_revenue_daily        — revenue harian (total, per taxi type)
  2. agg_revenue_by_zone      — revenue & trip count per zona pickup
  3. agg_heatmap_hour_day     — heatmap jumlah trip per jam x hari
  4. agg_weather_vs_trips     — korelasi cuaca vs trip (JOIN fact_trips + dim_weather)
  5. agg_holiday_comparison   — perbandingan libur vs weekend vs weekday

Cara jalankan:
    python analysis/run_analysis.py

Pastikan warehouse.duckdb sudah tersedia di data/final/ (jalankan build_warehouse.py dulu).
"""
import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"warehouse.duckdb tidak ditemukan di: {DB_PATH}\n"
        "Jalankan dulu: python pipeline/modelling/build_warehouse.py"
    )

print("=" * 60)
print("  RUN ANALYSIS — NYC Taxi Analytical Views")
print("=" * 60)
print(f"\n  Database : {DB_PATH}")

con = duckdb.connect(str(DB_PATH))

# VIEW 1 — agg_revenue_daily
# Revenue harian: total trip, total revenue, breakdown per taxi type
print("\n[1/5] Membuat view: agg_revenue_daily ...")

con.execute("""
    CREATE OR REPLACE VIEW agg_revenue_daily AS
    SELECT
        f.trip_date,
        t.year,
        t.month,
        t.day_name,
        t.is_weekend,
        t.is_holiday,
        COUNT(*)                                    AS total_trips,
        ROUND(SUM(f.total_amount), 2)               AS total_revenue,
        ROUND(AVG(f.total_amount), 2)               AS avg_revenue_per_trip,
        ROUND(SUM(f.fare_amount),  2)               AS total_fare,
        ROUND(SUM(f.tip_amount),   2)               AS total_tip,
        ROUND(AVG(f.tip_amount),   2)               AS avg_tip,
        -- Yellow breakdown
        COUNT(*) FILTER (WHERE f.taxi_type = 'yellow')                      AS yellow_trips,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'yellow'), 2) AS yellow_revenue,
        -- Green breakdown
        COUNT(*) FILTER (WHERE f.taxi_type = 'green')                       AS green_trips,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'green'),  2) AS green_revenue
    FROM fact_trips  f
    JOIN dim_time    t ON f.trip_date = t.date
    GROUP BY
        f.trip_date, t.year, t.month, t.day_name, t.is_weekend, t.is_holiday
    ORDER BY f.trip_date
""")

n = con.execute("SELECT COUNT(*) FROM agg_revenue_daily").fetchone()[0]
print(f"      [OK] agg_revenue_daily: {n:,} baris (hari unik)")


# VIEW 2 — agg_revenue_by_zone
# Revenue & trip count per zona pickup (join dim_location)
print("\n[2/5] Membuat view: agg_revenue_by_zone ...")

con.execute("""
    CREATE OR REPLACE VIEW agg_revenue_by_zone AS
    SELECT
        f.PULocationID                                  AS location_id,
        l.borough,
        l.zone_name,
        l.service_zone,
        COUNT(*)                                        AS total_trips,
        ROUND(SUM(f.total_amount),   2)                 AS total_revenue,
        ROUND(AVG(f.total_amount),   2)                 AS avg_revenue_per_trip,
        ROUND(SUM(f.fare_amount),    2)                 AS total_fare,
        ROUND(SUM(f.tip_amount),     2)                 AS total_tip,
        ROUND(AVG(f.trip_distance),  2)                 AS avg_distance_miles,
        ROUND(AVG(f.duration_minutes), 2)               AS avg_duration_min,
        -- Breakdown per taxi type
        COUNT(*) FILTER (WHERE f.taxi_type = 'yellow')                      AS yellow_trips,
        COUNT(*) FILTER (WHERE f.taxi_type = 'green')                       AS green_trips,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'yellow'), 2) AS yellow_revenue,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'green'),  2) AS green_revenue
    FROM fact_trips   f
    JOIN dim_location l ON f.PULocationID = l.location_id
    GROUP BY
        f.PULocationID, l.borough, l.zone_name, l.service_zone
    ORDER BY total_revenue DESC
""")

n = con.execute("SELECT COUNT(*) FROM agg_revenue_by_zone").fetchone()[0]
print(f"      [OK] agg_revenue_by_zone: {n:,} baris (zona unik)")


# VIEW 3 — agg_heatmap_hour_day
# Heatmap jumlah trip & revenue per jam x hari dalam seminggu
print("\n[3/5] Membuat view: agg_heatmap_hour_day ...")

con.execute("""
    CREATE OR REPLACE VIEW agg_heatmap_hour_day AS
    SELECT
        f.pickup_hour,
        f.day_of_week,
        t.day_name,
        t.is_weekend,
        COUNT(*)                            AS total_trips,
        ROUND(SUM(f.total_amount),  2)      AS total_revenue,
        ROUND(AVG(f.total_amount),  2)      AS avg_revenue_per_trip,
        ROUND(AVG(f.trip_distance), 2)      AS avg_distance_miles,
        ROUND(AVG(f.duration_minutes), 2)   AS avg_duration_min,
        -- Breakdown per taxi type
        COUNT(*) FILTER (WHERE f.taxi_type = 'yellow') AS yellow_trips,
        COUNT(*) FILTER (WHERE f.taxi_type = 'green')  AS green_trips
    FROM fact_trips f
    JOIN dim_time   t ON f.trip_date = t.date
    GROUP BY
        f.pickup_hour, f.day_of_week, t.day_name, t.is_weekend
    ORDER BY f.day_of_week, f.pickup_hour
""")

n = con.execute("SELECT COUNT(*) FROM agg_heatmap_hour_day").fetchone()[0]
print(f"      [OK] agg_heatmap_hour_day: {n:,} baris (kombinasi jam x hari)")


# VIEW 4 — agg_weather_vs_trips
# Korelasi kondisi cuaca vs pola perjalanan taxi
# JOIN fact_trips + dim_weather (on trip_date = weather.date)
print("\n[4/5] Membuat view: agg_weather_vs_trips ...")

con.execute("""
    CREATE OR REPLACE VIEW agg_weather_vs_trips AS
    SELECT
        w.date,
        w.weather_category,
        w.is_rainy,
        w.is_snowy,
        w.temp_mean_c,
        w.temp_max,
        w.temp_min,
        w.precipitation,
        w.weathercode,
        COUNT(f.trip_id)                        AS total_trips,
        ROUND(SUM(f.total_amount),   2)         AS total_revenue,
        ROUND(AVG(f.total_amount),   2)         AS avg_revenue_per_trip,
        ROUND(AVG(f.trip_distance),  2)         AS avg_distance_miles,
        ROUND(AVG(f.duration_minutes), 2)       AS avg_duration_min,
        ROUND(AVG(f.passenger_count),  2)       AS avg_passengers,
        ROUND(AVG(f.tip_amount),       2)       AS avg_tip,
        -- Breakdown per taxi type
        COUNT(f.trip_id) FILTER (WHERE f.taxi_type = 'yellow') AS yellow_trips,
        COUNT(f.trip_id) FILTER (WHERE f.taxi_type = 'green')  AS green_trips
    FROM dim_weather w
    LEFT JOIN fact_trips f ON f.trip_date = w.date
    GROUP BY
        w.date, w.weather_category, w.is_rainy, w.is_snowy,
        w.temp_mean_c, w.temp_max, w.temp_min,
        w.precipitation, w.weathercode
    ORDER BY w.date
""")

n = con.execute("SELECT COUNT(*) FROM agg_weather_vs_trips").fetchone()[0]
print(f"      [OK] agg_weather_vs_trips: {n:,} baris (hari dengan data cuaca)")


# VIEW 5 — agg_holiday_comparison
# Perbandingan metrik trip: Hari Libur vs Weekend vs Weekday
print("\n[5/5] Membuat view: agg_holiday_comparison ...")

con.execute("""
    CREATE OR REPLACE VIEW agg_holiday_comparison AS
    SELECT
        CASE
            WHEN t.is_holiday = TRUE                            THEN 'Holiday'
            WHEN t.is_weekend = TRUE AND t.is_holiday = FALSE   THEN 'Weekend'
            ELSE                                                     'Weekday'
        END                                             AS day_type,
        COUNT(DISTINCT f.trip_date)                     AS total_days,
        COUNT(f.trip_id)                                AS total_trips,
        ROUND(COUNT(f.trip_id) * 1.0
              / COUNT(DISTINCT f.trip_date), 0)         AS avg_trips_per_day,
        ROUND(SUM(f.total_amount),   2)                 AS total_revenue,
        ROUND(AVG(f.total_amount),   2)                 AS avg_revenue_per_trip,
        ROUND(SUM(f.total_amount)
              / COUNT(DISTINCT f.trip_date), 2)         AS avg_daily_revenue,
        ROUND(AVG(f.fare_amount),    2)                 AS avg_fare,
        ROUND(AVG(f.tip_amount),     2)                 AS avg_tip,
        ROUND(AVG(f.trip_distance),  2)                 AS avg_distance_miles,
        ROUND(AVG(f.duration_minutes), 2)               AS avg_duration_min,
        ROUND(AVG(f.passenger_count),  2)               AS avg_passengers,
        -- Breakdown per taxi type
        COUNT(f.trip_id) FILTER (WHERE f.taxi_type = 'yellow')       AS yellow_trips,
        COUNT(f.trip_id) FILTER (WHERE f.taxi_type = 'green')        AS green_trips,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'yellow'), 2) AS yellow_revenue,
        ROUND(SUM(f.total_amount) FILTER (WHERE f.taxi_type = 'green'),  2) AS green_revenue
    FROM fact_trips f
    JOIN dim_time   t ON f.trip_date = t.date
    GROUP BY day_type
    ORDER BY
        CASE day_type
            WHEN 'Holiday' THEN 1
            WHEN 'Weekend' THEN 2
            ELSE                3
        END
""")

n = con.execute("SELECT COUNT(*) FROM agg_holiday_comparison").fetchone()[0]
print(f"      [OK] agg_holiday_comparison: {n:,} baris (Holiday / Weekend / Weekday)")


# TEST — SELECT * LIMIT 10 dari semua view
print("\n" + "=" * 60)
print("  TEST: SELECT * LIMIT 10 dari semua view")
print("=" * 60)

views = [
    "agg_revenue_daily",
    "agg_revenue_by_zone",
    "agg_heatmap_hour_day",
    "agg_weather_vs_trips",
    "agg_holiday_comparison",
]

all_passed = True

for view in views:
    print(f"\n{'─' * 60}")
    print(f"{view}")
    print(f"{'─' * 60}")
    try:
        df = con.execute(f"SELECT * FROM {view} LIMIT 10").df()
        if df.empty:
            print("  [WARN] View kosong — mungkin data belum ada.")
            all_passed = False
        else:
            print(df.to_string(index=False))
            print(f"\n {len(df)} baris ditampilkan | {len(df.columns)} kolom: {list(df.columns)}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False


# RINGKASAN VIEWS
print("\n" + "=" * 60)
print("  RINGKASAN ANALYTICAL VIEWS")
print("=" * 60)

for view in views:
    try:
        cnt  = con.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        cols = [r[0] for r in con.execute(f"DESCRIBE {view}").fetchall()]
        print(f"\n  {view}")
        print(f"    Baris  : {cnt:,}")
        print(f"    Kolom  : {cols}")
    except Exception as e:
        print(f"  {view} — ERROR: {e}")

con.close()

print(f"\n{'=' * 60}")
if all_passed:
    print("  [DONE] Semua analytical views berhasil dibuat & diverifikasi")
else:
    print("  [WARN] Ada view yang kosong atau error — cek log di atas")
print(f"{'=' * 60}\n")
