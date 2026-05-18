"""
pipeline/cleaning/clean_tlc.py
Cleaning script untuk data TLC Yellow & Green Taxi (2025).
Output: data/clean/{taxi_type}_clean.parquet
"""

import duckdb
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()

FARE_MIN = 3.00
FARE_MAX = 500.00
DURATION_MIN = 1
DURATION_MAX = 480
LOCATION_MIN = 1
LOCATION_MAX = 263
PASSENGER_MAX = 6
DISTANCE_MAX_MILES = 100.0
TRIP_START_DATE = "2025-01-01"
TRIP_END_DATE = "2026-01-01"


def log_anomaly(label: str, before: int, after: int):
    removed = before - after
    pct = removed / before * 100 if before else 0
    print(f"    [{label}] dihapus: {removed:,} baris ({pct:.2f}%)")


def _relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def clean_taxi(taxi_type: str) -> Optional[Path]:
    prefix = "tpep" if taxi_type == "yellow" else "lpep"
    raw_dir = DATA_DIR / "raw" / taxi_type
    files = sorted(str(p) for p in raw_dir.glob("*.parquet"))

    if not files:
        print(f"[{taxi_type.upper()}] Tidak ada file ditemukan di {_relpath(raw_dir)}/")
        return None

    print(f"\n{'=' * 60}")
    print(f"  Cleaning: {taxi_type.upper()} ({len(files)} file)")
    print(f"{'=' * 60}")

    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW raw AS
        SELECT
            {prefix}_pickup_datetime AS pickup_datetime,
            {prefix}_dropoff_datetime AS dropoff_datetime,
            PULocationID,
            DOLocationID,
            trip_distance,
            fare_amount,
            tip_amount,
            total_amount,
            payment_type,
            CAST(passenger_count AS INTEGER) AS passenger_count,
            DATE({prefix}_pickup_datetime) AS trip_date,
            HOUR({prefix}_pickup_datetime) AS pickup_hour,
            DAYOFWEEK({prefix}_pickup_datetime) AS day_of_week,
            DATEDIFF(
                'minute',
                {prefix}_pickup_datetime,
                {prefix}_dropoff_datetime
            ) AS duration_minutes,
            '{taxi_type}' AS taxi_type
        FROM read_parquet({files!r})
    """)

    def count_raw(where: str = "TRUE") -> int:
        return con.execute(f"SELECT count(*) FROM raw WHERE {where}").fetchone()[0]

    total_raw = count_raw()
    print(f"\n  Total baris mentah : {total_raw:,}")
    print(f"  Null passenger_count: {count_raw('passenger_count IS NULL'):,}")
    print()

    filters = []
    n = total_raw

    filters.append("dropoff_datetime > pickup_datetime")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly("dropoff <= pickup", n, n_after)
    n = n_after

    filters.append(f"pickup_datetime >= TIMESTAMP '{TRIP_START_DATE}'")
    filters.append(f"pickup_datetime < TIMESTAMP '{TRIP_END_DATE}'")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly(f"pickup_datetime di luar [{TRIP_START_DATE}, {TRIP_END_DATE})", n, n_after)
    n = n_after

    filters.append(f"fare_amount >= {FARE_MIN}")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly(f"fare_amount < {FARE_MIN}", n, n_after)
    n = n_after

    filters.append(f"fare_amount <= {FARE_MAX}")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly(f"fare_amount > {FARE_MAX}", n, n_after)
    n = n_after

    filters.append("total_amount > 0")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly("total_amount <= 0", n, n_after)
    n = n_after

    where_now = " AND ".join(filters)
    neg_tip = count_raw(f"{where_now} AND tip_amount < 0")
    print(f"    [tip_amount < 0] dikoreksi ke 0: {neg_tip:,} baris")

    filters.append("trip_distance > 0")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly("trip_distance <= 0", n, n_after)
    n = n_after

    filters.append(f"trip_distance <= {DISTANCE_MAX_MILES}")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly(f"trip_distance > {DISTANCE_MAX_MILES} miles", n, n_after)
    n = n_after

    filters.append(f"PULocationID BETWEEN {LOCATION_MIN} AND {LOCATION_MAX}")
    filters.append(f"DOLocationID BETWEEN {LOCATION_MIN} AND {LOCATION_MAX}")
    n_after = count_raw(" AND ".join(filters))
    log_anomaly("LocationID di luar [1-263]", n, n_after)
    n = n_after

    base_where = " AND ".join(filters)
    con.execute(f"CREATE OR REPLACE TEMP VIEW base AS SELECT * FROM raw WHERE {base_where}")

    median_val = con.execute("SELECT median(passenger_count) FROM base").fetchone()[0]
    median_pax = int(median_val) if median_val is not None else 1

    null_pax = con.execute("SELECT count(*) FROM base WHERE passenger_count IS NULL").fetchone()[0]
    print(f"    [passenger_count null] diimputasi dengan median ({median_pax}): {null_pax:,} baris")

    pax_where = f"COALESCE(passenger_count, {median_pax}) BETWEEN 1 AND {PASSENGER_MAX}"
    n_after = con.execute(f"SELECT count(*) FROM base WHERE {pax_where}").fetchone()[0]
    log_anomaly("passenger_count <= 0 atau > 6", n, n_after)
    n = n_after

    duration_where = f"{pax_where} AND duration_minutes BETWEEN {DURATION_MIN} AND {DURATION_MAX}"
    n_after = con.execute(f"SELECT count(*) FROM base WHERE {duration_where}").fetchone()[0]
    log_anomaly(f"duration_minutes di luar [{DURATION_MIN}-{DURATION_MAX}]", n, n_after)
    n = n_after

    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW cleaned AS
        SELECT
            pickup_datetime,
            dropoff_datetime,
            PULocationID,
            DOLocationID,
            trip_distance,
            fare_amount,
            GREATEST(tip_amount, 0) AS tip_amount,
            total_amount,
            CAST(payment_type AS INTEGER) AS payment_type,
            CAST(COALESCE(passenger_count, {median_pax}) AS INTEGER) AS passenger_count,
            trip_date,
            pickup_hour,
            day_of_week,
            duration_minutes,
            '{taxi_type}' AS taxi_type
        FROM base
        WHERE {duration_where}
    """)

    out = CLEAN_DIR / f"{taxi_type}_clean.parquet"
    con.execute(f"COPY (SELECT * FROM cleaned) TO {str(out)!r} (FORMAT PARQUET)")

    removed_total = total_raw - n
    pct_kept = n / total_raw * 100 if total_raw else 0

    print(f"\n  [OK] Bersih : {n:,} baris ({pct_kept:.1f}% dari {total_raw:,})")
    print(f"  [DROP] Dihapus: {removed_total:,} baris")
    print(f"  [OUT] Output : {_relpath(out)}")

    if n == 0:
        print("  [WARN] Output kosong; validasi dilewati")
        return out

    min_fare = con.execute("SELECT min(fare_amount) FROM cleaned").fetchone()[0]
    max_fare = con.execute("SELECT max(fare_amount) FROM cleaned").fetchone()[0]
    min_total = con.execute("SELECT min(total_amount) FROM cleaned").fetchone()[0]
    min_tip = con.execute("SELECT min(tip_amount) FROM cleaned").fetchone()[0]
    min_dist = con.execute("SELECT min(trip_distance) FROM cleaned").fetchone()[0]

    bad_period = con.execute(f"""
        SELECT count(*)
        FROM cleaned
        WHERE pickup_datetime < TIMESTAMP '{TRIP_START_DATE}'
           OR pickup_datetime >= TIMESTAMP '{TRIP_END_DATE}'
    """).fetchone()[0]

    bad_duration = con.execute(
        f"SELECT count(*) FROM cleaned WHERE duration_minutes NOT BETWEEN {DURATION_MIN} AND {DURATION_MAX}"
    ).fetchone()[0]

    bad_pax = con.execute(
        f"SELECT count(*) FROM cleaned WHERE passenger_count NOT BETWEEN 1 AND {PASSENGER_MAX}"
    ).fetchone()[0]

    assert min_fare >= FARE_MIN, "Ada fare_amount di bawah minimum!"
    assert max_fare <= FARE_MAX, "Ada fare_amount di atas batas maksimum!"
    assert min_total > 0, "Ada total_amount <= 0!"
    assert min_tip >= 0, "Ada tip_amount negatif!"
    assert min_dist > 0, "Ada trip_distance <= 0!"
    assert bad_period == 0, "Ada pickup_datetime di luar periode 2025!"
    assert bad_duration == 0, "Ada duration di luar batas!"
    assert bad_pax == 0, "Ada passenger_count tidak valid!"

    print("  [OK] Semua validasi lolos")

    return out


def print_summary(yellow_path: Optional[Path], green_path: Optional[Path]):
    print(f"\n{'=' * 60}")
    print("  RINGKASAN CLEANING")
    print(f"{'=' * 60}")

    for label, path in [("Yellow", yellow_path), ("Green", green_path)]:
        if path is None or not path.exists():
            print(f"  {label}: tidak ada data")
            continue

        con.execute(f"CREATE OR REPLACE TEMP VIEW summary_data AS SELECT * FROM read_parquet({str(path)!r})")

        row_count = con.execute("SELECT count(*) FROM summary_data").fetchone()[0]
        if row_count == 0:
            print(f"  {label}: tidak ada data")
            continue

        period = con.execute("SELECT min(trip_date), max(trip_date) FROM summary_data").fetchone()
        cols = [row[0] for row in con.execute("DESCRIBE summary_data").fetchall()]

        fare_stats = con.execute(
            "SELECT min(fare_amount), median(fare_amount), max(fare_amount) FROM summary_data"
        ).fetchone()

        dur_stats = con.execute(
            "SELECT min(duration_minutes), median(duration_minutes), max(duration_minutes) FROM summary_data"
        ).fetchone()

        print(f"\n  {label}:")
        print(f"    Baris bersih   : {row_count:,}")
        print(f"    Periode        : {period[0]} -> {period[1]}")
        print(f"    Kolom          : {cols}")
        print(
            f"    fare_amount    : min={fare_stats[0]:.2f}, "
            f"median={fare_stats[1]:.2f}, max={fare_stats[2]:.2f}"
        )
        print(
            f"    duration_min   : min={dur_stats[0]}, "
            f"median={dur_stats[1]:.0f}, max={dur_stats[2]}"
        )


if __name__ == "__main__":
    yellow_path = clean_taxi("yellow")
    green_path = clean_taxi("green")
    print_summary(yellow_path, green_path)

    print(f"\n{'=' * 60}")
    print("  Cleaning selesai!")
    print(f"{'=' * 60}\n")