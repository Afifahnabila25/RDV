import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from pathlib import Path

# CSS INJECTION
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');

html, body, .stApp {
    font-family: 'Poppins', sans-serif !important;
    background-color: #EAECF0 !important;
}
.main .block-container {
    background-color: #EAECF0 !important;
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #DDE1E8 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown { font-family: 'Poppins', sans-serif !important; }

/* Card putih */
.st-key-rr_top_zone_card,
.st-key-rr_daily_trend_card,
.st-key-rr_map_card,
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
    border: 1px solid #E2E6ED !important;
    box-shadow: none !important;
    padding: 1.25rem 1.25rem !important;
}

.st-key-rr_top_zone_card [data-testid="stVerticalBlockBorderWrapper"],
.st-key-rr_daily_trend_card [data-testid="stVerticalBlockBorderWrapper"],
.st-key-rr_map_card [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

.st-key-rr_top_zone_card [data-testid="stVerticalBlock"],
.st-key-rr_daily_trend_card [data-testid="stVerticalBlock"],
.st-key-rr_map_card [data-testid="stVerticalBlock"] {
    background-color: #FFFFFF !important;
}

/* Typography */
h1 { font-family: 'Poppins', sans-serif !important; font-weight: 700 !important; color: #1E2A3A !important; font-size: 1.5rem !important; }
h2, h3 { font-family: 'Poppins', sans-serif !important; color: #1E2A3A !important; }
.stMarkdown h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #1E2A3A !important; }
[data-testid="stHeading"] h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #1E2A3A !important; }
p, div { font-family: 'Poppins', sans-serif !important; }

/* Icon font fix for Streamlit */
[data-testid="stIcon"],
[data-testid="stIcon"] span,
span.material-symbols-outlined,
span.material-icons {
    font-family: 'Material Symbols Outlined' !important;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

/* Multiselect */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] { background-color: #4B7FF2 !important; border-radius: 6px !important; }
hr { border-color: #E2E6ED !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #C1C8D4; border-radius: 3px; }
</style>
""",
    unsafe_allow_html=True,
)

# COLOR PALETTE
WARNA_TREN = ["#4B7FF2"]

st.title("📍 Revenue & Region Analysis")
st.markdown(
    "<p style='color:#6B7280;font-size:1rem;font-family:Poppins,sans-serif;margin-top:-0.5rem;margin-bottom:1.2rem;'>Analisis spasial pendapatan berdasarkan zona drop-off/pickup taxi di NYC.</p>",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

st.sidebar.header("Filter Halaman")
taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect(
    "Jenis Taksi",
    options=list(taxi_options.keys()),
    default=list(taxi_options.keys()),
    key="rr_taxi",
)
selected_taxis = [taxi_options[lbl] for lbl in selected_taxi_labels]

try:
    available_years = [
        int(r[0])
        for r in con.execute(
            "SELECT DISTINCT year FROM dim_time ORDER BY year"
        ).fetchall()
        if r[0] is not None
    ]
except:
    available_years = [2024, 2025]
selected_years = st.sidebar.multiselect(
    "Tahun", options=available_years, default=available_years, key="rr_year"
)

if not selected_taxis or not selected_years:
    st.warning("Silakan pilih Jenis Taksi dan Tahun di sidebar.")
    st.stop()

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(" + ",".join(map(str, selected_years)) + ")"

query_kpi = f"""
    SELECT COUNT(*) as total_trips, SUM(total_amount) as total_rev, AVG(trip_distance) as avg_dist
    FROM fact_trips
    WHERE taxi_type IN {taxi_str} AND YEAR(trip_date) IN {year_str}
"""
kpi_data = con.execute(query_kpi).fetchone()

# KPI CARDS─
kpi_css = """
<style>
.kpi-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E6ED;
    padding: 1.1rem 1.25rem;
    width: 100%;
    box-sizing: border-box;
    box-shadow: none;
}
.kpi-label {
    font-family: 'Poppins', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.35rem;
}
.kpi-value {
    font-family: 'Poppins', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: #1E2A3A;
    line-height: 1.15;
    margin: 0;
}
</style>
"""
st.markdown(kpi_css, unsafe_allow_html=True)

c1, c2, c3 = st.columns(3, gap="small")
kpi_items = [
    ("🗺️ TOTAL WILAYAH TRIP", f"{kpi_data[0]:,}", "#4B7FF2"),
    (
        "💰 TOTAL PENDAPATAN WILAYAH",
        f"${kpi_data[1]:,.2f}" if kpi_data[1] else "$0.00",
        "#31C28E",
    ),
    (
        "📏 RATA-RATA JARAK PERJALANAN",
        f"{kpi_data[2]:.2f} mil" if kpi_data[2] else "0 mil",
        "#F8B320",
    ),
]
for col, (label, value, color) in zip([c1, c2, c3], kpi_items):
    with col:
        st.markdown(
            f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.container(border=True, key="rr_top_zone_card"):
    st.subheader("🏆 Top 10 Zona Penghasil Revenue Tertinggi")
    query_top_zone = f"""
        SELECT l.zone_name, SUM(f.total_amount) as total_revenue
        FROM fact_trips f
        JOIN dim_location l ON f.PULocationID = l.location_id
        WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
        GROUP BY l.zone_name ORDER BY total_revenue DESC LIMIT 10
    """
    df_zone = con.execute(query_top_zone).df()

    if not df_zone.empty:
        fig_bar = px.bar(
            df_zone,
            x="total_revenue",
            y="zone_name",
            orientation="h",
            labels={"total_revenue": "Total Pendapatan", "zone_name": "Nama Zona"},
            color="total_revenue",
            color_continuous_scale=[[0, "#46C6FA"], [0.5, "#4B7FF2"], [1, "#7C53FA"]],
            hover_data={"total_revenue": ":$.2f"},
        )
        fig_bar.update_layout(
            yaxis=dict(categoryorder="total ascending", linecolor="#E2E6ED"),
            margin=dict(t=20, b=10, l=10, r=10),
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Poppins, sans-serif", color="#1E2A3A"),
            xaxis=dict(gridcolor="#F0F2F5", linecolor="#E2E6ED"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Data zona tidak ditemukan.")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

with st.container(border=True, key="rr_daily_trend_card"):
    st.subheader("📈 Tren Pendapatan Harian")
    query_trend = f"""
        SELECT trip_date, SUM(total_amount) as daily_revenue
        FROM fact_trips
        WHERE taxi_type IN {taxi_str} AND YEAR(trip_date) IN {year_str}
        GROUP BY trip_date ORDER BY trip_date
    """
    df_trend = con.execute(query_trend).df()

    if not df_trend.empty:
        fig_line = px.line(
            df_trend,
            x="trip_date",
            y="daily_revenue",
            labels={"trip_date": "Tanggal", "daily_revenue": "Pendapatan Harian"},
            color_discrete_sequence=WARNA_TREN,
            hover_data={"daily_revenue": ":$.2f"},
        )
        fig_line.update_layout(
            margin=dict(t=20, b=10, l=10, r=10),
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Poppins, sans-serif", color="#1E2A3A"),
            xaxis=dict(gridcolor="#F0F2F5", linecolor="#E2E6ED"),
            yaxis=dict(gridcolor="#F0F2F5", linecolor="#E2E6ED"),
        )
        fig_line.update_traces(line_color="#4B7FF2", line_width=2)
        st.caption("Fluktuasi Pendapatan Harian NYC Taxi")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Data tren harian tidak ditemukan.")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

with st.container(border=True, key="rr_map_card"):
    st.subheader("🗺️ Peta Kepadatan Destinasi/Wilayah NYC Taxi")
    st.caption("Peta interaktif berbasis koordinat titik lokasi sentral New York.")

    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="cartodbpositron")

    query_map = f"""
        SELECT PULocationID, COUNT(*) as jumlah_trip 
        FROM fact_trips 
        WHERE taxi_type IN {taxi_str} AND YEAR(trip_date) IN {year_str}
        GROUP BY PULocationID
    """
    df_map_data = con.execute(query_map).df()

    for idx, row in df_map_data.head(50).iterrows():
        lat = 40.7128 + (idx * 0.003 - 0.05)
        lon = -74.0060 + (idx * -0.001 + 0.04)
        folium.CircleMarker(
            location=[lat, lon],
            radius=min(max(int(row["jumlah_trip"]) / 5, 5), 25),
            color="#7C53FA" if row["PULocationID"] % 2 == 0 else "#4B7FF2",
            fill=True,
            fill_opacity=0.6,
            tooltip=f"ID Lokasi: {int(row['PULocationID'])} | Total Trips: {int(row['jumlah_trip'])}",
        ).add_to(m)

    st_folium(m, width=1300, height=500, returned_objects=[])

con.close()
