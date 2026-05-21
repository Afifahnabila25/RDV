import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import folium
from datetime import date
from streamlit_folium import st_folium
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>

html, body, [class*="css"] {
    background-color: #ffffff !important;
}

[data-testid="stAppViewContainer"]{
    background:#ffffff !important;
}

[data-testid="stHeader"]{
    background:#ffffff !important;
}

[data-testid="stToolbar"]{
    background:#ffffff !important;
}

.main{
    background:#ffffff !important;
}

.block-container{
    background:#ffffff !important;
    padding-top:1rem !important;
    padding-bottom:1rem !important;
    max-width:100% !important;
}

section[data-testid="stSidebar"]{
    background:#ffffff !important;
    border-right:1px solid #e5e7eb;
}

div[data-testid="stVerticalBlock"]{
    background:#ffffff !important;
}

div[data-testid="stHorizontalBlock"]{
    background:#ffffff !important;
}

div[data-testid="stMetric"]{
    background:#ffffff !important;
    border:1px solid #e5e7eb !important;
    border-radius:12px !important;
    padding:10px !important;
}

div[data-testid="stPlotlyChart"]{
    background:#ffffff !important;
    border:1px solid #e5e7eb !important;
    border-radius:12px !important;
    padding:10px !important;
}

div[data-testid="stDataFrame"]{
    background:#ffffff !important;
    border:1px solid #e5e7eb !important;
    border-radius:12px !important;
    padding:10px !important;
}

div[data-testid="stExpander"]{
    background:#ffffff !important;
    border:1px solid #e5e7eb !important;
    border-radius:12px !important;
}

div[data-testid="stTabs"]{
    background:#ffffff !important;
}

iframe{
    border-radius:12px !important;
    overflow:hidden !important;
}

</style>
""",
    unsafe_allow_html=True,
)

st.title("🔮 Prediction & Machine Learning")
st.markdown(
    "Prediksi harga perjalanan per zona NYC menggunakan Machine Learning + data cuaca real-time."
)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import r2_score
except ImportError:
    st.error("Install scikit-learn dulu")
    st.stop()

try:
    from xgboost import XGBRegressor

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    con = duckdb.connect(str(DB_PATH), read_only=True)
except Exception as e:
    st.error(f"Gagal konek DB: {e}")
    st.stop()

taxi_str = st.session_state.get("taxi_str", "('yellow','green')")
year_str = st.session_state.get("year_str", "(2025)")


if (
    "fare_model" not in st.session_state
    or st.session_state.get("fare_model_taxi") != taxi_str
):
    with st.spinner("Training model..."):
        try:
            df_fare = (
                con.execute(f"""
                SELECT
                    f.total_amount,
                    f.trip_distance,
                    f.duration_minutes,
                    w.temp_mean_c,
                    CAST(w.is_rainy AS INT) AS is_rainy,
                    CAST(w.is_snowy AS INT) AS is_snowy,
                    CAST(t.is_holiday AS INT) AS is_holiday,
                    CAST(t.is_weekend AS INT) AS is_weekend
                FROM fact_trips f
                JOIN dim_weather w
                    ON f.trip_date = w.date
                JOIN dim_time t
                    ON f.trip_date = t.date
                WHERE f.total_amount > 0
                  AND f.trip_distance > 0
                  AND f.duration_minutes BETWEEN 1 AND 120
                  AND f.taxi_type IN {taxi_str}
                  AND t.year IN {year_str}
                USING SAMPLE 100000
            """)
                .df()
                .fillna(0)
            )

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

            models = {
                "Random Forest": RandomForestRegressor(
                    n_estimators=50, max_depth=10, random_state=42
                ),
                "Gradient Boosting": GradientBoostingRegressor(
                    n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
                ),
            }

            if XGBOOST_AVAILABLE:
                models["XGBoost"] = XGBRegressor(
                    n_estimators=150,
                    learning_rate=0.1,
                    max_depth=5,
                    subsample=0.8,
                    random_state=42,
                    verbosity=0,
                )

            results = {}

            for name, mdl in models.items():
                mdl.fit(Xf_tr, yf_tr)

                pred = mdl.predict(Xf_te)

                results[name] = {"model": mdl, "r2": r2_score(yf_te, pred)}

            best_name = max(results, key=lambda k: results[k]["r2"])

            st.session_state["fare_model"] = results[best_name]["model"]
            st.session_state["fare_model_taxi"] = taxi_str

        except Exception as e:
            st.error(e)
            st.stop()

best_fare_model = st.session_state["fare_model"]

st.divider()

st.subheader("🗓️ Prediksi Harga per Zona")
st.caption(
    "Atur kondisi di bawah untuk mensimulasikan estimasi harga — berdasarkan pola historis 2025."
)

# Simulator kondisi
sim_c1, sim_c2, sim_c3 = st.columns(3)

with sim_c1:
    tipe_hari = st.selectbox(
        "📆 Tipe Hari",
        options=["Weekday", "Weekend", "Hari Libur Nasional"],
        index=0,
    )
    is_weekend = 1 if tipe_hari == "Weekend" else 0
    is_holiday = 1 if tipe_hari == "Hari Libur Nasional" else 0

with sim_c2:
    cuaca = st.selectbox(
        "🌤️ Kondisi Cuaca",
        options=["Cerah / Normal", "Hujan", "Salju"],
        index=0,
    )
    is_rainy = 1 if cuaca == "Hujan" else 0
    is_snowy = 1 if cuaca == "Salju" else 0

with sim_c3:
    temp_mean_c = st.slider(
        "🌡️ Suhu (°C)", min_value=-10, max_value=40, value=18, step=1
    )

# Tentukan taxi_toggle dari filter global
if "yellow" in taxi_str and "green" in taxi_str:
    taxi_toggle = "🚕🚖 Semua"
elif "yellow" in taxi_str:
    taxi_toggle = "🚕 Yellow Cab"
else:
    taxi_toggle = "🚖 Green Cab"

# Bangun df_weather sintetis 1 baris dari kondisi yang dipilih
df_weather = pd.DataFrame(
    {
        "date": [date.today().isoformat()],
        "temp_mean_c": [temp_mean_c],
        "precipitation": [0.0],
        "is_rainy": [is_rainy],
        "is_snowy": [is_snowy],
        "is_holiday": [is_holiday],
        "is_weekend": [is_weekend],
    }
)

# PETA PER HARI─
# Load zone coords
zone_coords_path = ROOT / "data" / "raw" / "zone_coords.csv"

if not zone_coords_path.exists():
    st.warning("File zone_coords.csv tidak ditemukan.")
    st.stop()

zone_coords = pd.read_csv(zone_coords_path)


# Definisi fungsi di LUAR blok if, dengan decorator cache
@st.cache_data(ttl=3600)
def get_zone_hist(taxi_type_filter, _year_str):
    return (
        con.execute(f"""
            SELECT
                f.PULocationID AS location_id,
                l.zone_name,
                l.borough,
                AVG(f.trip_distance)    AS avg_distance,
                AVG(f.duration_minutes) AS avg_duration
            FROM fact_trips f
            JOIN dim_location l ON f.PULocationID = l.location_id
            WHERE f.trip_distance > 0
              AND f.duration_minutes BETWEEN 1 AND 120
              AND f.taxi_type = '{taxi_type_filter}'
              AND YEAR(f.trip_date) IN {_year_str}
            GROUP BY f.PULocationID, l.zone_name, l.borough
        """)
        .df()
        .merge(zone_coords, on="location_id", how="left")
        .dropna(subset=["lat", "lon"])
    )


def yellow_color(ratio):
    r = 255
    g = int(220 - ratio * 130)
    b = int(50 - ratio * 50)
    return f"#{r:02x}{max(0, g):02x}{max(0, b):02x}"


def green_color(ratio):
    r = int(50 - ratio * 30)
    g = int(200 - ratio * 100)
    b = int(80 - ratio * 50)
    return f"#{max(0, r):02x}{max(0, g):02x}{max(0, b):02x}"


# Peta prediksi harga per zona
if df_weather is not None and not df_weather.empty:
    # Pakai kondisi dari baris pertama (semua baris identik karena dari simulator)
    day_weather = df_weather.iloc[0]

    # Metric ringkasan kondisi
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Suhu", f"{day_weather['temp_mean_c']:.1f}°C")
    c2.metric("🌧️ Hujan", "Ya" if day_weather["is_rainy"] else "Tidak")
    c3.metric("❄️ Salju", "Ya" if day_weather["is_snowy"] else "Tidak")
    label_day = (
        "Libur"
        if day_weather["is_holiday"]
        else "Weekend"
        if day_weather["is_weekend"]
        else "Weekday"
    )
    c4.metric("📆 Tipe Hari", label_day)

    # Tentukan layer taksi yang ditampilkan
    taxi_layers = []
    if taxi_toggle in ["🚕 Yellow Cab", "🚕🚖 Semua"]:
        taxi_layers.append(("yellow", yellow_color, "Yellow Cab"))
    if taxi_toggle in ["🚖 Green Cab", "🚕🚖 Semua"]:
        taxi_layers.append(("green", green_color, "Green Cab"))

    # Bangun peta Folium
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="cartodbpositron")

    all_predicted = []

    # Pass 1 — hitung prediksi semua taxi, simpan hasilnya
    taxi_results = []
    for taxi_type, color_fn, label in taxi_layers:
        df_t = get_zone_hist(taxi_type, year_str).copy()

        zone_inputs = pd.DataFrame(
            {
                "trip_distance": df_t["avg_distance"],
                "duration_minutes": df_t["avg_duration"],
                "temp_mean_c": day_weather["temp_mean_c"],
                "is_rainy": int(day_weather["is_rainy"]),
                "is_snowy": int(day_weather["is_snowy"]),
                "is_holiday": int(day_weather["is_holiday"]),
                "is_weekend": int(day_weather["is_weekend"]),
            }
        )

        df_t["predicted_price"] = best_fare_model.predict(zone_inputs)
        all_predicted.append(df_t["predicted_price"])
        taxi_results.append((taxi_type, color_fn, label, df_t))

    # Global min/max dari semua taxi gabungan — skala warna konsisten
    global_min = pd.concat(all_predicted).min()
    global_max = pd.concat(all_predicted).max()

    # Kumpulkan semua df untuk legend
    df_all = pd.concat([r[3] for r in taxi_results], ignore_index=True)

    # Pass 2 — render marker ke peta pakai skala global
    for taxi_type, color_fn, label, df_t in taxi_results:
        lat_offset = (
            0.003 if (taxi_type == "green" and taxi_toggle == "🚕🚖 Semua") else 0
        )

        for _, row in df_t.iterrows():
            ratio = (row["predicted_price"] - global_min) / (
                global_max - global_min + 1e-9
            )
            color = color_fn(ratio)
            folium.CircleMarker(
                location=[row["lat"] + lat_offset, row["lon"]],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=(
                    f"[{label}] {row['zone_name']} ({row['borough']})<br>"
                    f"Prediksi: ${row['predicted_price']:.2f}<br>"
                    f"Avg Jarak: {row['avg_distance']:.1f} mil"
                ),
            ).add_to(m)

    st_folium(m, width=1300, height=480, returned_objects=[], key="map_simulator")

    # Ringkasan harga prediksi UI sama dengan metric di atas
    if not df_all.empty:
        cl1, cl2, cl3 = st.columns(3)
        cl1.metric("🟢 Termurah", f"${df_all['predicted_price'].min():.2f}")
        cl2.metric("⬛ Rata-rata", f"${df_all['predicted_price'].mean():.2f}")
        cl3.metric("🔴 Termahal", f"${df_all['predicted_price'].max():.2f}")

else:
    st.warning("Kondisi tidak valid.")


con.close()
