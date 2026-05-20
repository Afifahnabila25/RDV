import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

html, body, [class*="css"]{
    background:#ffffff !important;
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
    border-right:1px solid #e5e7eb !important;
}

div[data-testid="stVerticalBlock"]{
    background:#ffffff !important;
}

div[data-testid="stHorizontalBlock"]{
    background:#ffffff !important;
}

div[data-testid="stPlotlyChart"]{
    background:#ffffff !important;
    border:none !important;
    box-shadow:none !important;
}

div[data-testid="stMarkdownContainer"]{
    background:#ffffff !important;
}

div[data-testid="stExpander"]{
    background:#ffffff !important;
    border:none !important;
    box-shadow:none !important;
}

div[data-testid="stDataFrame"]{
    background:#ffffff !important;
    border:none !important;
    box-shadow:none !important;
}

iframe{
    border-radius:12px !important;
}

</style>
""", unsafe_allow_html=True)

st.title("🗺️ Revenue & Region Analysis")

st.markdown(
    """
    <p style='color:#6B7280;
    font-size:1rem;
    font-family:Poppins,sans-serif;
    margin-top:-0.5rem;
    margin-bottom:1.2rem;'>
    Analisis distribusi pendapatan dan pemetaan wilayah kepadatan taksi NYC.
    </p>
    """,
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

if 'selected_taxis' in st.session_state and st.session_state['selected_taxis']:
    selected_taxis = [
        t.lower().replace(' cab', '')
        for t in st.session_state['selected_taxis']
    ]
else:
    selected_taxis = ['yellow', 'green']

if 'selected_years' in st.session_state and st.session_state['selected_years']:
    selected_years = st.session_state['selected_years']
else:
    selected_years = [2024, 2025]

taxi_str = "('" + "','".join(selected_taxis) + "')"
year_str = "(" + ",".join(map(str, selected_years)) + ")"

col1, col2 = st.columns([1,1], gap="large")

with col1:

    st.subheader("🗺️ Peta Kepadatan Destinasi NYC")

    st.caption(
        "Arahkan kursor ke peta lalu gunakan scroll mouse / trackpad untuk zoom langsung."
    )

    try:

        query_map = f"""
            SELECT
                f.DOLocationID,
                COUNT(*) as total_trips
            FROM fact_trips f
            WHERE f.taxi_type IN {taxi_str}
              AND YEAR(f.trip_date) IN {year_str}
            GROUP BY f.DOLocationID
        """

        df_map_data = con.execute(query_map).df()

        df_map_data.columns = [
            col.lower()
            for col in df_map_data.columns
        ]

        default_coords = {
            "locationid": [1,3,4,7,10,13,14,24,25,33,41,42,43,48,50,74,75,79,132,138,140,141,142,143,161,162,163,164,170,181,230,234,236,237,238,239],
            "borough": ["EWR","Bronx","Manhattan","Queens","Queens","Manhattan","Brooklyn","Manhattan","Brooklyn","Brooklyn","Manhattan","Manhattan","Manhattan","Manhattan","Staten Island","Manhattan","Manhattan","Manhattan","Queens","Queens","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Brooklyn","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan","Manhattan"],
            "zone": ["Newark Airport","Allerton/Pelham Gardens","Alphabet City","Astoria","Baisley Park","Battery Park","Bay Ridge","Bloomingdale","Boerum Hill","Brooklyn Heights","Central Harlem","Central Harlem North","Central Park","Clinton East","Charleston/Tottenville","East Harlem North","East Harlem South","East Village","JFK Airport","LaGuardia Airport","Lenox Hill East","Lenox Hill West","Lincoln Square East","Lincoln Square West","Midtown Center","Midtown East","Midtown North","Midtown South","Murray Hill","Park Slope","Times Square/Theater District","Union Square","Upper East Side North","Upper East Side South","Upper West Side North","Upper West Side South"],
            "latitude": [40.6895,40.8653,40.7260,40.7644,40.6771,40.7077,40.6260,40.7990,40.6853,40.6960,40.8079,40.8223,40.7829,40.7601,40.5110,40.8003,40.7905,40.7291,40.6413,40.7769,40.7641,40.7684,40.7731,40.7770,40.7562,40.7561,40.7621,40.7497,40.7479,40.6698,40.7580,40.7359,40.7781,40.7719,40.7912,40.7812],
            "longitude": [-74.1745,-73.8474,-73.9790,-73.9235,-73.7844,-74.0175,-74.0301,-73.9665,-73.9840,-73.9933,-73.9458,-73.9390,-73.9654,-73.9912,-74.2403,-73.9348,-73.9427,-73.9866,-73.7781,-73.8740,-73.9567,-73.9602,-73.9818,-73.9865,-73.9785,-73.9715,-73.9786,-73.9842,-73.9757,-73.9805,-73.9855,-73.9904,-73.9542,-73.9588,-73.9729,-73.9772]
        }

        df_coords = pd.DataFrame(default_coords)

        df_geo = pd.merge(
            df_map_data,
            df_coords,
            left_on="dolocationid",
            right_on="locationid",
            how="inner"
        )

        if not df_geo.empty:

            fig_map = px.scatter_mapbox(
                df_geo,
                lat="latitude",
                lon="longitude",
                size="total_trips",
                color="total_trips",
                color_continuous_scale="Viridis",
                hover_name="zone",
                hover_data={
                    "borough": True,
                    "total_trips": ":,"
                },
                zoom=9.5,
                mapbox_style="carto-positron"
            )

            fig_map.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(
                    family="Poppins, sans-serif",
                    color="#111827"
                ),
                height=450
            )

            st.plotly_chart(
                fig_map,
                use_container_width=True,
                config={
                    "scrollZoom": True,
                    "displayModeBar": False
                }
            )

        else:

            st.info("Data wilayah belum tersedia.")

    except Exception as e:

        st.error(f"Gagal memuat peta: {e}")

with col2:

    st.subheader("💰 Total Pendapatan per Wilayah")

    st.caption(
        "Distribusi total pendapatan berdasarkan borough NYC."
    )

    try:

        query_borough = f"""
            SELECT
                z.borough,
                SUM(f.total_amount) as total_revenue
            FROM fact_trips f
            JOIN dim_location z
                ON f.DOLocationID = z.location_id
            WHERE f.taxi_type IN {taxi_str}
              AND YEAR(f.trip_date) IN {year_str}
            GROUP BY z.borough
            ORDER BY total_revenue DESC
        """

        df_borough = con.execute(query_borough).df()

        if not df_borough.empty:

            df_borough.columns = [
                col.lower()
                for col in df_borough.columns
            ]

            fig_borough = px.bar(
                df_borough,
                x="total_revenue",
                y="borough",
                orientation="h",
                labels={
                    "total_revenue": "Total Pendapatan ($)",
                    "borough": "Wilayah"
                },
                color="total_revenue",
                color_continuous_scale="Blues",
                text_auto="$.2s"
            )

            fig_borough.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(
                    family="Poppins, sans-serif",
                    color="#111827"
                ),
                xaxis=dict(
                    gridcolor="#E5E7EB"
                ),
                yaxis=dict(
                    autorange="reversed"
                ),
                showlegend=False,
                height=450
            )

            st.plotly_chart(
                fig_borough,
                use_container_width=True
            )

        else:

            st.info("Data pendapatan tidak ditemukan.")

    except Exception as e:

        st.error(f"Gagal memuat revenue borough: {e}")

con.close()