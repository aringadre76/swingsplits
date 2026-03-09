from pybaseball import statcast, cache, playerid_reverse_lookup
import pandas as pd
import os

os.makedirs("statcast_data", exist_ok=True)
cache.enable()

YEARS = [2023, 2024, 2025, 2026]

for year in YEARS:
    outpath = f"statcast_data/hitters_{year}.csv"
    if os.path.exists(outpath):
        print(f"hitters_{year}.csv already exists, skipping.")
        continue
    print(f"Downloading Statcast {year}...")
    # 2026: spring training only (through early April)
    if year == 2026:
        start_dt, end_dt = "2026-02-15", "2026-04-01"
    else:
        start_dt, end_dt = f"{year}-03-01", f"{year}-11-01"
    df = statcast(start_dt=start_dt, end_dt=end_dt)
    if df is None or df.empty:
        print(f"  No data for {year}, skipping.")
        continue
    batter_ids = df["batter"].dropna().astype(int).unique().tolist()
    if not batter_ids:
        print(f"  No batter IDs for {year}, skipping.")
        continue
    print(f"  Looking up {len(batter_ids)} batter names...")
    lookup = playerid_reverse_lookup(batter_ids, key_type="mlbam")
    if lookup is None or lookup.empty:
        df["batter_name"] = df["batter"].astype(str)
    else:
        lookup["batter_name"] = lookup["name_last"] + ", " + lookup["name_first"]
        id_to_name = lookup.set_index("key_mlbam")["batter_name"].to_dict()
        df["batter_name"] = df["batter"].map(
            lambda x: id_to_name.get(int(x), str(int(x)) if pd.notna(x) else "")
        )
    df.to_csv(outpath, index=False)
    print(f"  Saved {len(df)} rows to {outpath}")

print("Done.")
