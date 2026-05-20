import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from pathlib import Path

WARNA_TREN = ['#3498DB']  
st.set_page_config(layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
    }
    div[data-testid="stBlock"] div[data-testid="element-container"] button {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📍 Revenue & Region Analysis")
st.markdown("Analisis spasial pendapatan berdasarkan zona drop-off/pickup taxi di NYC.")

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

st.sidebar.header("Filter Halaman")
taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect("Jenis Taksi", options=list(taxi_options.keys()), default=list(taxi_options.keys()), key="rr_taxi")
selected_taxis = [taxi_options[lbl] for lbl in selected_taxi_labels]

if not selected_taxis:
    st.warning("Silakan pilih Jenis Taksi di sidebar.")
    st.stop()

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(2025)"

query_kpi = f"""
    SELECT 
        COUNT(*) as total_trips,
        SUM(total_amount) as total_rev,
        AVG(trip_distance) as avg_dist
    FROM fact_trips
    WHERE taxi_type IN {taxi_str} 
      AND YEAR(trip_date) IN {year_str}
"""
kpi_data = con.execute(query_kpi).fetchone()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Wilayah Trip", f"{kpi_data[0]:,}")
with c2:
    st.metric("Total Pendapatan Wilayah (2025)", f"${kpi_data[1]:,.2f}" if kpi_data[1] else "$0.00")
with c3:
    st.metric("Rata-rata Jarak Perjalanan", f"{kpi_data[2]:.2f} mil" if kpi_data[2] else "0 mil")

st.markdown("---")

st.subheader("🏆 Top 10 Zona Penghasil Revenue Tertinggi (2025)")
query_top_zone = f"""
    SELECT l.zone_name, SUM(f.total_amount) as total_revenue
    FROM fact_trips f
    JOIN dim_location l ON f.PULocationID = l.location_id
    WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
    GROUP BY l.zone_name
    ORDER BY total_revenue DESC
    LIMIT 10
"""
df_zone = con.execute(query_top_zone).df()

if not df_zone.empty:
    fig_bar = px.bar(
        df_zone, 
        x='total_revenue', 
        y='zone_name', 
        orientation='h',
        labels={'total_revenue': 'Total Pendapatan', 'zone_name': 'Nama Zona'},
        color='total_revenue',
        color_continuous_scale='Blugrn',
        hover_data={'total_revenue': ':$.2f'} 
    )
    fig_bar.update_layout(
        yaxis={'categoryorder':'total ascending'},
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Data zona tidak ditemukan.")

st.markdown("---")

st.subheader("📈 Tren Pendapatan Harian Sepanjang Tahun 2025")
query_trend = f"""
    SELECT trip_date, SUM(total_amount) as daily_revenue
    FROM fact_trips
    WHERE taxi_type IN {taxi_str} AND YEAR(trip_date) IN {year_str}
    GROUP BY trip_date
    ORDER BY trip_date
"""
df_trend = con.execute(query_trend).df()

if not df_trend.empty:
    fig_line = px.line(
        df_trend, 
        x='trip_date', 
        y='daily_revenue',
        labels={'trip_date': 'Tanggal', 'daily_revenue': 'Pendapatan Harian'},
        title="Fluktuasi Pendapatan Harian NYC Taxi (2025)",
        color_discrete_sequence=WARNA_TREN,
        hover_data={'daily_revenue': ':$.2f'} 
    )
    fig_line.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Data tren harian tidak ditemukan.")

st.markdown("---")

st.subheader("🗺️ Peta Kepadatan Destinasi/Wilayah NYC Taxi (2025)")
st.markdown("> *Peta interaktif berbasis koordinat titik lokasi sentral New York.*")

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
        radius=min(max(int(row['jumlah_trip']) / 5, 5), 25),
        color="#E74C3C" if row['PULocationID'] % 2 == 0 else "#3498DB", 
        fill=True,
        fill_opacity=0.6,
        tooltip=f"ID Lokasi: {int(row['PULocationID'])} | Total Trips: {int(row['jumlah_trip'])}"
    ).add_to(m)

st_folium(m, width=1300, height=500, returned_objects=[])

con.close()