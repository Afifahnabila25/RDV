import requests, os, pandas as pd
from pathlib import Path

# Periode: Jan25-des25
MONTHS = {
    2025: range(1, 13),
}

COLS_YELLOW = [
    'tpep_pickup_datetime', 'tpep_dropoff_datetime',
    'PULocationID', 'DOLocationID', 'trip_distance',
    'fare_amount', 'tip_amount', 'total_amount',
    'payment_type', 'passenger_count'
]
COLS_GREEN = [
    'lpep_pickup_datetime', 'lpep_dropoff_datetime',
    'PULocationID', 'DOLocationID', 'trip_distance',
    'fare_amount', 'tip_amount', 'total_amount',
    'payment_type', 'passenger_count'
]

BASE_URL = 'https://d37ci6vzurychx.cloudfront.net/trip-data'

def download_parquet(taxi_type, year, month):
    fname = f'{taxi_type}_tripdata_{year}-{month:02d}.parquet'
    url   = f'{BASE_URL}/{fname}'
    folder = Path(f'data/raw/{taxi_type}')
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / fname

    if out.exists():
        print(f'[SKIP] {fname} sudah ada')
        return

    print(f'[DOWNLOAD] {url}')
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(out, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    # Column pruning - simpan hanya kolom yang dibutuhkan
    cols = COLS_YELLOW if taxi_type == 'yellow' else COLS_GREEN
    df = pd.read_parquet(out, columns=cols)
    df.to_parquet(out, index=False)
    print(f'[OK] {len(df):,} baris | {fname}')

if __name__ == '__main__':
    for year, months in MONTHS.items():
        for month in months:
            for taxi in ['yellow', 'green']:
                download_parquet(taxi, year, month)