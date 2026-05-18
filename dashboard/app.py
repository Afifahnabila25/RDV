# konfigurasi halaman, koneksi database, sidebar filter, dan navigasi antar halaman

import streamlit as st
import duckdb, pandas as pd

st.set_page_config(
    page_title='NYC Taxi Analysis | Kelompok 4',
    page_icon='🚕',
    layout='wide'
)

# Koneksi database (shared, read-only)
@st.cache_resource
def get_con():
    return duckdb.connect('data/final/warehouse.duckdb',
                          read_only=True)

# Fungsi load data dari view (bisa dipakai Gladys juga)
@st.cache_data
def load_view(view_name, filters=''):
    con = get_con()
    return con.execute(f'SELECT * FROM {view_name} {filters}').df()

# Sidebar filter
st.sidebar.title('Filter Dashboard')
taxi_filter = st.sidebar.multiselect(
    'Jenis Taksi', ['yellow', 'green'],
    default=['yellow', 'green']
)
year_filter = st.sidebar.multiselect(
    'Tahun', [2023, 2024, 2025, 2026],
    default=[2023, 2024, 2025, 2026]
)

# Navigasi halaman
page = st.sidebar.radio('Halaman', [
    'Overview',
    'Revenue & Region',
    'Time & External'
])

if page == 'Overview':
    exec(open('dashboard/pages/overview.py').read())
elif page == 'Revenue & Region':
    exec(open('dashboard/pages/revenue_region.py').read())
else:
    exec(open('dashboard/pages/time_external.py').read())