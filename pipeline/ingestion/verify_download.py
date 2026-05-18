import pandas as pd
import glob
from pathlib import Path

print("=" * 50)
print("VERIFIKASI HASIL DOWNLOAD TLC DATA")
print("=" * 50)

# ── 1. Hitung jumlah file ──────────────────────────
yellow_files = sorted(glob.glob('data/raw/yellow/*.parquet'))
green_files  = sorted(glob.glob('data/raw/green/*.parquet'))

print(f"\n[1] JUMLAH FILE")
print(f"    Yellow : {len(yellow_files)} file")
print(f"    Green  : {len(green_files)} file")

# ── 2. List semua file yang ada ────────────────────
print(f"\n[2] DAFTAR FILE YELLOW")
for f in yellow_files:
    size_mb = Path(f).stat().st_size / (1024 * 1024)
    print(f"    {Path(f).name}  ({size_mb:.1f} MB)")

print(f"\n[3] DAFTAR FILE GREEN")
for f in green_files:
    size_mb = Path(f).stat().st_size / (1024 * 1024)
    print(f"    {Path(f).name}  ({size_mb:.1f} MB)")

# ── 3. Cek sampel isi file ─────────────────────────
print(f"\n[4] CEK SAMPEL FILE")

for label, files in [("Yellow", yellow_files), ("Green", green_files)]:
    if not files:
        print(f"    [{label}] Tidak ada file ditemukan!")
        continue

    sample = files[0]
    df = pd.read_parquet(sample)
    print(f"\n    [{label}] {Path(sample).name}")
    print(f"    Jumlah baris  : {len(df):,}")
    print(f"    Jumlah kolom  : {len(df.columns)}")
    print(f"    Kolom         : {df.columns.tolist()}")
    print(f"    Sampel 3 baris:")
    print(df.head(3).to_string(index=False))

print("\n" + "=" * 50)
print("Verifikasi selesai!")
print("=" * 50)