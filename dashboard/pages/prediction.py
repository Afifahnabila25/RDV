import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
import requests
from datetime import date, timedelta
from streamlit_folium import st_folium
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

st.set_page_config(layout="wide")
st.title("🔮 Prediction & Machine Learning")
st.markdown("Prediksi harga perjalanan per zona NYC menggunakan Machine Learning + data cuaca real-time.")

try:
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
except ImportError:
    st.error("Library scikit-learn belum terinstall. Jalankan: `pip install scikit-learn`")
    st.stop()

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    con = duckdb.connect(str(DB_PATH), read_only=True)
except Exception as e:
    st.error(f"Gagal terhubung ke database: {e}")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
taxi_str = st.session_state.get("taxi_str", "('yellow','green')")
year_str = st.session_state.get("year_str", "(2025)")
selected_taxis = [t.strip("'") for t in taxi_str.strip("()").split(",")]

# ── Fungsi fetch cuaca forecast dari Open-Meteo ───────────────────────────────
@st.cache_data(ttl=3600)
def fetch_weather_forecast(start_date: str, days: int):
    """Ambil prakiraan cuaca NYC dari Open-Meteo untuk beberapa hari ke depan."""
    end_date = (date.fromisoformat(start_date) + timedelta(days=days - 1)).isoformat()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude=40.7128&longitude=-74.0060"
        f"&daily=temperature_2m_mean,precipitation_sum,weathercode"
        f"&start_date={start_date}&end_date={end_date}"
        f"&timezone=America/New_York"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        df = pd.DataFrame({
            "date":          data["daily"]["time"],
            "temp_mean_c":   data["daily"]["temperature_2m_mean"],
            "precipitation": data["daily"]["precipitation_sum"],
            "weathercode":   data["daily"]["weathercode"],
        })
        df["is_rainy"] = df["weathercode"].between(51, 67) | df["weathercode"].between(80, 82)
        df["is_snowy"] = df["weathercode"].between(71, 77) | df["weathercode"].between(85, 86)
        df["is_rainy"] = df["is_rainy"].astype(int)
        df["is_snowy"] = df["is_snowy"].astype(int)
        return df
    except Exception as e:
        return None

# ── Fungsi cek hari libur ─────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_holidays():
    try:
        rows = con.execute("SELECT date FROM dim_time WHERE is_holiday = TRUE").fetchall()
        return set(str(r[0])[:10] for r in rows)
    except:
        return set()

HOLIDAYS = get_holidays()

# ══════════════════════════════════════════════════════════════════════════════
# TRAIN MODEL — dijalankan sekali, disimpan di session_state
# ══════════════════════════════════════════════════════════════════════════════
if "fare_model" not in st.session_state or st.session_state.get("fare_model_taxi") != taxi_str:
    with st.spinner("⏳ Melatih model prediksi harga... (sekali saja)"):
        try:
            df_fare = con.execute(f"""
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
                  AND f.taxi_type IN {taxi_str}
                  AND t.year IN {year_str}
                USING SAMPLE 100000
            """).df().fillna(0)

            FEAT_FARE = ["trip_distance", "duration_minutes", "temp_mean_c",
                         "is_rainy", "is_snowy", "is_holiday", "is_weekend"]

            X_f = df_fare[FEAT_FARE]
            y_f = df_fare["total_amount"]
            Xf_tr, Xf_te, yf_tr, yf_te = train_test_split(X_f, y_f, test_size=0.2, random_state=42)

            models_fare = {
                "Random Forest": RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42),
                "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42),
            }
            if XGBOOST_AVAILABLE:
                models_fare["XGBoost"] = XGBRegressor(n_estimators=150, learning_rate=0.1, max_depth=5,
                                                       subsample=0.8, random_state=42, verbosity=0)

            res_fare = {}
            for name, mdl in models_fare.items():
                mdl.fit(Xf_tr, yf_tr)
                pred = mdl.predict(Xf_te)
                res_fare[name] = {
                    "model": mdl,
                    "r2": r2_score(yf_te, pred),
                    "mae": mean_absolute_error(yf_te, pred)
                }

            best_name = max(res_fare, key=lambda k: res_fare[k]["r2"])
            st.session_state["fare_model"]      = res_fare[best_name]["model"]
            st.session_state["fare_model_name"] = best_name
            st.session_state["fare_model_r2"]   = res_fare[best_name]["r2"]
            st.session_state["fare_model_mae"]  = res_fare[best_name]["mae"]
            st.session_state["fare_model_taxi"] = taxi_str
            st.session_state["FEAT_FARE"]       = FEAT_FARE

        except Exception as e:
            st.error(f"Error melatih model: {e}")
            st.stop()

best_fare_model = st.session_state["fare_model"]
FEAT_FARE       = st.session_state["FEAT_FARE"]


# ══════════════════════════════════════════════════════════════════════════════
# BAGIAN 1 — PREDIKSI HARGA PER ZONA (1-7 HARI KE DEPAN)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.container(border=True):
    st.subheader("🗓️ Prediksi Harga per Zona — 1 hingga 7 Hari ke Depan")
    st.markdown("Prediksi harga per zona NYC menggunakan **prakiraan cuaca real-time** dari Open-Meteo.")

    # ── Pilih tanggal & jumlah hari ──────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        start_date = st.date_input(
            "Tanggal Mulai Prediksi",
            value=date.today(),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=14)
        )
    with col2:
        num_days = st.slider("Berapa hari ke depan?", min_value=1, max_value=7, value=3)

    # Toggle jenis taksi
    taxi_toggle = st.radio(
        "Tampilkan prediksi untuk:",
        options=["🚕 Yellow Cab", "🚖 Green Cab", "🚕🚖 Semua"],
        horizontal=True,
        key="map_taxi_toggle"
    )

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("🟡➡️🟠 **Yellow Cab**: kuning (murah) → oranye (mahal)")
    with col_info2:
        st.markdown("🟢➡️🌲 **Green Cab**: hijau muda (murah) → hijau tua (mahal)")

    # ── Fetch cuaca ───────────────────────────────────────────────────────────
    with st.spinner("📡 Mengambil data prakiraan cuaca NYC..."):
        df_weather = fetch_weather_forecast(str(start_date), num_days)

    if df_weather is None or df_weather.empty:
        st.warning("Gagal mengambil data cuaca. Pastikan koneksi internet tersedia.")
    else:
        # Tambah flag hari libur & weekend
        df_weather["is_holiday"] = df_weather["date"].isin(HOLIDAYS).astype(int)
        df_weather["is_weekend"] = pd.to_datetime(df_weather["date"]).dt.dayofweek.isin([5, 6]).astype(int)

        # Tampilkan ringkasan cuaca yang diambil
        st.markdown("**☁️ Prakiraan Cuaca NYC yang Digunakan:**")
        weather_display = df_weather[["date", "temp_mean_c", "precipitation", "is_rainy", "is_snowy", "is_holiday", "is_weekend"]].copy()
        weather_display.columns = ["Tanggal", "Suhu (°C)", "Hujan (mm)", "Hujan?", "Salju?", "Hari Libur?", "Weekend?"]
        st.dataframe(weather_display, use_container_width=True, hide_index=True)

        # Load koordinat zona
        zone_coords_path = ROOT / "data" / "raw" / "zone_coords.csv"
        if not zone_coords_path.exists():
            st.warning("File zone_coords.csv tidak ditemukan. Jalankan generate_zone_coords.py dulu.")
        else:
            zone_coords = pd.read_csv(zone_coords_path)

            # Ambil avg distance & duration per zona per taxi type dari historis
            @st.cache_data(ttl=3600)
            def get_zone_hist(taxi_type_filter, _year_str):
                return con.execute(f"""
                    SELECT
                        f.PULocationID      AS location_id,
                        l.zone_name,
                        l.borough,
                        AVG(f.trip_distance)     AS avg_distance,
                        AVG(f.duration_minutes)  AS avg_duration
                    FROM fact_trips f
                    JOIN dim_location l ON f.PULocationID = l.location_id
                    WHERE f.trip_distance > 0
                      AND f.duration_minutes BETWEEN 1 AND 120
                      AND f.taxi_type = '{taxi_type_filter}'
                      AND YEAR(f.trip_date) IN {_year_str}
                    GROUP BY f.PULocationID, l.zone_name, l.borough
                """).df().merge(zone_coords, on="location_id", how="left").dropna(subset=["lat", "lon"])

            def yellow_color(ratio):
                r, g, b = 255, int(220 - ratio * 130), int(50 - ratio * 50)
                return f"#{r:02x}{max(0,g):02x}{max(0,b):02x}"

            def green_color(ratio):
                r, g, b = int(50 - ratio * 30), int(200 - ratio * 100), int(80 - ratio * 50)
                return f"#{max(0,r):02x}{max(0,g):02x}{max(0,b):02x}"

            # ── Tab per hari ─────────────────────────────────────────────────
            day_tabs = st.tabs([
                f"📅 {(start_date + timedelta(days=i)).strftime('%a, %d %b')}"
                for i in range(num_days)
            ])

            all_day_summary = []

            for i, tab in enumerate(day_tabs):
                with tab:
                    day_date   = start_date + timedelta(days=i)
                    day_weather = df_weather.iloc[i]

                    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
                    with col_w1:
                        st.metric("🌡️ Suhu", f"{day_weather['temp_mean_c']:.1f}°C")
                    with col_w2:
                        st.metric("🌧️ Hujan", "Ya" if day_weather["is_rainy"] else "Tidak")
                    with col_w3:
                        st.metric("❄️ Salju", "Ya" if day_weather["is_snowy"] else "Tidak")
                    with col_w4:
                        label_day = "Libur" if day_weather["is_holiday"] else ("Weekend" if day_weather["is_weekend"] else "Weekday")
                        st.metric("📆 Tipe Hari", label_day)

                    # Peta prediksi
                    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="cartodbpositron")

                    taxi_layers = []
                    if taxi_toggle in ["🚕 Yellow Cab", "🚕🚖 Semua"]:
                        taxi_layers.append(("yellow", yellow_color, "Yellow Cab"))
                    if taxi_toggle in ["🚖 Green Cab", "🚕🚖 Semua"]:
                        taxi_layers.append(("green", green_color, "Green Cab"))

                    day_summary = {"Tanggal": str(day_date)}
                    df_first = pd.DataFrame()

                    for taxi_type, color_fn, label in taxi_layers:
                        df_t = get_zone_hist(taxi_type, year_str).copy()
                        zone_inputs = pd.DataFrame({
                            "trip_distance":    df_t["avg_distance"],
                            "duration_minutes": df_t["avg_duration"],
                            "temp_mean_c":      day_weather["temp_mean_c"],
                            "is_rainy":         int(day_weather["is_rainy"]),
                            "is_snowy":         int(day_weather["is_snowy"]),
                            "is_holiday":       int(day_weather["is_holiday"]),
                            "is_weekend":       int(day_weather["is_weekend"]),
                        })
                        df_t["predicted_price"] = best_fare_model.predict(zone_inputs)
                        min_p = df_t["predicted_price"].min()
                        max_p = df_t["predicted_price"].max()

                        if df_first.empty:
                            df_first = df_t.copy()
                            day_summary[f"Avg Harga ({label})"] = f"${df_t['predicted_price'].mean():.2f}"

                        for _, row in df_t.iterrows():
                            ratio = (row["predicted_price"] - min_p) / (max_p - min_p + 1e-9)
                            color = color_fn(ratio)
                            lat_offset = 0.003 if taxi_type == "green" and taxi_toggle == "🚕🚖 Semua" else 0
                            folium.CircleMarker(
                                location=[row["lat"] + lat_offset, row["lon"]],
                                radius=7,
                                color=color, fill=True, fill_color=color, fill_opacity=0.8,
                                tooltip=(
                                    f"[{label}] {row['zone_name']} ({row['borough']})<br>"
                                    f"Prediksi: ${row['predicted_price']:.2f}<br>"
                                    f"Avg Jarak: {row['avg_distance']:.1f} mil | "
                                    f"Avg Durasi: {row['avg_duration']:.0f} mnt"
                                )
                            ).add_to(m)

                    st_folium(m, width=1300, height=480, returned_objects=[])

                    if not df_first.empty:
                        cl1, cl2, cl3 = st.columns(3)
                        with cl1:
                            st.markdown(f"🟡/🟢 Termurah: **${df_first['predicted_price'].min():.2f}**")
                        with cl2:
                            st.markdown(f"⬛ Rata-rata: **${df_first['predicted_price'].mean():.2f}**")
                        with cl3:
                            st.markdown(f"🟠/🌲 Termahal: **${df_first['predicted_price'].max():.2f}**")

                    all_day_summary.append(day_summary)

            # ── Grafik tren harga rata-rata per hari ─────────────────────────
            if len(all_day_summary) > 1:
                st.markdown("#### 📈 Tren Prediksi Harga Rata-rata per Hari")
                df_summary = pd.DataFrame(all_day_summary)
                price_cols = [c for c in df_summary.columns if "Avg Harga" in c]
                for col in price_cols:
                    df_summary[col] = df_summary[col].str.replace("$", "").astype(float)

                fig_trend = go.Figure()
                colors_line = {"Yellow Cab": "#F39C12", "Green Cab": "#27AE60"}
                for col in price_cols:
                    taxi_label = col.replace("Avg Harga (", "").replace(")", "")
                    fig_trend.add_trace(go.Scatter(
                        x=df_summary["Tanggal"], y=df_summary[col],
                        mode="lines+markers+text",
                        name=taxi_label,
                        text=[f"${v:.2f}" for v in df_summary[col]],
                        textposition="top center",
                        line=dict(color=colors_line.get(taxi_label, "#3498DB"), width=2),
                        marker=dict(size=8)
                    ))
                fig_trend.update_layout(
                    title="Tren Prediksi Harga Rata-rata NYC per Hari",
                    xaxis_title="Tanggal",
                    yaxis_title="Prediksi Harga ($)",
                    margin=dict(t=40, b=20)
                )
                st.plotly_chart(fig_trend, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BAGIAN 2 — TOP ZONA DEMAND
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.container(border=True):
    st.subheader("📍 Prediksi Zona Paling Ramai")
    st.markdown("Zona dengan **demand tertinggi** berdasarkan tren historis.")

    try:
        df_zone = con.execute(f"""
            SELECT
                l.zone_name,
                l.borough,
                COUNT(*)                          AS total_trips,
                ROUND(AVG(f.total_amount), 2)     AS avg_revenue_per_trip,
                ROUND(STDDEV(f.total_amount), 2)  AS std_revenue_per_trip,
                ROUND(SUM(f.total_amount), 2)     AS total_revenue
            FROM fact_trips f
            JOIN dim_location l ON f.PULocationID = l.location_id
            WHERE f.taxi_type IN {taxi_str}
              AND YEAR(f.trip_date) IN {year_str}
            GROUP BY l.zone_name, l.borough
            ORDER BY total_trips DESC
            LIMIT 10
        """).df()

        if not df_zone.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig_demand = px.bar(
                    df_zone, x="total_trips", y="zone_name", orientation="h",
                    title="Top 10 Zona — Demand Tertinggi",
                    color="total_trips", color_continuous_scale="Oranges",
                    labels={"total_trips": "Jumlah Trip", "zone_name": "Zona"},
                    text_auto=True
                )
                fig_demand.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=40, b=20))
                st.plotly_chart(fig_demand, use_container_width=True)

            with col2:
                fig_rev = px.bar(
                    df_zone, x="avg_revenue_per_trip", y="zone_name", orientation="h",
                    title="Top 10 Zona — Rata-rata Revenue per Trip",
                    color="avg_revenue_per_trip", color_continuous_scale="Greens",
                    labels={"avg_revenue_per_trip": "Avg Revenue ($)", "zone_name": "Zona"},
                    error_x="std_revenue_per_trip",
                    text_auto=".2f"
                )
                fig_rev.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=40, b=20))
                st.plotly_chart(fig_rev, use_container_width=True)

            with st.expander("Lihat Data Lengkap"):
                st.dataframe(df_zone, use_container_width=True)

    except Exception as e:
        st.error(f"Error memuat data zona: {e}")

con.close()