from pybaseball import statcast, cache
import pandas as pd
import os

os.makedirs("statcast_data", exist_ok=True)

cache.enable()

years = range(2023, 2026)

for year in years:
    filepath = f"statcast_data/batters_{year}.csv"
    if os.path.exists(filepath):
        print(f"{year} already exists, skipping.")
        continue
    print(f"Downloading {year}...")
    df = statcast(start_dt=f"{year}-03-01", end_dt=f"{year}-11-01")
    df.to_csv(filepath, index=False)
    print(f"  Saved {len(df)} rows to {filepath}")

print("Done.")
