import duckdb
con = duckdb.connect("data/final/warehouse.duckdb", read_only=True)

print("=== TABEL ===")
print(con.execute("SHOW TABLES").df().to_string())

print("\n=== dim_location (10 baris) ===")
print(con.execute("SELECT * FROM dim_location LIMIT 10").df().to_string())

print("\n=== fact_trips (5 baris) ===")
print(con.execute("SELECT * FROM fact_trips LIMIT 5").df().to_string())