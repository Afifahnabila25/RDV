# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(
    page_title="NYC Taxi Analysis | Kelompok 4",
    page_icon="🚕",
    layout="wide",
)

# ── CSS GLOBAL (berlaku ke semua halaman) ─────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');

html, body, .stApp {
    font-family: 'Poppins', sans-serif !important;
    background-color: #EAECF0 !important;
}
.main .block-container {
    background-color: #EAECF0 !important;
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #DDE1E8 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown {
    font-family: 'Poppins', sans-serif !important;
}

/* Card putih — semua border container */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
    border: 1px solid #E2E6ED !important;
    box-shadow: none !important;
    padding: 1.25rem 1.25rem !important;
}
/* Nested border container (di dalam card) — hilangkan border ganda */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
[data-testid="stVerticalBlock"] {
    background-color: #FFFFFF !important;
}

/* KPI card custom */
.kpi-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E6ED;
    padding: 1.1rem 1.25rem;
    width: 100%;
    box-sizing: border-box;
    box-shadow: none;
}
.kpi-label {
    font-family: 'Poppins', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.35rem;
}
.kpi-value {
    font-family: 'Poppins', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: #1E2A3A;
    line-height: 1.15;
    margin: 0;
}

/* Typography */
h1 {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 700 !important;
    color: #1E2A3A !important;
    font-size: 1.5rem !important;
}
h2, h3 {
    font-family: 'Poppins', sans-serif !important;
    color: #1E2A3A !important;
}
.stMarkdown h3,
[data-testid="stHeading"] h3 {
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #1E2A3A !important;
}
p, div {
    font-family: 'Poppins', sans-serif !important;
}

/* Icon font */
[data-testid="stIcon"],
[data-testid="stIcon"] span,
span.material-symbols-outlined,
span.material-icons {
    font-family: 'Material Symbols Outlined' !important;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

/* Multiselect tag */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background-color: #4B7FF2 !important;
    border-radius: 6px !important;
}

/* Divider & scrollbar */
hr { border-color: #E2E6ED !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #C1C8D4; border-radius: 3px; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Filter Global (Sidebar) ───────────────────────────────────────────────────
# ── Filter Global (Sidebar) ───────────────────────────────────────────────────
st.sidebar.title("Filter Dashboard")

taxi_options = {"Yellow Cab": "yellow", "Green Cab": "green"}
selected_taxi_labels = st.sidebar.multiselect(
    "Jenis Taksi",
    options=list(taxi_options.keys()),
    default=list(taxi_options.keys()),
    key="global_taxi",
)

selected_taxis = [taxi_options[l] for l in selected_taxi_labels]

# Simpan KEDUA format — taxi_str untuk halaman lain, selected_taxis untuk overview
st.session_state["taxi_str"]      = "('" + "','".join(selected_taxis) + "')"
st.session_state["selected_taxis"] = selected_taxis

# Tahun hardcode 2025 — tidak perlu filter
st.session_state["year_str"]       = "(2025)"
st.session_state["selected_years"] = [2025]

if not selected_taxi_labels:
    st.warning("Pilih minimal satu Jenis Taksi.")
    st.stop()
    
# ── Navigasi ──────────────────────────────────────────────────────────────────
pg = st.navigation(
    [
        st.Page("dashboard/pages/overview.py",       title="Overview"),
        st.Page("dashboard/pages/prediction.py",     title="Prediction"),
        st.Page("dashboard/pages/revenue_region.py", title="Revenue & Region"),
        st.Page("dashboard/pages/time_external.py",  title="Time & External"),
    ]
)
pg.run()