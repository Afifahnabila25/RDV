import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
import requests

from datetime import date, timedelta
from streamlit_folium import st_folium
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
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
""", unsafe_allow_html=True)

st.title("🔮 Prediction & Machine Learning")
st.markdown("Prediksi harga perjalanan per zona NYC menggunakan Machine Learning + data cuaca real-time.")

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

@st.cache_data(ttl=3600)
def fetch_weather_forecast(start_date: str, days: int):

    end_date = (
        date.fromisoformat(start_date) +
        timedelta(days=days - 1)
    ).isoformat()

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude=40.7128&longitude=-74.0060"
        f"&daily=temperature_2m_mean,precipitation_sum,weathercode"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&timezone=America/New_York"
    )

    try:

        resp = requests.get(url, timeout=10)
        data = resp.json()

        df = pd.DataFrame({
            "date": data["daily"]["time"],
            "temp_mean_c": data["daily"]["temperature_2m_mean"],
            "precipitation": data["daily"]["precipitation_sum"],
            "weathercode": data["daily"]["weathercode"]
        })

        df["is_rainy"] = (
            df["weathercode"].between(51, 67) |
            df["weathercode"].between(80, 82)
        ).astype(int)

        df["is_snowy"] = (
            df["weathercode"].between(71, 77) |
            df["weathercode"].between(85, 86)
        ).astype(int)

        return df

    except:
        return None

@st.cache_data(ttl=86400)
def get_holidays():

    try:

        rows = con.execute("""
            SELECT date
            FROM dim_time
            WHERE is_holiday = TRUE
        """).fetchall()

        return set(str(r[0])[:10] for r in rows)

    except:
        return set()

HOLIDAYS = get_holidays()

if (
    "fare_model" not in st.session_state or
    st.session_state.get("fare_model_taxi") != taxi_str
):

    with st.spinner("Training model..."):

        try:

            df_fare = con.execute(f"""
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
            """).df().fillna(0)

            FEAT_FARE = [
                "trip_distance",
                "duration_minutes",
                "temp_mean_c",
                "is_rainy",
                "is_snowy",
                "is_holiday",
                "is_weekend"
            ]

            X_f = df_fare[FEAT_FARE]
            y_f = df_fare["total_amount"]

            Xf_tr, Xf_te, yf_tr, yf_te = train_test_split(
                X_f,
                y_f,
                test_size=0.2,
                random_state=42
            )

            models = {
                "Random Forest": RandomForestRegressor(
                    n_estimators=50,
                    max_depth=10,
                    random_state=42
                ),
                "Gradient Boosting": GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
            }

            if XGBOOST_AVAILABLE:

                models["XGBoost"] = XGBRegressor(
                    n_estimators=150,
                    learning_rate=0.1,
                    max_depth=5,
                    subsample=0.8,
                    random_state=42,
                    verbosity=0
                )

            results = {}

            for name, mdl in models.items():

                mdl.fit(Xf_tr, yf_tr)

                pred = mdl.predict(Xf_te)

                results[name] = {
                    "model": mdl,
                    "r2": r2_score(yf_te, pred)
                }

            best_name = max(results, key=lambda k: results[k]["r2"])

            st.session_state["fare_model"] = results[best_name]["model"]
            st.session_state["fare_model_taxi"] = taxi_str

        except Exception as e:

            st.error(e)
            st.stop()

best_fare_model = st.session_state["fare_model"]

st.divider()

st.subheader("🗓️ Prediksi Harga per Zona")

col1, col2 = st.columns([2,1])

with col1:

    start_date = st.date_input(
        "Tanggal Mulai Prediksi",
        value=date.today(),
        min_value=date.today(),
        max_value=date.today() + timedelta(days=14)
    )

with col2:

    num_days = st.slider(
        "Berapa hari ke depan?",
        1,
        7,
        3
    )

taxi_toggle = st.radio(
    "Tampilkan prediksi:",
    [
        "🚕 Yellow Cab",
        "🚖 Green Cab",
        "🚕🚖 Semua"
    ],
    horizontal=True
)

with st.spinner("Mengambil cuaca..."):

    df_weather = fetch_weather_forecast(
        str(start_date),
        num_days
    )

if df_weather is not None and not df_weather.empty:

    df_weather["is_holiday"] = (
        df_weather["date"]
        .isin(HOLIDAYS)
        .astype(int)
    )

    df_weather["is_weekend"] = (
        pd.to_datetime(df_weather["date"])
        .dt.dayofweek
        .isin([5,6])
        .astype(int)
    )

    weather_display = df_weather[
        [
            "date",
            "temp_mean_c",
            "precipitation",
            "is_rainy",
            "is_snowy",
            "is_holiday",
            "is_weekend"
        ]
    ].copy()

    weather_display.columns = [
        "Tanggal",
        "Suhu",
        "Hujan(mm)",
        "Hujan?",
        "Salju?",
        "Libur?",
        "Weekend?"
    ]

    st.dataframe(
        weather_display,
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.subheader("📍 Prediksi Zona Paling Ramai")

try:

    df_zone = con.execute(f"""
        SELECT
            l.zone_name,
            l.borough,
            COUNT(*) AS total_trips,
            ROUND(AVG(f.total_amount),2) AS avg_revenue_per_trip,
            ROUND(STDDEV(f.total_amount),2) AS std_revenue_per_trip,
            ROUND(SUM(f.total_amount),2) AS total_revenue
        FROM fact_trips f
        JOIN dim_location l
            ON f.PULocationID = l.location_id
        WHERE f.taxi_type IN {taxi_str}
          AND YEAR(f.trip_date) IN {year_str}
        GROUP BY
            l.zone_name,
            l.borough
        ORDER BY total_trips DESC
        LIMIT 10
    """).df()

    if not df_zone.empty:

        col1, col2 = st.columns(2)

        with col1:

            fig_demand = px.bar(
                df_zone,
                x="total_trips",
                y="zone_name",
                orientation="h",
                color="total_trips",
                color_continuous_scale="Oranges",
                text_auto=True
            )

            fig_demand.update_layout(
                margin=dict(t=20, b=20),
                yaxis={"categoryorder":"total ascending"},
                paper_bgcolor="white",
                plot_bgcolor="white"
            )

            st.plotly_chart(
                fig_demand,
                use_container_width=True
            )

        with col2:

            fig_rev = px.bar(
                df_zone,
                x="avg_revenue_per_trip",
                y="zone_name",
                orientation="h",
                color="avg_revenue_per_trip",
                color_continuous_scale="Greens",
                error_x="std_revenue_per_trip",
                text_auto=".2f"
            )

            fig_rev.update_layout(
                margin=dict(t=20, b=20),
                yaxis={"categoryorder":"total ascending"},
                paper_bgcolor="white",
                plot_bgcolor="white"
            )

            st.plotly_chart(
                fig_rev,
                use_container_width=True
            )

        with st.expander("Lihat Data Lengkap"):

            st.dataframe(
                df_zone,
                use_container_width=True,
                hide_index=True
            )

except Exception as e:

    st.error(e)

con.close()