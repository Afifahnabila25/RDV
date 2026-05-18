from pathlib import Path
import pandas as pd

DATA_RAW_EXTERNAL = Path("data/raw/external")
WEATHER_PARQUET = DATA_RAW_EXTERNAL / "weather.parquet"
HOLIDAYS_PARQUET = DATA_RAW_EXTERNAL / "holidays.parquet"


def read_weather() -> pd.DataFrame:
    if WEATHER_PARQUET.exists():
        return pd.read_parquet(WEATHER_PARQUET)
    raise FileNotFoundError(f"Weather file not found. Expected {WEATHER_PARQUET}.")


def read_holidays() -> pd.DataFrame:
    if HOLIDAYS_PARQUET.exists():
        return pd.read_parquet(HOLIDAYS_PARQUET)
    raise FileNotFoundError(f"Holidays file not found. Expected {HOLIDAYS_PARQUET}.")


# Weather
df_w = read_weather()
df_w["date"] = pd.to_datetime(df_w["date"])
df_w["precipitation_mm"] = df_w["precipitation_mm"].fillna(0)
df_w["temp_mean_c"] = df_w["temp_mean_c"].fillna(df_w["temp_mean_c"].median())
df_w["temp_max_c"] = df_w["temp_max_c"].fillna(df_w["temp_max_c"].median())
df_w["temp_min_c"] = df_w["temp_min_c"].fillna(df_w["temp_min_c"].median())
df_w["is_rainy"] = (df_w["precipitation_mm"] > 1.0).astype(int)
df_w["is_snowy"] = df_w["weathercode"].isin([71, 73, 75, 77, 85, 86]).astype(int)
df_w.to_parquet("data/clean/weather_clean.parquet", index=False)
print(f"[WEATHER] {len(df_w)} hari tersimpan")

# Holidays
df_h = read_holidays()
df_h["date"] = pd.to_datetime(df_h["date"])
df_h.to_parquet("data/clean/holidays_clean.parquet", index=False)
print(f"[HOLIDAYS] {len(df_h)} hari libur tersimpan")
