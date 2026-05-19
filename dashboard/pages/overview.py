import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(layout="wide")

st.title("🚖 NYC Taxi Operations — Executive Overview")
st.markdown("Ringkasan Eksekutif Kinerja Operasional dan Pendapatan Armada Taxi New York City.")

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)

try:
    con = get_connection()
except Exception as e:
    st.error(f"Gagal terhubung ke database. Pastikan data warehouse sudah siap. Error: {e}")
    st.stop()

st.sidebar.header("Filter Global")
taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect("Jenis Taksi", options=list(taxi_options.keys()), default=list(taxi_options.keys()), key="ov_taxi")
selected_taxis = [taxi_options[lbl] for lbl in selected_taxi_labels]

try:
    available_years = [int(r[0]) for r in con.execute("SELECT DISTINCT year FROM dim_time ORDER BY year").fetchall() if r[0] is not None]
except:
    available_years = [2023, 2024, 2025, 2026]
selected_years = st.sidebar.multiselect("Tahun", options=available_years, default=available_years[:2], key="ov_year")

if not selected_taxis or not selected_years:
    st.warning("Silakan pilih minimal satu Jenis Taksi dan satu Tahun pada sidebar.")
    st.stop()

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(" + ",".join(map(str, selected_years)) + ")"

trip_parts = []
rev_parts = []
if 'yellow' in selected_taxis:
    trip_parts.append("SUM(yellow_trips)")
    rev_parts.append("SUM(yellow_revenue)")
if 'green' in selected_taxis:
    trip_parts.append("SUM(green_trips)")
    rev_parts.append("SUM(green_revenue)")

trip_logic = " + ".join(trip_parts) if trip_parts else "0"
rev_logic = " + ".join(rev_parts) if rev_parts else "0"

query_kpi = f"""
    SELECT 
        COALESCE({trip_logic}, 0) as total_trips,
        COALESCE({rev_logic}, 0) as total_revenue,
        SUM(total_tip) as total_tips
    FROM agg_revenue_daily
    WHERE year IN {year_str}
"""
kpi_data = con.execute(query_kpi).fetchone()

total_trips = kpi_data[0] if kpi_data else 0
total_revenue = kpi_data[1] if kpi_data else 0
total_tips = kpi_data[2] if kpi_data else 0
avg_rev_per_trip = (total_revenue / total_trips) if total_trips > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Perjalanan", f"{total_trips:,}")
with col2:
    st.metric("Total Pendapatan", f"${total_revenue:,.2f}")
with col3:
    st.metric("Total Tip Pengemudi", f"${total_tips:,.2f}")
with col4:
    st.metric("Rata-rata Pendapatan / Trip", f"${avg_rev_per_trip:,.2f}")

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Kontribusi Jumlah Trip & Pendapatan")
    
    query_share = f"""
        SELECT 
            SUM(yellow_trips) as yellow_total_trips,
            SUM(green_trips) as green_total_trips,
            SUM(yellow_revenue) as yellow_total_revenue,
            SUM(green_revenue) as green_total_revenue
        FROM agg_revenue_daily
        WHERE year IN {year_str}
    """
    share_data = con.execute(query_share).fetchone()
    
    shares = []
    if 'yellow' in selected_taxis and share_data:
        shares.append({'Jenis Taksi': 'Yellow Cab', 'Trips': share_data[0], 'Revenue': share_data[2]})
    if 'green' in selected_taxis and share_data:
        shares.append({'Jenis Taksi': 'Green Cab', 'Trips': share_data[1], 'Revenue': share_data[3]})
    
    df_share = pd.DataFrame(shares)
    
    if not df_share.empty and df_share['Trips'].sum() > 0:
        fig_donut = px.pie(
            df_share, 
            values='Revenue', 
            names='Jenis Taksi', 
            hole=0.4,
            title="Pangsa Pasar Berdasarkan Pendapatan ($)",
            color='Jenis Taksi',
            color_discrete_map={'Yellow Cab': '#f1c40f', 'Green Cab': '#2ecc71'}
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Pilih jenis taksi untuk melihat kontribusi.")

with col_right:
    st.subheader("📈 Akumulasi Pertumbuhan Pendapatan Bulanan")
    
    query_monthly = f"""
        SELECT 
            year, 
            month,
            SUM(total_trips) as trips,
            SUM(total_revenue) as revenue
        FROM agg_revenue_daily
        WHERE year IN {year_str}
        GROUP BY year, month
        ORDER BY year, month
    """
    df_monthly = con.execute(query_monthly).df()
    
    if not df_monthly.empty:
        df_monthly['Periode'] = df_monthly['year'].astype(str) + '-' + df_monthly['month'].astype(str).str.zfill(2)
        
        fig_monthly = px.bar(
            df_monthly,
            x='Periode',
            y='revenue',
            labels={'revenue': 'Total Pendapatan ($)', 'Periode': 'Bulan'},
            title="Tren Pendapatan Bulanan",
            text_auto='.2s'
        )
        fig_monthly.update_traces(marker_color='#34495e')
        st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.info("Data bulanan tidak ditemukan.")

st.markdown("---")
st.subheader("ℹ️ Informasi Wilayah Cakupan Armada")
try:
    df_taxi_info = con.execute("SELECT taxi_type AS 'Tipe', description AS 'Deskripsi', coverage_area AS 'Cakupan Wilayah' FROM dim_taxi_type").df()
    df_taxi_info['Tipe'] = df_taxi_info['Tipe'].str.upper()
    st.table(df_taxi_info)
except:
    st.info("Gagal memuat info tabel dimensi jenis taksi.")

con.close()