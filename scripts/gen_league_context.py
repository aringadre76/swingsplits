#!/usr/bin/env python3
"""
gen_league_context.py

Reads data/hitter_aggregates.json and data/abs_2026.json and writes
data/league_context.json, which the frontend uses to display:

  1. Year-over-year league swing trends (2023-2026)
       – population averages, two-strike deltas, % shorteners/extenders
  2. Per-player 2026 percentile ranks
       – bat speed, two-strike bat-speed deceleration, two-strike length shortening
  3. 2026 league-wide ABS context
       – total challenges / overturns / walks / Ks avoided

Run:
    python3 scripts/gen_league_context.py
"""

import json
import os
import unicodedata
import re
from datetime import date

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.join(os.path.dirname(__file__), "..")
AGG_PATH  = os.path.join(BASE, "data", "hitter_aggregates.json")
ABS_PATH  = os.path.join(BASE, "data", "abs_2026.json")
OUT_PATH  = os.path.join(BASE, "data", "league_context.json")

# ---------------------------------------------------------------------------
# Thresholds  (match the frontend + analysis script)
# ---------------------------------------------------------------------------
MIN_ALL_SWINGS = 30   # minimum all-count swings to qualify
MIN_TS_SWINGS  = 20   # minimum two-strike swings to qualify for deltas
LEN_THRESH_FT  = 0.2  # swing-length delta threshold for shortener/extender
BAT_THRESH_MPH = 1.0  # bat-speed delta threshold

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def to_abs_key(raw: str) -> str:
    """Mirror of the frontend toAbsKey function."""
    trimmed = raw.strip()
    if "," in trimmed:
        parts = trimmed.split(",", 1)
        last  = parts[0].strip()
        first = parts[1].strip()
        trimmed = (first + " " + last) if (first and last) else (first or last)
    trimmed = strip_accents(trimmed)
    trimmed = re.sub(
        r"\s+(jr\.?|sr\.?|ii|iii|iv|v)\s*$", "", trimmed, flags=re.IGNORECASE
    ).strip()
    return trimmed.lower()


def safe_mean(vals: list) -> float | None:
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def pct_rank_desc(population: list[float], player_val: float | None) -> int | None:
    """
    Descending percentile: higher rank means MORE negative (more deceleration /
    more shortening).  Returns 0-100 integer.

    pct = fraction of population values that are GREATER than player_val, i.e.
    player_val is more negative than that fraction of the population.
    """
    if player_val is None or not population:
        return None
    count_above = sum(1 for v in population if v > player_val)
    return round(count_above / len(population) * 100)


def pct_rank_asc(population: list[float], player_val: float | None) -> int | None:
    """
    Ascending percentile: higher rank means LARGER value (faster bat speed).
    pct = fraction of population values that are LESS than player_val.
    """
    if player_val is None or not population:
        return None
    count_below = sum(1 for v in population if v < player_val)
    return round(count_below / len(population) * 100)


def round2(v: float | None) -> float | None:
    return round(v, 2) if v is not None else None


def round3(v: float | None) -> float | None:
    return round(v, 3) if v is not None else None


def round1(v: float | None) -> float | None:
    return round(v, 1) if v is not None else None

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
with open(AGG_PATH, encoding="utf-8") as f:
    agg: dict = json.load(f)

with open(ABS_PATH, encoding="utf-8") as f:
    abs_data: dict = json.load(f)

# ---------------------------------------------------------------------------
# 1.  Year-over-year league trends
# ---------------------------------------------------------------------------

league_trends: list[dict] = []

for year in ("2023", "2024", "2025", "2026"):
    bs_all_pop:     list[float] = []
    sl_all_pop:     list[float] = []
    ts_bat_deltas:  list[float] = []
    ts_len_deltas:  list[float] = []

    for player in agg.values():
        s = player.get("seasons", {}).get(year)
        if not s:
            continue

        buckets = s["buckets"]
        all_rec = buckets["all"]
        ts_rec  = buckets["two_strikes"]
        bs_all  = all_rec["batSpeed"]
        sl_all  = all_rec["swingLength"]
        bs_ts   = ts_rec["batSpeed"]
        sl_ts   = ts_rec["swingLength"]

        if bs_all.get("swings", 0) >= MIN_ALL_SWINGS and bs_all.get("avg") is not None:
            bs_all_pop.append(bs_all["avg"])

        if sl_all.get("swings", 0) >= MIN_ALL_SWINGS and sl_all.get("avg") is not None:
            sl_all_pop.append(sl_all["avg"])

        # Two-strike deltas require qualifying all-count AND two-strike data
        if (bs_all.get("swings", 0) >= MIN_ALL_SWINGS
                and sl_all.get("swings", 0) >= MIN_ALL_SWINGS
                and bs_ts.get("swings",  0) >= MIN_TS_SWINGS
                and sl_ts.get("swings",  0) >= MIN_TS_SWINGS
                and bs_all.get("avg") is not None
                and sl_all.get("avg") is not None
                and bs_ts.get("avg")  is not None
                and sl_ts.get("avg")  is not None):
            ts_bat_deltas.append(bs_ts["avg"] - bs_all["avg"])
            ts_len_deltas.append(sl_ts["avg"] - sl_all["avg"])

    n_ts          = len(ts_bat_deltas)
    n_shorteners  = sum(1 for d in ts_len_deltas if d < -LEN_THRESH_FT)
    n_extenders   = sum(1 for d in ts_len_deltas if d >  LEN_THRESH_FT)
    n_neutral     = n_ts - n_shorteners - n_extenders

    league_trends.append({
        "year":                  year,
        "nQualifyingAllCount":   len(bs_all_pop),
        "nQualifyingTwoStrike":  n_ts,
        "avgBatSpeed":           safe_mean(bs_all_pop),
        "avgSwingLength":        safe_mean(sl_all_pop),
        "avgTsBatDelta":         safe_mean(ts_bat_deltas),
        "avgTsLenDelta":         safe_mean(ts_len_deltas),
        "pctShorteners":         round(n_shorteners / n_ts * 100, 1) if n_ts else None,
        "pctExtenders":          round(n_extenders  / n_ts * 100, 1) if n_ts else None,
        "pctNeutral":            round(n_neutral     / n_ts * 100, 1) if n_ts else None,
        "nShorteners":           n_shorteners,
        "nExtenders":            n_extenders,
        "nNeutral":              n_neutral,
    })

print("League trends:")
for t in league_trends:
    print(
        f"  {t['year']}: n={t['nQualifyingAllCount']:4d}  "
        f"bs={t['avgBatSpeed']}  sl={t['avgSwingLength']}  "
        f"ts_bat_Δ={t['avgTsBatDelta']}  ts_len_Δ={t['avgTsLenDelta']}  "
        f"shorteners={t['pctShorteners']}%"
    )

# ---------------------------------------------------------------------------
# 2.  Per-player 2026 percentiles
# ---------------------------------------------------------------------------

# Build the 2026 population arrays used as reference distributions
pop_bat_speed_2026:    list[float] = []
pop_ts_bat_delta_2026: list[float] = []
pop_ts_len_delta_2026: list[float] = []

for player in agg.values():
    s = player.get("seasons", {}).get("2026")
    if not s:
        continue
    buckets = s["buckets"]
    all_rec = buckets["all"]
    ts_rec  = buckets["two_strikes"]
    bs_all  = all_rec["batSpeed"]
    sl_all  = all_rec["swingLength"]
    bs_ts   = ts_rec["batSpeed"]
    sl_ts   = ts_rec["swingLength"]

    if bs_all.get("swings", 0) >= MIN_ALL_SWINGS and bs_all.get("avg") is not None:
        pop_bat_speed_2026.append(bs_all["avg"])

    if (bs_all.get("swings", 0) >= MIN_ALL_SWINGS
            and sl_all.get("swings", 0) >= MIN_ALL_SWINGS
            and bs_ts.get("swings",  0) >= MIN_TS_SWINGS
            and sl_ts.get("swings",  0) >= MIN_TS_SWINGS
            and bs_all.get("avg") is not None
            and sl_all.get("avg") is not None
            and bs_ts.get("avg")  is not None
            and sl_ts.get("avg")  is not None):
        pop_ts_bat_delta_2026.append(bs_ts["avg"] - bs_all["avg"])
        pop_ts_len_delta_2026.append(sl_ts["avg"] - sl_all["avg"])

print(f"\n2026 percentile populations: "
      f"bat_speed n={len(pop_bat_speed_2026)}, "
      f"ts_bat_delta n={len(pop_ts_bat_delta_2026)}, "
      f"ts_len_delta n={len(pop_ts_len_delta_2026)}")

# Build per-player entries (keyed by agg name = "last, first")
player_percentiles: dict[str, dict] = {}

for agg_name, player in agg.items():
    s = player.get("seasons", {}).get("2026")
    if not s:
        continue

    buckets = s["buckets"]
    all_rec = buckets["all"]
    ts_rec  = buckets["two_strikes"]
    bs_all  = all_rec["batSpeed"]
    sl_all  = all_rec["swingLength"]
    bs_ts   = ts_rec["batSpeed"]
    sl_ts   = ts_rec["swingLength"]

    has_all = bs_all.get("swings", 0) >= MIN_ALL_SWINGS and bs_all.get("avg") is not None

    has_ts = (
        bs_all.get("swings", 0) >= MIN_ALL_SWINGS
        and sl_all.get("swings", 0) >= MIN_ALL_SWINGS
        and bs_ts.get("swings",  0) >= MIN_TS_SWINGS
        and sl_ts.get("swings",  0) >= MIN_TS_SWINGS
        and bs_all.get("avg") is not None
        and sl_all.get("avg") is not None
        and bs_ts.get("avg")  is not None
        and sl_ts.get("avg")  is not None
    )

    if not has_all and not has_ts:
        continue

    entry: dict = {"hasAll": has_all, "hasTs": has_ts}

    if has_all:
        bs = bs_all["avg"]
        sl = sl_all["avg"]
        entry["batSpeed"]    = round2(bs)
        entry["swingLength"] = round2(sl)
        entry["batSpeedSwings"] = bs_all["swings"]
        # Ascending: higher pct = faster
        entry["batSpeedPct"] = pct_rank_asc(pop_bat_speed_2026, bs)

    if has_ts:
        bat_d = bs_ts["avg"] - bs_all["avg"]
        len_d = sl_ts["avg"] - sl_all["avg"]
        entry["tsBatDelta"]  = round3(bat_d)
        entry["tsLenDelta"]  = round3(len_d)
        entry["tsBatSwings"] = bs_ts["swings"]
        entry["tsLenSwings"] = sl_ts["swings"]
        # Descending: higher pct = more deceleration (more negative delta)
        entry["tsBatDeltaDecelerationPct"] = pct_rank_desc(pop_ts_bat_delta_2026, bat_d)
        # Descending: higher pct = more shortening (more negative delta)
        entry["tsLenDeltaShorteningPct"]   = pct_rank_desc(pop_ts_len_delta_2026, len_d)

    player_percentiles[agg_name] = entry

print(f"Player percentile entries: {len(player_percentiles)}")

# Quick spot check
for check_name in ("judge, aaron", "trout, mike", "schwarber, kyle", "de la cruz, elly"):
    p = player_percentiles.get(check_name)
    if p:
        print(
            f"  {check_name:30s}  bs={p.get('batSpeed')} ({p.get('batSpeedPct')}th pct)  "
            f"ts_bat_Δ={p.get('tsBatDelta')} ({p.get('tsBatDeltaDecelerationPct')}th pct)  "
            f"ts_len_Δ={p.get('tsLenDelta')} ({p.get('tsLenDeltaShorteningPct')}th pct)"
        )

# ---------------------------------------------------------------------------
# 3.  2026 league ABS context
# ---------------------------------------------------------------------------

total_challenges  = sum(p["challenges"]       for p in abs_data.values())
total_overturns   = sum(p["overturns"]         for p in abs_data.values())
total_confirms    = sum(p["confirms"]           for p in abs_data.values())
total_walks       = sum(p["walksFlipped"]       for p in abs_data.values())
total_ks          = sum(p["strikeoutsFlipped"]  for p in abs_data.values())
n_challengers     = sum(1 for p in abs_data.values() if p["challenges"] > 0)

overall_rate = (
    round(total_overturns / total_challenges, 4)
    if total_challenges > 0 else None
)

# ABS overturn rate distribution (among players who have challenged)
overturn_rates = [
    p["overturnRate"]
    for p in abs_data.values()
    if p["challenges"] > 0 and p["overturnRate"] is not None
]
avg_player_overturn_rate = safe_mean(overturn_rates)

# totalVsExpected distribution
tvse_vals = [
    p["totalVsExpected"]
    for p in abs_data.values()
    if p["totalVsExpected"] is not None
]
avg_tvse = safe_mean(tvse_vals)
tvse_sd = None
if len(tvse_vals) > 1:
    m = sum(tvse_vals) / len(tvse_vals)
    tvse_sd = round((sum((v - m) ** 2 for v in tvse_vals) / (len(tvse_vals) - 1)) ** 0.5, 4)

abs_league_context = {
    "nPlayersWithData":          len(abs_data),
    "nWhoHaveChallenged":        n_challengers,
    "totalChallenges":           total_challenges,
    "totalOverturns":            total_overturns,
    "totalConfirms":             total_confirms,
    "overallOverturnRate":       overall_rate,
    "avgPlayerOverturnRate":     avg_player_overturn_rate,
    "totalWalksFlipped":         total_walks,
    "totalKsFlipped":            total_ks,
    "avgTotalVsExpected":        avg_tvse,
    "sdTotalVsExpected":         tvse_sd,
}

print(
    f"\n2026 ABS: {total_challenges} challenges, "
    f"{total_overturns}/{total_challenges} overturned "
    f"({round(overall_rate * 100) if overall_rate else '?'}%), "
    f"{total_ks} Ks avoided, {total_walks} walks created"
)

# ---------------------------------------------------------------------------
# 4.  Write output
# ---------------------------------------------------------------------------

# league2026 convenience block = trend row for 2026 merged with ABS data
trend_2026 = league_trends[-1]  # last entry is always 2026

output = {
    "generated":          str(date.today()),
    "leagueTrends":       league_trends,
    "league2026": {
        **trend_2026,
        "abs": abs_league_context,
    },
    "playerPercentiles2026": player_percentiles,
    "thresholds": {
        "minAllSwings":         MIN_ALL_SWINGS,
        "minTsSwings":          MIN_TS_SWINGS,
        "lenThresholdFt":       LEN_THRESH_FT,
        "batThresholdMph":      BAT_THRESH_MPH,
    },
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f)

# Human-readable size info
size_kb = os.path.getsize(OUT_PATH) / 1024
print(f"\nWrote {OUT_PATH}  ({size_kb:.1f} KB)")
print(f"  leagueTrends:          {len(league_trends)} year rows")
print(f"  playerPercentiles2026: {len(player_percentiles)} players")
print(f"  league2026.abs:        {n_challengers} ABS challengers tracked")
