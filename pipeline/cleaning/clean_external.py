import pandas as pd, json

# ── Weather ─────────────────────────────────────────────────────
df_w = pd.read_csv('data/raw/external/weather.csv')
df_w['date']          = pd.to_datetime(df_w['date'])
df_w['precipitation'] = df_w['precipitation'].fillna(0)
df_w['temp_max']      = df_w['temp_max'].fillna(df_w['temp_max'].median())
df_w['temp_min']      = df_w['temp_min'].fillna(df_w['temp_min'].median())
# Kategorisasi cuaca
df_w['is_rainy']  = (df_w['precipitation'] > 1.0).astype(int)
df_w['is_snowy']  = df_w['weathercode'].isin([71,73,75,77,85,86]).astype(int)
df_w.to_parquet('data/clean/weather_clean.parquet', index=False)
print(f'[WEATHER] {len(df_w)} hari tersimpan')

# ── Holidays ────────────────────────────────────────────────────
with open('data/raw/external/holidays.json') as f:
    holidays = json.load(f)
df_h = pd.DataFrame(holidays)
df_h['date'] = pd.to_datetime(df_h['date'])
df_h.to_parquet('data/clean/holidays_clean.parquet', index=False)
print(f'[HOLIDAYS] {len(df_h)} hari libur tersimpan')