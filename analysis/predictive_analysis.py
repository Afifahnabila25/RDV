"""
analysis/predictive_analysis.py
Script Machine Learning untuk NYC Taxi Analysis.
Menjawab kebutuhan prediksi:
1. Prediksi Total Revenue Harian  (+ statistik mean & std)
2. Prediksi Zona Paling Ramai (Demand)
3. Prediksi Harga (Total Amount) dipengaruhi Cuaca & Hari Libur/Weekday
"""

import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
except ImportError:
    print("ERROR: Library 'scikit-learn' belum terinstall.")
    print("Silakan jalankan: pip install scikit-learn")
    exit(1)

try:
    from xgboost import XGBRegressor

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print(
        "[INFO] XGBoost tidak tersedia, menggunakan GradientBoosting sebagai pengganti."
    )
    print("       Untuk install: pip install xgboost\n")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
if not DB_PATH.exists():
    DB_PATH = Path("data/final/warehouse.duckdb")
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database tidak ditemukan. Pastikan pipeline sudah dijalankan."
        )


def print_stats_block(label, series: pd.Series):
    """Cetak mean, std, min, max dari sebuah series."""
    print(f"      Mean (rata-rata)  : {label}{series.mean():>14,.2f}")
    print(f"      Std Dev           : {label}{series.std():>14,.2f}")
    print(f"      Min               : {label}{series.min():>14,.2f}")
    print(f"      Max               : {label}{series.max():>14,.2f}")


def add_cyclical(df, col, max_val):
    """Encode kolom siklikal (bulan, hari) sebagai sin/cos agar model lebih akurat."""
    df[f"{col}_sin"] = np.sin(2 * np.pi * df[col] / max_val)
    df[f"{col}_cos"] = np.cos(2 * np.pi * df[col] / max_val)
    return df


def main():
    print("=" * 62)
    print("  NYC TAXI — PREDICTIVE MODELLING")
    print("=" * 62)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    #  1. PREDIKSI TOTAL REVENUE PER HARI
    print("\n      Membangun Model Prediksi Revenue Harian...")

    df_daily = con.execute("""
        SELECT
            r.total_revenue,
            t.month,
            t.day_of_week,
            CAST(t.is_weekend AS INT)  AS is_weekend,
            CAST(t.is_holiday AS INT)  AS is_holiday,
            w.temp_mean_c,
            w.precipitation,
            CAST(w.is_rainy AS INT)    AS is_rainy,
            CAST(w.is_snowy AS INT)    AS is_snowy
        FROM agg_revenue_daily r
        JOIN dim_time t    ON r.trip_date = t.date
        LEFT JOIN dim_weather w ON r.trip_date = w.date
        WHERE w.temp_mean_c IS NOT NULL
    """).df()

    # Statistik deskriptif revenue
    print("\n      [STATISTIK REVENUE HARIAN]")
    print_stats_block("$", df_daily["total_revenue"])

    # Feature engineering─
    df_daily = add_cyclical(df_daily, "month", 12)
    df_daily = add_cyclical(df_daily, "day_of_week", 7)

    FEAT_DAILY = [
        "month_sin",
        "month_cos",
        "day_of_week_sin",
        "day_of_week_cos",
        "is_weekend",
        "is_holiday",
        "temp_mean_c",
        "precipitation",
        "is_rainy",
        "is_snowy",
    ]

    X = df_daily[FEAT_DAILY]
    y = df_daily["total_revenue"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Bandingkan 3 model
    models_daily = {
        "RandomForest": RandomForestRegressor(n_estimators=200, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
        ),
    }
    if XGBOOST_AVAILABLE:
        models_daily["XGBoost"] = XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
        )

    best_model_daily = None
    best_r2_daily = -999
    best_name_daily = ""

    print("\n      [PERBANDINGAN MODEL]")
    print(f"      {'Model':<22} {'R²':>7}  {'MAE':>14}")
    print(f"      {'-' * 47}")
    for name, mdl in models_daily.items():
        mdl.fit(X_train, y_train)
        pred = mdl.predict(X_test)
        r2 = r2_score(y_test, pred)
        mae = mean_absolute_error(y_test, pred)
        print(f"      {name:<22} {r2:>7.4f}  ${mae:>13,.2f}")
        if r2 > best_r2_daily:
            best_r2_daily = r2
            best_model_daily = mdl
            best_name_daily = name

    print(f"\n      → Model terbaik: {best_name_daily} (R² = {best_r2_daily:.4f})")

    # Feature importance (hanya untuk RF/GBM/XGB)
    feat_imp = pd.DataFrame(
        {
            "Fitur": FEAT_DAILY,
            "Pentingnya": best_model_daily.feature_importances_,
        }
    ).sort_values("Pentingnya", ascending=False)
    print("\n      Faktor paling mempengaruhi revenue harian:")
    for _, row in feat_imp.head(3).iterrows():
        print(f"        - {row['Fitur']}: {row['Pentingnya'] * 100:.1f}%")

    #  2. PREDIKSI ZONA PALING RAMAI
    print("\n      Memprediksi Zona Paling Ramai Berdasarkan Tren...")

    df_zone = con.execute("""
        SELECT
            l.zone_name,
            l.borough,
            COUNT(*)                AS total_trips,
            AVG(f.total_amount)     AS avg_revenue_per_trip,
            STDDEV(f.total_amount)  AS std_revenue_per_trip
        FROM fact_trips f
        JOIN dim_location l ON f.PULocationID = l.location_id
        GROUP BY l.zone_name, l.borough
        ORDER BY total_trips DESC
        LIMIT 5
    """).df()

    # Statistik total_amount dari seluruh dataset
    stats_fare = (
        con.execute("""
        SELECT
            AVG(total_amount)    AS mean_fare,
            STDDEV(total_amount) AS std_fare,
            MIN(total_amount)    AS min_fare,
            MAX(total_amount)    AS max_fare
        FROM fact_trips
        WHERE total_amount > 0
    """)
        .df()
        .iloc[0]
    )

    print("\n      [STATISTIK HARGA SELURUH PERJALANAN]")
    print(f"      Mean (rata-rata)  : ${stats_fare['mean_fare']:>14,.2f}")
    print(f"      Std Dev           : ${stats_fare['std_fare']:>14,.2f}")
    print(f"      Min               : ${stats_fare['min_fare']:>14,.2f}")
    print(f"      Max               : ${stats_fare['max_fare']:>14,.2f}")

    print("\n      Top 5 Zona Prediksi Demand Tertinggi:")
    for i, row in df_zone.iterrows():
        print(
            f"      {i + 1}. {row['zone_name']} ({row['borough']})"
            f"  → Avg: ${row['avg_revenue_per_trip']:.2f}"
            f"  ± Std: ${row['std_revenue_per_trip']:.2f}"
        )

    #  3. PREDIKSI HARGA vs CUACA & HARI LIBUR
    print("\n      Membangun Model Prediksi Harga (Cuaca & Hari Libur)...")

    df_fare = (
        con.execute("""
        SELECT
            f.total_amount,
            f.trip_distance,
            f.duration_minutes,
            w.temp_mean_c,
            CAST(w.is_rainy   AS INT) AS is_rainy,
            CAST(w.is_snowy   AS INT) AS is_snowy,
            CAST(t.is_holiday AS INT) AS is_holiday,
            CAST(t.is_weekend AS INT) AS is_weekend
        FROM fact_trips f
        JOIN dim_weather  w ON f.trip_date = w.date
        JOIN dim_time     t ON f.trip_date = t.date
        WHERE f.total_amount  > 0
          AND f.trip_distance > 0
          AND f.duration_minutes BETWEEN 1 AND 120
        USING SAMPLE 100000
    """)
        .df()
        .fillna(0)
    )

    print("\n      [STATISTIK HARGA SAMPLE 100K PERJALANAN]")
    print_stats_block("$", df_fare["total_amount"])

    FEAT_FARE = [
        "trip_distance",
        "duration_minutes",
        "temp_mean_c",
        "is_rainy",
        "is_snowy",
        "is_holiday",
        "is_weekend",
    ]
    X_f = df_fare[FEAT_FARE]
    y_f = df_fare["total_amount"]

    Xf_tr, Xf_te, yf_tr, yf_te = train_test_split(
        X_f, y_f, test_size=0.2, random_state=42
    )

    models_fare = {
        "RandomForest": RandomForestRegressor(
            n_estimators=50, max_depth=10, random_state=42
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
        ),
    }
    if XGBOOST_AVAILABLE:
        models_fare["XGBoost"] = XGBRegressor(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=5,
            subsample=0.8,
            random_state=42,
            verbosity=0,
        )

    best_model_fare = None
    best_r2_fare = -999
    best_name_fare = ""

    print("\n      [PERBANDINGAN MODEL PREDIKSI HARGA]")
    print(f"      {'Model':<22} {'R²':>7}  {'MAE':>10}")
    print(f"      {'-' * 43}")
    for name, mdl in models_fare.items():
        mdl.fit(Xf_tr, yf_tr)
        pred = mdl.predict(Xf_te)
        r2 = r2_score(yf_te, pred)
        mae = mean_absolute_error(yf_te, pred)
        print(f"      {name:<22} {r2:>7.4f}  ${mae:>8,.2f}")
        if r2 > best_r2_fare:
            best_r2_fare = r2
            best_model_fare = mdl
            best_name_fare = name

    print(f"\n      → Model terbaik: {best_name_fare} (R² = {best_r2_fare:.4f})")

    # Simulasi prediksi harga
    print("\n      --- HASIL SIMULASI PREDIKSI HARGA ---")
    print("      Asumsi: Perjalanan sejauh 5 miles, memakan waktu 20 menit.")
    kasus = [
        ("Hari Kerja Biasa (Cerah)", [5.0, 20.0, 25.0, 0, 0, 0, 0]),
        ("Hari Kerja Biasa (Hujan)", [5.0, 20.0, 20.0, 1, 0, 0, 0]),
        ("Hari Kerja Biasa (Salju)", [5.0, 20.0, -2.0, 0, 1, 0, 0]),
        ("Hari Libur Nasional", [5.0, 20.0, 25.0, 0, 0, 1, 0]),
        ("Akhir Pekan (Weekend)", [5.0, 20.0, 25.0, 0, 0, 0, 1]),
    ]
    for nama, feat in kasus:
        df_kasus = pd.DataFrame([feat], columns=FEAT_FARE)
        pred = best_model_fare.predict(df_kasus)[0]
        print(f"      {nama:<32}: ${pred:.2f}")

    con.close()
    print("\n" + "=" * 60)
    print("  Predictive modelling selesai")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
