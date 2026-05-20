import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# COLOR PALETTE
WARNA_TAKSI = {"Yellow Cab": "#F8B320", "Green Cab": "#31C28E"}
WARNA_TREN = ["#4B7FF2"]

st.title("🚖 NYC Taxi Operations")
st.markdown(
    "<p style='color:#6B7280;font-size:1rem;font-family:Poppins,sans-serif;margin-top:-0.5rem;margin-bottom:1.2rem;'>Ringkasan Eksekutif Kinerja Operasional dan Pendapatan Armada Taxi New York City.</p>",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"


def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


try:
    con = get_connection()
except Exception as e:
    st.error(
        f"Gagal terhubung ke database. Pastikan data warehouse sudah siap. Error: {e}"
    )
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
taxi_str = st.session_state.get("taxi_str", "('yellow','green')")
year_str = st.session_state.get("year_str", "(2025)")
selected_taxis = [t.strip("'") for t in taxi_str.strip("()").split(",")]

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

col1, col2, col3, col4 = st.columns(4, gap="small")
kpi_items = [
    ("🚗 TOTAL TRIP CARRIED", f"{total_trips:,}"),
    ("💰 TOTAL GROSS REVENUE", f"${total_revenue:,.2f}"),
    ("💵 TOTAL DRIVER TIPS", f"${total_tips:,.2f}"),
    ("⚡ AVG REV / TRIP", f"${avg_rev_per_trip:,.2f}"),
]
for col, (label, value) in zip([col1, col2, col3, col4], kpi_items):
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

col_left, col_right = st.columns([1.2, 1.8], gap="small")

with col_left:
    with st.container(border=True, key="overview_market_share_card"):
        st.markdown("### 📊 Market Share")
        st.caption("Proporsi kontribusi pendapatan armada aktif")

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
        if "yellow" in selected_taxis and share_data:
            shares.append(
                {
                    "Jenis Taksi": "Yellow Cab",
                    "Trips": share_data[0],
                    "Revenue": share_data[2],
                }
            )
        if "green" in selected_taxis and share_data:
            shares.append(
                {
                    "Jenis Taksi": "Green Cab",
                    "Trips": share_data[1],
                    "Revenue": share_data[3],
                }
            )

        df_share = pd.DataFrame(shares)

        if not df_share.empty and df_share["Trips"].sum() > 0:
            fig_donut = px.pie(
                df_share,
                values="Revenue",
                names="Jenis Taksi",
                hole=0.5,
                color="Jenis Taksi",
                color_discrete_map=WARNA_TAKSI,
            )
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
                ),
                margin=dict(t=10, b=30, l=10, r=10),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Poppins, sans-serif", color="#1E2A3A"),
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("Pilih jenis taksi untuk melihat kontribusi.")

with col_right:
    with st.container(border=True, key="overview_revenue_growth_card"):
        st.markdown("### 📈 Revenue Growth")
        st.caption("Akumulasi performa tren pendapatan berkala")

        query_monthly = f"""
            SELECT 
                year, month,
                SUM(CASE WHEN 'yellow' IN {taxi_str} THEN yellow_revenue ELSE 0 END +
                    CASE WHEN 'green' IN {taxi_str} THEN green_revenue ELSE 0 END) as revenue
            FROM agg_revenue_daily
            WHERE year IN {year_str}
            GROUP BY year, month
            ORDER BY year, month
        """
        df_monthly = con.execute(query_monthly).df()

        if not df_monthly.empty:
            df_monthly["Periode"] = (
                df_monthly["year"].astype(str)
                + "-"
                + df_monthly["month"].astype(str).str.zfill(2)
            )
            fig_monthly = px.bar(
                df_monthly,
                x="Periode",
                y="revenue",
                labels={"revenue": "Revenue ($)", "Periode": "Bulan"},
                text_auto=".2s",
                color_discrete_sequence=WARNA_TREN,
            )
            fig_monthly.update_layout(
                margin=dict(t=20, b=10, l=10, r=10),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Poppins, sans-serif", color="#1E2A3A"),
                xaxis=dict(gridcolor="#F0F2F5", linecolor="#E2E6ED"),
                yaxis=dict(gridcolor="#F0F2F5", linecolor="#E2E6ED"),
            )
            fig_monthly.update_traces(marker_color="#4B7FF2")
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("Data bulanan tidak ditemukan.")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

with st.container(border=True, key="overview_fleet_metadata_card"):
    st.markdown("### ℹ️ Fleet Metadata")
    st.caption("Detail klasifikasi operasional dan wilayah jangkauan resmi")
    try:
        df_taxi_info = con.execute(
            "SELECT taxi_type AS 'Tipe', description AS 'Deskripsi', coverage_area AS 'Cakupan Wilayah' FROM dim_taxi_type"
        ).df()
        df_taxi_info["Tipe"] = df_taxi_info["Tipe"].str.upper()
        st.dataframe(df_taxi_info, use_container_width=True, hide_index=True)
    except:
        st.info("Gagal memuat info tabel dimensi jenis taksi.")

con.close()
