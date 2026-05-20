import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path


WARNA_HOLIDAY = {'Hari Libur Nasional': '#E74C3C', 'Hari Kerja Biasa': '#34495E'}

st.set_page_config(layout="wide")

st.title("⏰ Time & External Factors Analysis")
st.markdown("Analisis pengaruh waktu, cuaca harian, dan hari libur nasional terhadap operasional taksi.")

# Koneksi Database
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

# Filter Sidebar
st.sidebar.header("Filter Halaman")
taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect("Jenis Taksi", options=list(taxi_options.keys()), default=list(taxi_options.keys()), key="te_taxi")
selected_taxis = [taxi_options[lbl] for lbl in selected_taxi_labels]

try:
    available_years = [int(r[0]) for r in con.execute("SELECT DISTINCT year FROM dim_time ORDER BY year").fetchall() if r[0] is not None]
except:
    available_years = [2024, 2025]
selected_years = st.sidebar.multiselect("Tahun", options=available_years, default=available_years, key="te_year")

if not selected_taxis or not selected_years:
    st.warning("Silakan pilih Jenis Taksi dan Tahun di sidebar.")
    st.stop()

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(" + ",".join(map(str, selected_years)) + ")"


with st.container(border=True):
    st.subheader("🗓️ Heatmap Kepadatan Trip: Jam vs Hari")
    
    query_heatmap = f"""
        SELECT f.day_of_week, f.pickup_hour, COUNT(*) as total_trips
        FROM fact_trips f
        WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
        GROUP BY f.day_of_week, f.pickup_hour
    """
    df_heat = con.execute(query_heatmap).df()

    if not df_heat.empty:
        hari_map = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Minggu"}
        df_heat['Nama Hari'] = df_heat['day_of_week'].map(hari_map)
        
        df_pivot = df_heat.pivot(index='Nama Hari', columns='pickup_hour', values='total_trips')
        df_pivot = df_pivot.reindex(["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])

        fig_heat = px.imshow(
            df_pivot,
            labels=dict(x="Jam Keberangkatan (Hour)", y="Hari dalam Seminggu", color="Jumlah Trip"),
            x=df_pivot.columns,
            y=df_pivot.index,
            color_continuous_scale='YlOrRd' 
        )
        fig_heat.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Data waktu perjalanan tidak ditemukan.")

st.markdown("---")


with st.container(border=True): 
    st.subheader("☀️ Dampak Suhu Cuaca terhadap Jumlah Perjalanan")
    
    query_weather = f"""
        SELECT w.temp_mean_c, COUNT(f.trip_id) as total_trips, w.weather_category
        FROM fact_trips f
        JOIN dim_weather w ON f.trip_date = w.date
        WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
        GROUP BY w.temp_mean_c, w.weather_category
    """
    df_weather = con.execute(query_weather).df()

    if not df_weather.empty:
        fig_scatter = px.scatter(
            df_weather,
            x='temp_mean_c',
            y='total_trips',
            color='weather_category',
            labels={'temp_mean_c': 'Rata-rata Suhu Harian (°C)', 'total_trips': 'Total Perjalanan', 'weather_category': 'Kondisi Cuaca'},
            title="Hubungan Suhu dan Kategori Cuaca terhadap Volume Pesanan",
            color_discrete_sequence=px.colors.qualitative.Safe, 
            hover_data={'temp_mean_c': ':.1f°C', 'total_trips': ':,'} 
        )
        fig_scatter.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Data korelasi cuaca tidak ditemukan.")

st.markdown("---")


with st.container(border=True):
    st.subheader("🇺🇸 Perbandingan Volume Perjalanan di Hari Libur (Holiday)")
    
    query_holiday = f"""
        SELECT t.is_holiday, COUNT(f.trip_id) as total_trips
        FROM fact_trips f
        JOIN dim_time t ON f.trip_date = t.date
        WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
        GROUP BY t.is_holiday
    """
    df_holiday = con.execute(query_holiday).df()

    if not df_holiday.empty:
        df_holiday['Status Hari'] = df_holiday['is_holiday'].map({True: 'Hari Libur Nasional', False: 'Hari Kerja Biasa'})
        
        fig_holiday = px.bar(
            df_holiday,
            x='Status Hari',
            y='total_trips',
            color='Status Hari',
            labels={'total_trips': 'Jumlah Perjalanan', 'Status Hari': 'Kategori Hari'},
            color_discrete_map=WARNA_HOLIDAY, 
            text_auto=':,' 
        )
        fig_holiday.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_holiday, use_container_width=True)
    else:
        st.info("Data hari libur tidak ditemukan.")

con.close()