import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

WARNA_TAKSI = {"Yellow Cab": "#F8B320", "Green Cab": "#31C28E"}
WARNA_TREN = ["#4B7FF2"]

st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
    }
    div[data-testid="stBlock"] div[data-testid="element-container"] button {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

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

if 'selected_taxis' in st.session_state and st.session_state['selected_taxis']:
    selected_taxis = st.session_state['selected_taxis']
else:
    selected_taxis = ['yellow', 'green']

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(2025)"

trip_parts = []
rev_parts = []
if "yellow" in selected_taxis:
    trip_parts.append("SUM(yellow_trips)")
    rev_parts.append("SUM(yellow_revenue)")
if "green" in selected_taxis:
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
    with st.container(border=True):
        st.markdown("<small style='color:gray;'>🚗 TOTAL TRIP CARRIED</small>", unsafe_allow_html=True)
        st.header(f"{total_trips:,}")
with col2:
    with st.container(border=True):
        st.markdown("<small style='color:gray;'>💰 TOTAL GROSS REVENUE</small>", unsafe_allow_html=True)
        st.header(f"${total_revenue:,.2f}")
with col3:
    with st.container(border=True):
        st.markdown("<small style='color:gray;'>💵 TOTAL DRIVER TIPS</small>", unsafe_allow_html=True)
        st.header(f"${total_tips:,.2f}")
with col4:
    with st.container(border=True):
        st.markdown("<small style='color:gray;'>⚡ AVG REV / TRIP</small>", unsafe_allow_html=True)
        st.header(f"${avg_rev_per_trip:,.2f}")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

col_left, col_right = st.columns([1.2, 1.8], gap="small")

with col_left:
    with st.container(border=True): 
        st.markdown("### 📊 Market Share")
        st.caption("Proporsi kontribusi pendapatan armada aktif (2025)")
        
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
                hole=0.5,
                color='Jenis Taksi',
                color_discrete_map=WARNA_TAKSI  
            )
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=10, b=10, l=10, r=10),
                height=320,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("Pilih jenis taksi untuk melihat kontribusi.")

with col_right:
    with st.container(border=True):  
        st.markdown("### 📈 Revenue Growth")
        st.caption("Akumulasi performa tren pendapatan berkala (2025)")

        query_monthly = f"""
            SELECT 
                year, 
                month,
                SUM(CASE WHEN 'yellow' IN {taxi_str} THEN yellow_revenue ELSE 0 END +
                    CASE WHEN 'green' IN {taxi_str} THEN green_revenue ELSE 0 END) as revenue
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
                labels={'revenue': 'Revenue ($)', 'Periode': 'Bulan'},
                text_auto='.2s',
                color_discrete_sequence=WARNA_TREN  
            )
            fig_monthly.update_layout(
                margin=dict(t=20, b=10, l=10, r=10),
                height=320,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("Data bulanan tidak ditemukan.")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

with st.container(border=True): 
    st.markdown("### ℹ️ Fleet Metadata")
    st.caption("Detail klasifikasi operasional dan wilayah jangkauan resmi")
    try:
        df_taxi_info = con.execute("SELECT taxi_type AS 'Tipe', description AS 'Deskripsi', coverage_area AS 'Cakupan Wilayah' FROM dim_taxi_type").df()
        df_taxi_info['Tipe'] = df_taxi_info['Tipe'].str.upper()
        st.dataframe(df_taxi_info, use_container_width=True, hide_index=True)
    except:
        st.info("Gagal memuat info tabel dimensi jenis taksi.")

con.close()