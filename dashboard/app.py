import streamlit as st
import duckdb
import pandas as pd

st.set_page_config(
    page_title='NYC Taxi Analysis | Kelompok 4',
    page_icon='🚕',
    layout='wide'
)

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

@st.cache_resource
def get_con():
    return duckdb.connect('data/final/warehouse.duckdb', read_only=True)

st.sidebar.title('Filter Dashboard')

taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect(
    'Jenis Taksi', 
    options=list(taxi_options.keys()), 
    default=list(taxi_options.keys()),
    key="global_taxi_select"
)

st.session_state['selected_taxis'] = [taxi_options[lbl] for lbl in selected_taxi_labels]

st.sidebar.markdown("---")

page = st.sidebar.radio('Halaman Navigasi', [
    'Overview',
    'Prediction',
    'Revenue & Region',
    'Time & External'
])

if not st.session_state['selected_taxis']:
    st.warning("Silakan pilih minimal satu Jenis Taksi pada sidebar.")
    st.stop()

if page == 'Overview':
    exec(open('dashboard/pages/overview.py', encoding='utf-8').read())
elif page == 'Prediction':
    exec(open('dashboard/pages/prediction.py', encoding='utf-8').read())
elif page == 'Revenue & Region':
    exec(open('dashboard/pages/revenue_region.py', encoding='utf-8').read())
else:
    exec(open('dashboard/pages/time_external.py', encoding='utf-8').read())