import requests
import pandas as pd
from pathlib import Path

# ── Konfigurasi periode (sesuaikan dengan MONTHS di download_tlc.py) ──
START_DATE = '2025-01-01'
END_DATE   = '2025-12-31'
YEARS      = 2025

# ── Output folder ──
OUTPUT_DIR = Path('data/raw/external')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════
# 1. FETCH WEATHER — Open-Meteo Historical API
# ══════════════════════════════════════════════════
def fetch_weather():
    out = OUTPUT_DIR / 'weather.parquet'
    if out.exists():
        print('[SKIP] weather.parquet sudah ada')
        return

    print('[DOWNLOAD] Data cuaca harian NYC dari Open-Meteo...')

    url = 'https://archive-api.open-meteo.com/v1/archive'
    params = {
        'latitude': 40.7128,        # NYC
        'longitude': -74.0060,
        'start_date': START_DATE,
        'end_date': END_DATE,
        'daily': [
            'temperature_2m_mean',
            'precipitation_sum',
            'weathercode'
        ],
        'timezone': 'America/New_York'
    }

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame({
        'date':         data['daily']['time'],
        'temp_mean_c':  data['daily']['temperature_2m_mean'],
        'precipitation_mm': data['daily']['precipitation_sum'],
        'weathercode':  data['daily']['weathercode'],
    })
    df['date'] = pd.to_datetime(df['date'])

    df.to_parquet(out, index=False)
    print(f'[OK] {len(df):,} baris cuaca | weather.parquet')


# ══════════════════════════════════════════════════
# 2. FETCH HOLIDAYS — Nager.Date API
# ══════════════════════════════════════════════════
def fetch_holidays():
    out = OUTPUT_DIR / 'holidays.parquet'
    if out.exists():
        print('[SKIP] holidays.parquet sudah ada')
        return

    print('[DOWNLOAD] Data hari libur AS dari Nager.Date...')

    all_holidays = []
    for year in YEARS:
        url = f'https://date.nager.at/api/v3/PublicHolidays/{year}/US'
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        for h in r.json():
            all_holidays.append({
                'date': h['date'],
                'name': h['name'],
                'year': year
            })
        print(f'    [{year}] {len(r.json())} hari libur')

    df = pd.DataFrame(all_holidays)
    df['date'] = pd.to_datetime(df['date'])

    df.to_parquet(out, index=False)
    print(f'[OK] {len(df):,} total hari libur | holidays.parquet')


# ── Run langsung jika dieksekusi sendiri ──
if __name__ == '__main__':
    fetch_weather()
    fetch_holidays()