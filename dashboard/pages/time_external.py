import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

WARNA_HOLIDAY = {
    "Hari Libur Nasional": "#F8B320",
    "Hari Kerja Biasa": "#4B7FF2"
}

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
    border-right:1px solid #E5E7EB !important;
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

button[kind="header"]{
    display:none !important;
}

</style>
""", unsafe_allow_html=True)

st.title("⏰ Time & External Factors Analysis")

st.markdown(
    """
    <p style='
    color:#6B7280;
    font-size:1rem;
    font-family:Poppins,sans-serif;
    margin-top:-0.5rem;
    margin-bottom:1.2rem;
    '>
    Analisis pengaruh waktu, cuaca harian, dan hari libur nasional terhadap operasional taksi.
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

st.subheader("🗓️ Heatmap Kepadatan Trip: Jam vs Hari")

query_heatmap = f"""
    SELECT
        f.day_of_week,
        f.pickup_hour,
        COUNT(*) as total_trips
    FROM fact_trips f
    WHERE f.taxi_type IN {taxi_str}
      AND YEAR(f.trip_date) IN {year_str}
    GROUP BY
        f.day_of_week,
        f.pickup_hour
"""

df_heat = con.execute(query_heatmap).df()

if not df_heat.empty:

    hari_map = {
        1: "Senin",
        2: "Selasa",
        3: "Rabu",
        4: "Kamis",
        5: "Jumat",
        6: "Sabtu",
        7: "Minggu"
    }

    df_heat["Nama Hari"] = df_heat["day_of_week"].map(hari_map)

    df_pivot = df_heat.pivot(
        index="Nama Hari",
        columns="pickup_hour",
        values="total_trips"
    )

    df_pivot = df_pivot.reindex([
        "Senin",
        "Selasa",
        "Rabu",
        "Kamis",
        "Jumat",
        "Sabtu",
        "Minggu"
    ])

    fig_heat = px.imshow(
        df_pivot,
        labels=dict(
            x="Jam Keberangkatan",
            y="Hari",
            color="Jumlah Trip"
        ),
        x=df_pivot.columns,
        y=df_pivot.index,
        color_continuous_scale=[
            [0, "#EEF2FF"],
            [0.5, "#4B7FF2"],
            [1, "#1E2A3A"]
        ]
    )

    fig_heat.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family="Poppins, sans-serif",
            color="#111827"
        )
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True
    )

else:

    st.info("Data waktu perjalanan tidak ditemukan.")

st.markdown(
    "<div style='height:0.5rem'></div>",
    unsafe_allow_html=True
)

col1, col2 = st.columns(2, gap="large")

with col1:

    st.subheader("☀️ Dampak Suhu Cuaca terhadap Perjalanan")

    query_weather = f"""
        SELECT
            w.temp_mean_c,
            COUNT(f.trip_id) as total_trips,
            w.weather_category
        FROM fact_trips f
        JOIN dim_weather w
            ON f.trip_date = w.date
        WHERE f.taxi_type IN {taxi_str}
          AND YEAR(f.trip_date) IN {year_str}
        GROUP BY
            w.temp_mean_c,
            w.weather_category
    """

    df_weather = con.execute(query_weather).df()

    if not df_weather.empty:

        fig_scatter = px.scatter(
            df_weather,
            x="temp_mean_c",
            y="total_trips",
            color="weather_category",
            labels={
                "temp_mean_c": "Rata-rata Suhu Harian (°C)",
                "total_trips": "Total Perjalanan",
                "weather_category": "Kondisi Cuaca"
            },
            color_discrete_sequence=[
                "#4B7FF2",
                "#F8B320",
                "#31C28E",
                "#7C53FA",
                "#46C6FA"
            ],
            hover_data={
                "temp_mean_c": ":.1f°C",
                "total_trips": ":,"
            }
        )

        fig_scatter.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
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
                gridcolor="#E5E7EB"
            )
        )

        st.caption(
            "Hubungan Suhu dan Kategori Cuaca terhadap Volume Pesanan"
        )

        st.plotly_chart(
            fig_scatter,
            use_container_width=True
        )

    else:

        st.info("Data korelasi cuaca tidak ditemukan.")

with col2:

    st.subheader("📊 Perbandingan Volume di Hari Libur")

    query_holiday = f"""
        SELECT
            t.is_holiday,
            COUNT(f.trip_id) as total_trips
        FROM fact_trips f
        JOIN dim_time t
            ON f.trip_date = t.date
        WHERE f.taxi_type IN {taxi_str}
          AND YEAR(f.trip_date) IN {year_str}
        GROUP BY t.is_holiday
    """

    df_holiday = con.execute(query_holiday).df()

    if not df_holiday.empty:

        df_holiday["Status Hari"] = df_holiday["is_holiday"].map({
            True: "Hari Libur Nasional",
            False: "Hari Kerja Biasa"
        })

        fig_holiday = px.bar(
            df_holiday,
            x="Status Hari",
            y="total_trips",
            color="Status Hari",
            labels={
                "total_trips": "Jumlah Perjalanan",
                "Status Hari": "Kategori Hari"
            },
            color_discrete_map=WARNA_HOLIDAY,
            text_auto=":,"
        )

        fig_holiday.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(
                family="Poppins, sans-serif",
                color="#111827"
            ),
            yaxis=dict(
                gridcolor="#E5E7EB"
            ),
            showlegend=False
        )

        st.plotly_chart(
            fig_holiday,
            use_container_width=True
        )

    else:

        st.info("Data hari libur tidak ditemukan.")

con.close()