import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

WARNA_HOLIDAY = {"Hari Libur Nasional": "#F8B320", "Hari Kerja Biasa": "#4B7FF2"}

st.markdown("""
    <style>
    div[data-testid="stBlock"] div[data-testid="element-container"] button {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⏰ Time & External Factors Analysis")
st.markdown(
    "<p style='color:#6B7280;font-size:1rem;font-family:Poppins,sans-serif;margin-top:-0.5rem;margin-bottom:1.2rem;'>Analisis pengaruh waktu, cuaca harian, dan hari libur nasional terhadap operasional taksi.</p>",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "final" / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

if 'selected_taxis' in st.session_state and st.session_state['selected_taxis']:
    selected_taxis = st.session_state['selected_taxis']
else:
    selected_taxis = ['yellow', 'green']

if 'selected_years' in st.session_state and st.session_state['selected_years']:
    selected_years = st.session_state['selected_years']
else:
    selected_years = [2024, 2025]

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
        hari_map = {
            1: "Senin", 2: "Selasa", 3: "Rabu", 
            4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Minggu"
        }
        df_heat["Nama Hari"] = df_heat["day_of_week"].map(hari_map)
        df_pivot = df_heat.pivot(index="Nama Hari", columns="pickup_hour", values="total_trips")
        df_pivot = df_pivot.reindex(["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])

        fig_heat = px.imshow(
            df_pivot,
            labels=dict(x="Jam Keberangkatan (Hour)", y="Hari dalam Seminggu", color="Jumlah Trip"),
            x=df_pivot.columns,
            y=df_pivot.index,
            color_continuous_scale=[
                [0, "#EEF2FF"],
                [0.5, "#4B7FF2"],
                [1, "#1E2A3A"],
            ],
        )
        fig_heat.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Poppins, sans-serif"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Data waktu perjalanan tidak ditemukan.")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="small")

with col1:
    with st.container(border=True):
        st.subheader("☀️ Dampak Suhu Cuaca terhadap Perjalanan")

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
                x="temp_mean_c",
                y="total_trips",
                color="weather_category",
                labels={
                    "temp_mean_c": "Rata-rata Suhu Harian (°C)",
                    "total_trips": "Total Perjalanan",
                    "weather_category": "Kondisi Cuaca",
                },
                color_discrete_sequence=["#4B7FF2", "#F8B320", "#31C28E", "#7C53FA", "#46C6FA"],
                hover_data={"temp_mean_c": ":.1f°C", "total_trips": ":,"},
            )
            fig_scatter.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Poppins, sans-serif"),
                xaxis=dict(gridcolor="#F0F2F5"),
                yaxis=dict(gridcolor="#F0F2F5"),
            )
            st.caption("Hubungan Suhu dan Kategori Cuaca terhadap Volume Pesanan")
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Data korelasi cuaca tidak ditemukan.")

with col2:
    with st.container(border=True):
        st.subheader("📊 Perbandingan Volume di Hari Lib")

        query_holiday = f"""
            SELECT t.is_holiday, COUNT(f.trip_id) as total_trips
            FROM fact_trips f
            JOIN dim_time t ON f.trip_date = t.date
            WHERE f.taxi_type IN {taxi_str} AND YEAR(f.trip_date) IN {year_str}
            GROUP BY t.is_holiday
        """
        df_holiday = con.execute(query_holiday).df()

        if not df_holiday.empty:
            df_holiday["Status Hari"] = df_holiday["is_holiday"].map(
                {True: "Hari Libur Nasional", False: "Hari Kerja Biasa"}
            )
            fig_holiday = px.bar(
                df_holiday,
                x="Status Hari",
                y="total_trips",
                color="Status Hari",
                labels={"total_trips": "Jumlah Perjalanan", "Status Hari": "Kategori Hari"},
                color_discrete_map=WARNA_HOLIDAY,
                text_auto=":,",
            )
            fig_holiday.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Poppins, sans-serif"),
                yaxis=dict(gridcolor="#F0F2F5"),
                showlegend=False,
            )
            st.plotly_chart(fig_holiday, use_container_width=True)
        else:
            st.info("Data hari libur tidak ditemukan.")

con.close()