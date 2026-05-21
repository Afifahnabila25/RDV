import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
html, body, [class*="css"]{background:#ffffff !important;}
[data-testid="stAppViewContainer"]{background:#ffffff !important;}
[data-testid="stHeader"]{background:#ffffff !important;}
[data-testid="stToolbar"]{background:#ffffff !important;}
.main{background:#ffffff !important;}
.block-container{background:#ffffff !important;padding-top:1rem !important;padding-bottom:1rem !important;max-width:100% !important;}
section[data-testid="stSidebar"]{background:#ffffff !important;border-right:1px solid #e5e7eb !important;}
div[data-testid="stVerticalBlock"]{background:#ffffff !important;}
div[data-testid="stHorizontalBlock"]{background:#ffffff !important;}
div[data-testid="stPlotlyChart"]{background:#ffffff !important;border:none !important;box-shadow:none !important;}
div[data-testid="stMarkdownContainer"]{background:#ffffff !important;}
div[data-testid="stExpander"]{background:#ffffff !important;border:none !important;box-shadow:none !important;}
div[data-testid="stDataFrame"]{background:#ffffff !important;border:none !important;box-shadow:none !important;}
iframe{border-radius:12px !important;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🗺️ Revenue & Region Analysis")
st.markdown(
    "<p style='color:#6B7280;font-size:1rem;font-family:Poppins,sans-serif;margin-top:-0.5rem;margin-bottom:1.2rem;'>Analisis distribusi pendapatan dan pemetaan wilayah kepadatan taksi NYC.</p>",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

# ── Filter dari session_state ─────────────────────────────────────────────────
if "selected_taxis" in st.session_state and st.session_state["selected_taxis"]:
    selected_taxis = [
        t.lower().replace(" cab", "") for t in st.session_state["selected_taxis"]
    ]
else:
    selected_taxis = ["yellow", "green"]

if "selected_years" in st.session_state and st.session_state["selected_years"]:
    selected_years = st.session_state["selected_years"]
else:
    selected_years = [2024, 2025]

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(" + ",".join(map(str, selected_years)) + ")"

# ══════════════════════════════════════════════════════════════════════════════
# BARIS 1 — TOTAL PENDAPATAN PER WILAYAH + TOP 10 ZONA
# ══════════════════════════════════════════════════════════════════════════════
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("💰 Total Pendapatan per Wilayah")
    st.caption("Distribusi total pendapatan berdasarkan borough NYC.")
    try:
        df_borough = con.execute(f"""
            SELECT z.borough, SUM(f.total_amount) as total_revenue
            FROM fact_trips f
            JOIN dim_location z ON f.PULocationID = z.location_id
            WHERE f.taxi_type IN {taxi_str}
              AND YEAR(f.trip_date) IN {year_str}
            GROUP BY z.borough
            ORDER BY total_revenue DESC
        """).df()
        df_borough.columns = [c.lower() for c in df_borough.columns]
        if not df_borough.empty:
            fig_borough = px.bar(
                df_borough,
                x="total_revenue",
                y="borough",
                orientation="h",
                labels={"total_revenue": "Total Pendapatan ($)", "borough": "Wilayah"},
                color="total_revenue",
                color_continuous_scale="Blues",
                text_auto="$.2s",
            )
            fig_borough.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(family="Poppins, sans-serif", color="#111827"),
                xaxis=dict(gridcolor="#E5E7EB"),
                yaxis=dict(autorange="reversed"),
                showlegend=False,
                height=350,
            )
            st.plotly_chart(fig_borough, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal memuat revenue borough: {e}")

with col2:
    st.subheader("🏆 Top 10 Zona Revenue Tertinggi")
    st.caption("Zona pickup dengan total pendapatan tertinggi.")
    try:
        df_top_zone = con.execute(f"""
            SELECT l.zone_name, l.borough,
                   SUM(f.total_amount) AS total_revenue,
                   COUNT(*) AS total_trips
            FROM fact_trips f
            JOIN dim_location l ON f.PULocationID = l.location_id
            WHERE f.taxi_type IN {taxi_str}
              AND YEAR(f.trip_date) IN {year_str}
            GROUP BY l.zone_name, l.borough
            ORDER BY total_revenue DESC
            LIMIT 10
        """).df()
        if not df_top_zone.empty:
            fig_top = px.bar(
                df_top_zone,
                x="total_revenue",
                y="zone_name",
                orientation="h",
                color="total_revenue",
                color_continuous_scale="Blues",
                labels={"total_revenue": "Total Revenue ($)", "zone_name": "Zona"},
                hover_data={"borough": True, "total_trips": ":,"},
                text_auto="$.2s",
            )
            fig_top.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(family="Poppins, sans-serif", color="#111827"),
                xaxis=dict(gridcolor="#E5E7EB"),
                showlegend=False,
                height=350,
            )
            st.plotly_chart(fig_top, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal memuat top zona: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BARIS 2 — PETA KEPADATAN FULL WIDTH
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🗺️ Peta Kepadatan Pickup NYC")
st.caption("Ukuran titik menunjukkan jumlah trip yang berangkat dari tiap zona.")
try:
    zone_coords_path = ROOT / "data" / "raw" / "zone_coords.csv"
    zone_coords = pd.read_csv(zone_coords_path)
    df_loc = con.execute(
        "SELECT location_id, zone_name, borough FROM dim_location"
    ).df()

    # Tentukan warna berdasarkan filter
    if len(selected_taxis) == 2:  # All
        map_color = "#4B7FF2"
    elif "yellow" in selected_taxis:
        map_color = "#F8B320"
    else:
        map_color = "#31C28E"

    df_map_data = con.execute(f"""
        SELECT f.PULocationID AS location_id, COUNT(*) as total_trips
        FROM fact_trips f
        WHERE f.taxi_type IN {taxi_str}
          AND YEAR(f.trip_date) IN {year_str}
        GROUP BY f.PULocationID
    """).df()

    df_geo = pd.merge(df_map_data, zone_coords, on="location_id", how="inner")
    df_geo = df_geo.merge(df_loc, on="location_id", how="left")

    if not df_geo.empty:
        fig_map = px.scatter_mapbox(
            df_geo,
            lat="lat",
            lon="lon",
            size="total_trips",
            hover_name="zone_name",
            hover_data={"borough": True, "total_trips": ":,"},
            zoom=9.5,
            mapbox_style="carto-positron",
        )
        fig_map.update_traces(marker=dict(color=map_color))
        fig_map.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(family="Poppins, sans-serif", color="#111827"),
            height=500,
        )
        st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={"scrollZoom": True, "displayModeBar": False},
        )
except Exception as e:
    st.error(f"Gagal memuat peta: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BARIS 3 — REVENUE PER TRIP + RATA-RATA JARAK
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🚕 Revenue per Trip: Yellow vs Green")
st.caption("Perbandingan rata-rata pendapatan per perjalanan antar jenis taksi.")
try:
    df_ygrev = con.execute(f"""
        SELECT taxi_type,
               ROUND(AVG(total_amount), 2) AS avg_revenue_per_trip,
               ROUND(AVG(trip_distance), 2) AS avg_distance
        FROM fact_trips
        WHERE taxi_type IN {taxi_str}
          AND YEAR(trip_date) IN {year_str}
        GROUP BY taxi_type
    """).df()
    if not df_ygrev.empty:
        df_ygrev["Jenis Taksi"] = df_ygrev["taxi_type"].map(
            {"yellow": "Yellow Cab", "green": "Green Cab"}
        )
        col5, col6 = st.columns([1, 1], gap="large")
        with col5:
            fig_yg = px.bar(
                df_ygrev,
                x="Jenis Taksi",
                y="avg_revenue_per_trip",
                color="Jenis Taksi",
                color_discrete_map={"Yellow Cab": "#F8B320", "Green Cab": "#31C28E"},
                labels={"avg_revenue_per_trip": "Avg Revenue ($)"},
                text_auto=".2f",
            )
            fig_yg.update_layout(
                title="Rata-rata Revenue per Trip",
                margin=dict(t=30, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(family="Poppins, sans-serif", color="#111827"),
                yaxis=dict(gridcolor="#E5E7EB"),
                showlegend=False,
                height=300,
            )
            st.plotly_chart(
                fig_yg, use_container_width=True, config={"displayModeBar": False}
            )
        with col6:
            fig_dist = px.bar(
                df_ygrev,
                x="Jenis Taksi",
                y="avg_distance",
                color="Jenis Taksi",
                color_discrete_map={"Yellow Cab": "#F8B320", "Green Cab": "#31C28E"},
                labels={"avg_distance": "Avg Jarak (mil)"},
                text_auto=".2f",
            )
            fig_dist.update_layout(
                title="Rata-rata Jarak Perjalanan",
                margin=dict(t=30, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(family="Poppins, sans-serif", color="#111827"),
                yaxis=dict(gridcolor="#E5E7EB"),
                showlegend=False,
                height=300,
            )
            st.plotly_chart(
                fig_dist, use_container_width=True, config={"displayModeBar": False}
            )
except Exception as e:
    st.error(f"Gagal memuat perbandingan Yellow vs Green: {e}")

con.close()
