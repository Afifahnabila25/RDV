import urllib.request
import zipfile
import geopandas as gpd
import csv
from pathlib import Path
import io

url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
print("Downloading taxi zones...")

with urllib.request.urlopen(url) as r:
    zip_data = r.read()

# Simpan zip dulu
with open("data/raw/taxi_zones.zip", "wb") as f:
    f.write(zip_data)

# Cek isi zip
with zipfile.ZipFile("data/raw/taxi_zones.zip") as z:
    print("Isi ZIP:", z.namelist())
    z.extractall("data/raw/taxi_zones/")

print("Extracting...")
with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
    z.extractall("data/raw/taxi_zones/")

print("Reading shapefile...")
gdf = gpd.read_file("data/raw/taxi_zones/taxi_zones/taxi_zones.shp")

# Hitung centroid tiap zona
gdf = gdf.to_crs(epsg=4326)  # konversi ke lat/lon
gdf["lat"] = gdf.geometry.centroid.y
gdf["lon"] = gdf.geometry.centroid.x

print(f"Total zona: {len(gdf)}")

# Simpan ke CSV
output = Path("data/raw/zone_coords.csv")
gdf[["LocationID", "lat", "lon"]].rename(columns={"LocationID": "location_id"}).to_csv(
    output, index=False
)
print(f"Tersimpan di {output}")
