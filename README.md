# Swingsplits

Bat speed and swing length splits by count situation, powered by Statcast data.

Live site: [swingsplits.vercel.app](http://swingsplits.vercel.app/)

## Prerequisites

- Bun installed locally
- Statcast CSVs for the seasons you care about in `statcast_data/` named `hitters_YYYY.csv`

## Install dependencies

```bash
bun install
```

## Download hitter-centric Statcast data (optional)

```bash
python3 scripts/download_batters_with_names.py
```

Fetches Statcast data per season via pybaseball, adds a `batter_name` column (Last, First) so aggregates are per hitter, and writes `statcast_data/hitters_YYYY.csv` for each year. Run this whenever you want to refresh or add seasons.

## Precompute hitter aggregates

```bash
bun run precompute
```

This scans `statcast_data/hitters_*.csv` (or falls back to `batters_*.csv` if no hitters files exist), builds per-hitter, per-season, and career aggregates by count bucket, and writes:

- `data/hitter_aggregates.json`
- `data/meta.json`

You must run this step whenever you add new CSVs.

## Run the app in development

```bash
bun run dev
```

Then open the printed URL in your browser. The app lets you:

- Search for any hitter by name
- Filter by season or view a career average
- See bat speed and swing length by count bucket with red and green deltas and sample sizes

## Production

```bash
bun run start
```

