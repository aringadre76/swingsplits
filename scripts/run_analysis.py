#!/usr/bin/env python3
"""
run_analysis.py
Comprehensive cross-analysis of ABS challenge data (2026) and swing split data (2023-2026).
Writes results to scripts/analysis_results.json and prints a human-readable summary.
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.join(os.path.dirname(__file__), "..")
AGG_PATH = os.path.join(BASE, "data", "hitter_aggregates.json")
ABS_PATH = os.path.join(BASE, "data", "abs_2026.json")
OUT_PATH = os.path.join(BASE, "scripts", "analysis_results.json")

# ---------------------------------------------------------------------------
# Name-matching helpers  (mirrors frontend toAbsKey)
# ---------------------------------------------------------------------------

def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def to_abs_key(raw: str) -> str:
    trimmed = raw.strip()
    if "," in trimmed:
        parts = trimmed.split(",", 1)
        last = parts[0].strip()
        first = parts[1].strip()
        trimmed = (first + " " + last) if (first and last) else (first or last)
    trimmed = strip_accents(trimmed)
    trimmed = re.sub(r"\s+(jr\.?|sr\.?|ii|iii|iv|v)\s*$", "", trimmed, flags=re.IGNORECASE).strip()
    return trimmed.lower()

# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None

def pearson_r(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)

def fmt(v, decimals=2):
    if v is None:
        return None
    return round(v, decimals)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

with open(AGG_PATH, encoding="utf-8") as f:
    agg = json.load(f)

with open(ABS_PATH, encoding="utf-8") as f:
    abs_data = json.load(f)

# Build reverse lookup: abs_key -> agg_name
agg_by_abs_key = {to_abs_key(name): name for name in agg}

# ---------------------------------------------------------------------------
# Helper: get 2026 bucket metrics for a player
# ---------------------------------------------------------------------------

def get_bucket(agg_name, season, bucket):
    """Return (bat_speed_avg, bat_speed_swings, swing_len_avg, swing_len_swings) or all None."""
    player = agg.get(agg_name)
    if not player:
        return None, None, None, None
    s = player.get("seasons", {}).get(season)
    if not s:
        return None, None, None, None
    b = s.get("buckets", {}).get(bucket)
    if not b:
        return None, None, None, None
    return (
        b["batSpeed"]["avg"],
        b["batSpeed"]["swings"],
        b["swingLength"]["avg"],
        b["swingLength"]["swings"],
    )

# ---------------------------------------------------------------------------
# Build the joined dataset: players present in BOTH abs_data and agg (2026)
# ---------------------------------------------------------------------------

joined = []  # list of dicts

for abs_key, abs_rec in abs_data.items():
    agg_name = agg_by_abs_key.get(abs_key)
    if not agg_name:
        continue
    bs_all, sw_all, sl_all, slsw_all = get_bucket(agg_name, "2026", "all")
    bs_2s, sw_2s, sl_2s, slsw_2s = get_bucket(agg_name, "2026", "two_strikes")
    bs_early, sw_early, sl_early, slsw_early = get_bucket(agg_name, "2026", "early")
    bs_ahead, sw_ahead, sl_ahead, slsw_ahead = get_bucket(agg_name, "2026", "ahead")
    bs_behind, sw_behind, sl_behind, slsw_behind = get_bucket(agg_name, "2026", "behind")

    # Deltas (two-strike minus all)
    ts_bat_delta = (bs_2s - bs_all) if (bs_2s is not None and bs_all is not None) else None
    ts_len_delta = (sl_2s - sl_all) if (sl_2s is not None and sl_all is not None) else None

    joined.append({
        "name": abs_rec["name"],
        "agg_name": agg_name,
        "abs_key": abs_key,
        "team": abs_rec["team"],
        # ABS metrics
        "challenges": abs_rec["challenges"],
        "overturns": abs_rec["overturns"],
        "confirms": abs_rec["confirms"],
        "overturn_rate": abs_rec["overturnRate"],
        "walks_flipped": abs_rec["walksFlipped"],
        "ks_flipped": abs_rec["strikeoutsFlipped"],
        "net_for": abs_rec["netFor"],
        "total_vs_expected": abs_rec["totalVsExpected"],
        "challenges_against": abs_rec["challengesAgainst"],
        "overturns_against": abs_rec["overturnsAgainst"],
        "overturn_rate_against": abs_rec["overturnRateAgainst"],
        # Swing all-count
        "bat_speed_all": bs_all,
        "bat_speed_all_swings": sw_all,
        "swing_len_all": sl_all,
        "swing_len_all_swings": slsw_all,
        # Swing two-strike
        "bat_speed_2s": bs_2s,
        "bat_speed_2s_swings": sw_2s,
        "swing_len_2s": sl_2s,
        "swing_len_2s_swings": slsw_2s,
        # Deltas
        "ts_bat_delta": ts_bat_delta,
        "ts_len_delta": ts_len_delta,
        # Early / ahead / behind all-count bat speed
        "bat_speed_early": bs_early,
        "bat_speed_ahead": bs_ahead,
        "bat_speed_behind": bs_behind,
        "swing_len_early": sl_early,
        "swing_len_ahead": sl_ahead,
        "swing_len_behind": sl_behind,
    })

print(f"Joined dataset: {len(joined)} players with both ABS and 2026 swing data\n")

# ---------------------------------------------------------------------------
# ANALYSIS 1: ABS overturn rate vs. two-strike swing approach
# ---------------------------------------------------------------------------
print("=" * 60)
print("ANALYSIS 1: Overturn rate vs. two-strike swing deltas")
print("=" * 60)

# Filter: has ABS challenges, has 2026 two-strike swings ≥20, has overturn rate
a1 = [
    p for p in joined
    if p["challenges"] > 0
    and p["overturn_rate"] is not None
    and p["bat_speed_2s_swings"] is not None and p["bat_speed_2s_swings"] >= 20
    and p["ts_bat_delta"] is not None
    and p["ts_len_delta"] is not None
]

r_bat = pearson_r([p["ts_bat_delta"] for p in a1], [p["overturn_rate"] for p in a1])
r_len = pearson_r([p["ts_len_delta"] for p in a1], [p["overturn_rate"] for p in a1])

print(f"  N = {len(a1)} players")
print(f"  Pearson r (two-strike bat speed delta vs overturn rate): {r_bat}")
print(f"  Pearson r (two-strike swing length delta vs overturn rate): {r_len}")

a1_sorted_rate = sorted(a1, key=lambda p: p["overturn_rate"], reverse=True)
top5_a1 = [
    {"name": p["name"], "team": p["team"],
     "overturn_rate": fmt(p["overturn_rate"]),
     "challenges": p["challenges"],
     "overturns": p["overturns"],
     "ts_bat_delta": fmt(p["ts_bat_delta"]),
     "ts_len_delta": fmt(p["ts_len_delta"])}
    for p in a1_sorted_rate[:5]
]
bot5_a1 = [
    {"name": p["name"], "team": p["team"],
     "overturn_rate": fmt(p["overturn_rate"]),
     "challenges": p["challenges"],
     "overturns": p["overturns"],
     "ts_bat_delta": fmt(p["ts_bat_delta"]),
     "ts_len_delta": fmt(p["ts_len_delta"])}
    for p in a1_sorted_rate[-5:]
]

print("\n  Top 5 ABS overturn rates:")
for p in top5_a1:
    print(f"    {p['name']:25s} {p['overturns']}/{p['challenges']}  ts_bat_Δ={p['ts_bat_delta']:+.2f}  ts_len_Δ={p['ts_len_delta']:+.2f}")
print("\n  Bottom 5 ABS overturn rates (min 1 challenge):")
for p in bot5_a1:
    print(f"    {p['name']:25s} {p['overturns']}/{p['challenges']}  ts_bat_Δ={p['ts_bat_delta']:+.2f}  ts_len_Δ={p['ts_len_delta']:+.2f}")

analysis_1 = {
    "n": len(a1),
    "pearson_r_bat_delta_vs_overturn_rate": r_bat,
    "pearson_r_len_delta_vs_overturn_rate": r_len,
    "top5_by_overturn_rate": top5_a1,
    "bottom5_by_overturn_rate": bot5_a1,
}

# ---------------------------------------------------------------------------
# ANALYSIS 2: Swing length shortening groups vs. ABS performance
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 2: Two-strike shorteners vs. extenders (2026)")
print("=" * 60)

# All 2026 players with enough swings
MIN_2S_SWINGS = 20
MIN_ALL_SWINGS = 30

qualified_2026 = []
for agg_name, player in agg.items():
    s = player.get("seasons", {}).get("2026")
    if not s:
        continue
    all_b = s["buckets"].get("all", {})
    ts_b = s["buckets"].get("two_strikes", {})
    bs_all = all_b.get("batSpeed", {})
    sl_all = all_b.get("swingLength", {})
    bs_2s = ts_b.get("batSpeed", {})
    sl_2s = ts_b.get("swingLength", {})
    if (bs_all.get("swings", 0) >= MIN_ALL_SWINGS
            and sl_all.get("swings", 0) >= MIN_ALL_SWINGS
            and bs_2s.get("swings", 0) >= MIN_2S_SWINGS
            and sl_2s.get("swings", 0) >= MIN_2S_SWINGS
            and bs_all.get("avg") is not None
            and sl_all.get("avg") is not None
            and bs_2s.get("avg") is not None
            and sl_2s.get("avg") is not None):
        abs_key = to_abs_key(agg_name)
        abs_rec = abs_data.get(abs_key)
        len_delta = sl_2s["avg"] - sl_all["avg"]
        bat_delta = bs_2s["avg"] - bs_all["avg"]
        qualified_2026.append({
            "agg_name": agg_name,
            "abs_key": abs_key,
            "bat_speed_all": bs_all["avg"],
            "swing_len_all": sl_all["avg"],
            "bat_speed_2s": bs_2s["avg"],
            "swing_len_2s": sl_2s["avg"],
            "ts_len_delta": len_delta,
            "ts_bat_delta": bat_delta,
            "has_abs": abs_rec is not None,
            "abs_challenges": abs_rec["challenges"] if abs_rec else 0,
            "abs_overturn_rate": abs_rec["overturnRate"] if abs_rec else None,
            "abs_walks_flipped": abs_rec["walksFlipped"] if abs_rec else 0,
            "abs_net_for": abs_rec["netFor"] if abs_rec else 0,
            "abs_total_vs_expected": abs_rec["totalVsExpected"] if abs_rec else None,
        })

print(f"  Qualified 2026 players (≥{MIN_ALL_SWINGS} all-count swings, ≥{MIN_2S_SWINGS} two-strike swings): {len(qualified_2026)}")

LEN_THRESH = 0.2
BAT_THRESH = 1.0

def group_stats(players, label):
    bs_vals = [p["bat_speed_all"] for p in players]
    sl_vals = [p["swing_len_all"] for p in players]
    ts_bat_deltas = [p["ts_bat_delta"] for p in players]
    ts_len_deltas = [p["ts_len_delta"] for p in players]
    abs_players = [p for p in players if p["has_abs"] and p["abs_challenges"] > 0]
    overturn_rates = [p["abs_overturn_rate"] for p in abs_players if p["abs_overturn_rate"] is not None]
    challenges = [p["abs_challenges"] for p in abs_players]
    walks = [p["abs_walks_flipped"] for p in abs_players]
    net_for_vals = [p["abs_net_for"] for p in abs_players]
    tvse_vals = [p["abs_total_vs_expected"] for p in abs_players if p["abs_total_vs_expected"] is not None]
    return {
        "group": label,
        "n_players": len(players),
        "avg_bat_speed_all": fmt(mean(bs_vals)),
        "avg_swing_len_all": fmt(mean(sl_vals)),
        "avg_ts_bat_delta": fmt(mean(ts_bat_deltas)),
        "avg_ts_len_delta": fmt(mean(ts_len_deltas)),
        "n_with_abs_challenges": len(abs_players),
        "avg_overturn_rate": fmt(mean(overturn_rates)),
        "avg_challenges": fmt(mean(challenges)),
        "avg_walks_flipped": fmt(mean(walks), 3),
        "avg_net_for": fmt(mean(net_for_vals)),
        "avg_total_vs_expected": fmt(mean(tvse_vals)),
    }

len_shorteners = [p for p in qualified_2026 if p["ts_len_delta"] < -LEN_THRESH]
len_extenders = [p for p in qualified_2026 if p["ts_len_delta"] > LEN_THRESH]
len_neutral = [p for p in qualified_2026 if abs(p["ts_len_delta"]) <= LEN_THRESH]

bat_decelerators = [p for p in qualified_2026 if p["ts_bat_delta"] < -BAT_THRESH]
bat_accelerators = [p for p in qualified_2026 if p["ts_bat_delta"] > BAT_THRESH]
bat_neutral = [p for p in qualified_2026 if abs(p["ts_bat_delta"]) <= BAT_THRESH]

len_groups = [
    group_stats(len_shorteners, "shorteners (ts_len_delta < -0.2 ft)"),
    group_stats(len_neutral,    "neutral (|ts_len_delta| ≤ 0.2 ft)"),
    group_stats(len_extenders,  "extenders (ts_len_delta > +0.2 ft)"),
]
bat_groups = [
    group_stats(bat_decelerators, "decelerators (ts_bat_delta < -1 mph)"),
    group_stats(bat_neutral,       "neutral (|ts_bat_delta| ≤ 1 mph)"),
    group_stats(bat_accelerators,  "accelerators (ts_bat_delta > +1 mph)"),
]

print("\n  Swing LENGTH groups in two-strike counts:")
for g in len_groups:
    print(f"    {g['group']:45s}  n={g['n_players']:3d}  avg_bs={g['avg_bat_speed_all']}  avg_len={g['avg_swing_len_all']}  "
          f"abs_win%={g['avg_overturn_rate']}  avg_chal={g['avg_challenges']}")

print("\n  Bat SPEED groups in two-strike counts:")
for g in bat_groups:
    print(f"    {g['group']:45s}  n={g['n_players']:3d}  avg_bs={g['avg_bat_speed_all']}  avg_len={g['avg_swing_len_all']}  "
          f"abs_win%={g['avg_overturn_rate']}  avg_chal={g['avg_challenges']}")

analysis_2 = {
    "n_qualified_2026": len(qualified_2026),
    "len_threshold_ft": LEN_THRESH,
    "bat_threshold_mph": BAT_THRESH,
    "swing_length_groups": len_groups,
    "bat_speed_groups": bat_groups,
}

# ---------------------------------------------------------------------------
# ANALYSIS 3: Year-over-year swing trends (2023 → 2026 population averages)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 3: Year-over-year population swing trends")
print("=" * 60)

YOY_MIN_SWINGS = 30
yoy_data = {}

for year in ["2023", "2024", "2025", "2026"]:
    bs_vals, sl_vals = [], []
    ts_bat_deltas, ts_len_deltas = [], []
    n_shorteners, n_extenders, n_neutral = 0, 0, 0
    for agg_name, player in agg.items():
        s = player.get("seasons", {}).get(year)
        if not s:
            continue
        all_b = s["buckets"].get("all", {})
        ts_b = s["buckets"].get("two_strikes", {})
        bs_all_rec = all_b.get("batSpeed", {})
        sl_all_rec = all_b.get("swingLength", {})
        bs_2s_rec = ts_b.get("batSpeed", {})
        sl_2s_rec = ts_b.get("swingLength", {})
        if (bs_all_rec.get("swings", 0) >= YOY_MIN_SWINGS
                and sl_all_rec.get("swings", 0) >= YOY_MIN_SWINGS
                and bs_all_rec.get("avg") is not None
                and sl_all_rec.get("avg") is not None):
            bs_vals.append(bs_all_rec["avg"])
            sl_vals.append(sl_all_rec["avg"])
        if (bs_all_rec.get("swings", 0) >= YOY_MIN_SWINGS
                and sl_all_rec.get("swings", 0) >= YOY_MIN_SWINGS
                and bs_2s_rec.get("swings", 0) >= 20
                and bs_all_rec.get("avg") is not None
                and sl_all_rec.get("avg") is not None
                and bs_2s_rec.get("avg") is not None
                and sl_2s_rec.get("avg") is not None):
            bat_d = bs_2s_rec["avg"] - bs_all_rec["avg"]
            len_d = sl_2s_rec["avg"] - sl_all_rec["avg"]
            ts_bat_deltas.append(bat_d)
            ts_len_deltas.append(len_d)
            if len_d < -LEN_THRESH:
                n_shorteners += 1
            elif len_d > LEN_THRESH:
                n_extenders += 1
            else:
                n_neutral += 1

    yoy_data[year] = {
        "year": year,
        "n_qualifying_players": len(bs_vals),
        "pop_avg_bat_speed": fmt(mean(bs_vals)),
        "pop_avg_swing_length": fmt(mean(sl_vals)),
        "n_with_ts_data": len(ts_bat_deltas),
        "pop_avg_ts_bat_delta": fmt(mean(ts_bat_deltas)),
        "pop_avg_ts_len_delta": fmt(mean(ts_len_deltas)),
        "pct_shorteners": fmt(n_shorteners / len(ts_bat_deltas) * 100 if ts_bat_deltas else None, 1),
        "pct_extenders": fmt(n_extenders / len(ts_bat_deltas) * 100 if ts_bat_deltas else None, 1),
        "pct_neutral": fmt(n_neutral / len(ts_bat_deltas) * 100 if ts_bat_deltas else None, 1),
    }

    print(f"  {year}: n={len(bs_vals):4d}  avg_bat={yoy_data[year]['pop_avg_bat_speed']}  "
          f"avg_len={yoy_data[year]['pop_avg_swing_length']}  "
          f"ts_bat_Δ={yoy_data[year]['pop_avg_ts_bat_delta']}  "
          f"ts_len_Δ={yoy_data[year]['pop_avg_ts_len_delta']}  "
          f"shorteners={yoy_data[year]['pct_shorteners']}%")

analysis_3 = {"year_over_year": list(yoy_data.values())}

# ---------------------------------------------------------------------------
# ANALYSIS 4: ABS aggressiveness vs. swing profile (bat speed quartiles)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 4: Bat speed quartiles vs. ABS challenge behaviour")
print("=" * 60)

# Use players with ABS data AND 2026 all-count swing data (≥30 swings)
a4 = [
    p for p in joined
    if p["bat_speed_all"] is not None
    and p["bat_speed_all_swings"] is not None
    and p["bat_speed_all_swings"] >= 30
]

if len(a4) >= 4:
    a4_sorted = sorted(a4, key=lambda p: p["bat_speed_all"])
    q_size = len(a4_sorted) // 4
    quartiles = [
        a4_sorted[:q_size],
        a4_sorted[q_size:2*q_size],
        a4_sorted[2*q_size:3*q_size],
        a4_sorted[3*q_size:],
    ]
    quartile_labels = ["Q1 (slowest)", "Q2", "Q3", "Q4 (fastest)"]

    quartile_stats = []
    for label, grp in zip(quartile_labels, quartiles):
        challengers = [p for p in grp if p["challenges"] > 0]
        overturn_rates = [p["overturn_rate"] for p in challengers if p["overturn_rate"] is not None]
        net_fors = [p["net_for"] for p in challengers]
        challenges_list = [p["challenges"] for p in grp]
        qstat = {
            "quartile": label,
            "n": len(grp),
            "bat_speed_range": [fmt(grp[0]["bat_speed_all"]), fmt(grp[-1]["bat_speed_all"])],
            "avg_bat_speed": fmt(mean([p["bat_speed_all"] for p in grp])),
            "avg_swing_len": fmt(mean([p["swing_len_all"] for p in grp if p["swing_len_all"] is not None])),
            "avg_challenges": fmt(mean(challenges_list), 2),
            "n_who_challenged": len(challengers),
            "avg_overturn_rate_among_challengers": fmt(mean(overturn_rates)),
            "avg_net_for_among_challengers": fmt(mean(net_fors)) if net_fors else None,
        }
        quartile_stats.append(qstat)
        print(f"  {label:15s}: n={qstat['n']}  bat=[{qstat['bat_speed_range'][0]}-{qstat['bat_speed_range'][1]}]  "
              f"avg_chal={qstat['avg_challenges']}  challengers={qstat['n_who_challenged']}  "
              f"win%={qstat['avg_overturn_rate_among_challengers']}")

    analysis_4 = {"quartile_stats": quartile_stats}
else:
    print("  Not enough data for quartile analysis.")
    analysis_4 = {"quartile_stats": []}

# ---------------------------------------------------------------------------
# ANALYSIS 5: "Protected K" analysis – who's avoiding strikeouts with ABS
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 5: Strikeout-avoidance via ABS challenges")
print("=" * 60)

protected_k = []
for p in joined:
    if p["ks_flipped"] > 0:
        protected_k.append({
            "name": p["name"],
            "team": p["team"],
            "ks_flipped": p["ks_flipped"],
            "walks_flipped": p["walks_flipped"],
            "challenges": p["challenges"],
            "overturns": p["overturns"],
            "ts_bat_delta": fmt(p["ts_bat_delta"]),
            "ts_len_delta": fmt(p["ts_len_delta"]),
            "bat_speed_all": fmt(p["bat_speed_all"]),
            "swing_len_all": fmt(p["swing_len_all"]),
        })

protected_k.sort(key=lambda p: p["ks_flipped"], reverse=True)
print(f"  Players with Ks avoided via ABS: {len(protected_k)}")
for p in protected_k:
    print(f"    {p['name']:25s}  Ks_avoided={p['ks_flipped']}  walks_created={p['walks_flipped']}  "
          f"ts_bat_Δ={p['ts_bat_delta']}  ts_len_Δ={p['ts_len_delta']}  "
          f"bat_speed={p['bat_speed_all']}  swing_len={p['swing_len_all']}")

# Also: among players with strikeouts flipped, are they more likely to be shorteners?
pk_shorteners = [p for p in protected_k if p["ts_len_delta"] is not None and p["ts_len_delta"] < -LEN_THRESH]
pk_extenders = [p for p in protected_k if p["ts_len_delta"] is not None and p["ts_len_delta"] > LEN_THRESH]
print(f"\n  Of K-avoiders: shorteners={len(pk_shorteners)}  extenders={len(pk_extenders)}")

analysis_5 = {
    "n_with_ks_flipped": len(protected_k),
    "players": protected_k,
    "n_shorteners_among_k_avoiders": len(pk_shorteners),
    "n_extenders_among_k_avoiders": len(pk_extenders),
}

# ---------------------------------------------------------------------------
# ANALYSIS 6: Top & bottom ABS performers with full swing profile
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 6: Top/bottom ABS performers with swing profiles")
print("=" * 60)

abs_perf = sorted(joined, key=lambda p: p["total_vs_expected"], reverse=True)

def perf_entry(p):
    return {
        "name": p["name"],
        "team": p["team"],
        "challenges": p["challenges"],
        "overturns": p["overturns"],
        "confirms": p["confirms"],
        "net_for": fmt(p["net_for"]),
        "total_vs_expected": fmt(p["total_vs_expected"]),
        "walks_flipped": p["walks_flipped"],
        "ks_flipped": p["ks_flipped"],
        "bat_speed_all": fmt(p["bat_speed_all"]),
        "swing_len_all": fmt(p["swing_len_all"]),
        "ts_bat_delta": fmt(p["ts_bat_delta"]),
        "ts_len_delta": fmt(p["ts_len_delta"]),
    }

top10 = [perf_entry(p) for p in abs_perf[:10]]
bot10 = [perf_entry(p) for p in abs_perf[-10:]]

print("  Top 10 (total_vs_expected):")
for p in top10:
    print(f"    {p['name']:25s}  tvse={p['total_vs_expected']:+.2f}  {p['overturns']}/{p['challenges']}  "
          f"bs={p['bat_speed_all']}  sl={p['swing_len_all']}  ts_batΔ={p['ts_bat_delta']}  ts_lenΔ={p['ts_len_delta']}")

print("\n  Bottom 10 (total_vs_expected):")
for p in bot10:
    print(f"    {p['name']:25s}  tvse={p['total_vs_expected']:+.2f}  {p['overturns']}/{p['challenges']}  "
          f"bs={p['bat_speed_all']}  sl={p['swing_len_all']}  ts_batΔ={p['ts_bat_delta']}  ts_lenΔ={p['ts_len_delta']}")

analysis_6 = {
    "top10_by_total_vs_expected": top10,
    "bottom10_by_total_vs_expected": bot10,
}

# ---------------------------------------------------------------------------
# ANALYSIS 7: 2026 vs. career swing changes for ABS challengers
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 7: 2026 vs. career swing changes for ABS challengers")
print("=" * 60)

career_shifts = []
for p in joined:
    agg_name = p["agg_name"]
    player = agg.get(agg_name, {})
    career_s = player.get("seasons", {}).get("career")
    if not career_s:
        continue
    career_all = career_s["buckets"].get("all", {})
    career_2s = career_s["buckets"].get("two_strikes", {})
    c_bs = career_all.get("batSpeed", {})
    c_sl = career_all.get("swingLength", {})
    c_2s_bs = career_2s.get("batSpeed", {})
    c_2s_sl = career_2s.get("swingLength", {})
    if (c_bs.get("avg") is None or p["bat_speed_all"] is None
            or c_sl.get("avg") is None or p["swing_len_all"] is None
            or c_bs.get("swings", 0) < 50 or (p["bat_speed_all_swings"] or 0) < 20):
        continue

    bs_shift = p["bat_speed_all"] - c_bs["avg"]
    sl_shift = p["swing_len_all"] - c_sl["avg"]

    # Two-strike delta shift: is the player shortening MORE or LESS than career norm?
    career_ts_len_delta = None
    if (c_2s_sl.get("avg") is not None and c_sl.get("avg") is not None
            and c_2s_sl.get("swings", 0) >= 20):
        career_ts_len_delta = c_2s_sl["avg"] - c_sl["avg"]

    ts_len_delta_shift = None
    if career_ts_len_delta is not None and p["ts_len_delta"] is not None:
        ts_len_delta_shift = p["ts_len_delta"] - career_ts_len_delta

    career_shifts.append({
        "name": p["name"],
        "team": p["team"],
        "challenges": p["challenges"],
        "overturns": p["overturns"],
        "overturn_rate": p["overturn_rate"],
        "bs_2026_vs_career": fmt(bs_shift),
        "sl_2026_vs_career": fmt(sl_shift),
        "career_ts_len_delta": fmt(career_ts_len_delta),
        "current_ts_len_delta": fmt(p["ts_len_delta"]),
        "ts_len_delta_shift": fmt(ts_len_delta_shift),
    })

career_shifts.sort(key=lambda p: p["ts_len_delta_shift"] if p["ts_len_delta_shift"] is not None else 0, reverse=True)

print(f"  Players with career comparison available: {len(career_shifts)}")
print("\n  Most increased two-strike shortening in 2026 vs. career (top 8):")
for p in career_shifts[:8]:
    print(f"    {p['name']:25s}  ts_len_delta_shift={p['ts_len_delta_shift']:+.2f}  "
          f"career_ts_len_Δ={p['career_ts_len_delta']}  2026_ts_len_Δ={p['current_ts_len_delta']}  "
          f"abs={p['overturns']}/{p['challenges']}")

print("\n  Most decreased two-strike shortening in 2026 vs. career (bottom 8):")
for p in career_shifts[-8:]:
    print(f"    {p['name']:25s}  ts_len_delta_shift={p['ts_len_delta_shift']:+.2f}  "
          f"career_ts_len_Δ={p['career_ts_len_delta']}  2026_ts_len_Δ={p['current_ts_len_delta']}  "
          f"abs={p['overturns']}/{p['challenges']}")

# Avg bs/sl shift for challengers vs non-challengers (among qualified)
challengers_cs = [p for p in career_shifts if p["challenges"] > 0]
non_challengers_cs = [p for p in career_shifts if p["challenges"] == 0]
print(f"\n  Challengers (n={len(challengers_cs)}):  avg bs shift={fmt(mean([p['bs_2026_vs_career'] for p in challengers_cs if p['bs_2026_vs_career'] is not None]))}  "
      f"avg sl shift={fmt(mean([p['sl_2026_vs_career'] for p in challengers_cs if p['sl_2026_vs_career'] is not None]))}")
print(f"  Non-challengers (n={len(non_challengers_cs)}):  avg bs shift={fmt(mean([p['bs_2026_vs_career'] for p in non_challengers_cs if p['bs_2026_vs_career'] is not None]))}  "
      f"avg sl shift={fmt(mean([p['sl_2026_vs_career'] for p in non_challengers_cs if p['sl_2026_vs_career'] is not None]))}")

analysis_7 = {
    "n_with_career_comparison": len(career_shifts),
    "challengers_avg_bs_shift_vs_career": fmt(mean([p["bs_2026_vs_career"] for p in challengers_cs if p["bs_2026_vs_career"] is not None])),
    "challengers_avg_sl_shift_vs_career": fmt(mean([p["sl_2026_vs_career"] for p in challengers_cs if p["sl_2026_vs_career"] is not None])),
    "non_challengers_avg_bs_shift_vs_career": fmt(mean([p["bs_2026_vs_career"] for p in non_challengers_cs if p["bs_2026_vs_career"] is not None])),
    "non_challengers_avg_sl_shift_vs_career": fmt(mean([p["sl_2026_vs_career"] for p in non_challengers_cs if p["sl_2026_vs_career"] is not None])),
    "most_increased_ts_shortening": career_shifts[:8],
    "most_decreased_ts_shortening": career_shifts[-8:],
}

# ---------------------------------------------------------------------------
# ANALYSIS 8: Count bucket profiles — who challenges most by approach type
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 8: Count-bucket approach and challenge propensity")
print("=" * 60)

# For each player, compute their "behind" vs "early" bat speed delta
# Hypothesis: hitters who slow WAY down behind in the count are more protective
# and might be more ABS-savvy (taking more, challenging more)

a8 = []
for p in joined:
    if p["bat_speed_all"] is None or p["bat_speed_behind"] is None or p["bat_speed_early"] is None:
        continue
    if p["swing_len_all"] is None or p["swing_len_behind"] is None:
        continue
    behind_bat_delta = p["bat_speed_behind"] - p["bat_speed_all"]
    behind_len_delta = p["swing_len_behind"] - p["swing_len_all"]
    early_bat_delta = p["bat_speed_early"] - p["bat_speed_all"]
    a8.append({
        **p,
        "behind_bat_delta": behind_bat_delta,
        "behind_len_delta": behind_len_delta,
        "early_bat_delta": early_bat_delta,
    })

# Correlation: behind_len_delta vs challenges
r_behind_len_chal = pearson_r(
    [p["behind_len_delta"] for p in a8],
    [p["challenges"] for p in a8]
)
r_behind_bat_chal = pearson_r(
    [p["behind_bat_delta"] for p in a8],
    [p["challenges"] for p in a8]
)
r_early_bat_tvse = pearson_r(
    [p["early_bat_delta"] for p in a8 if p["total_vs_expected"] is not None],
    [p["total_vs_expected"] for p in a8 if p["total_vs_expected"] is not None]
)

print(f"  n = {len(a8)}")
print(f"  Pearson r (behind len delta vs challenges initiated): {r_behind_len_chal}")
print(f"  Pearson r (behind bat delta vs challenges initiated): {r_behind_bat_chal}")
print(f"  Pearson r (early bat delta vs total_vs_expected): {r_early_bat_tvse}")

analysis_8 = {
    "n": len(a8),
    "pearson_r_behind_len_delta_vs_challenges": r_behind_len_chal,
    "pearson_r_behind_bat_delta_vs_challenges": r_behind_bat_chal,
    "pearson_r_early_bat_delta_vs_total_vs_expected": r_early_bat_tvse,
}

# ---------------------------------------------------------------------------
# ANALYSIS 9: "Takes" proxy — swing length in two-strike vs. ahead counts
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 9: Ahead vs. two-strike approach divergence")
print("=" * 60)

# Hitters who have very DIFFERENT approaches when ahead vs. two-strike:
# Big gap = disciplined approach adjustment.  Correlate with ABS performance.
a9 = []
for p in joined:
    if (p["bat_speed_ahead"] is None or p["bat_speed_2s"] is None
            or p["swing_len_ahead"] is None or p["swing_len_2s"] is None
            or p["bat_speed_all"] is None):
        continue
    ahead_to_2s_bat = p["bat_speed_ahead"] - p["bat_speed_2s"]
    ahead_to_2s_len = p["swing_len_ahead"] - p["swing_len_2s"]
    a9.append({**p, "ahead_to_2s_bat": ahead_to_2s_bat, "ahead_to_2s_len": ahead_to_2s_len})

r_ahead_2s_len_tvse = pearson_r(
    [p["ahead_to_2s_len"] for p in a9],
    [p["total_vs_expected"] for p in a9]
)
r_ahead_2s_bat_tvse = pearson_r(
    [p["ahead_to_2s_bat"] for p in a9],
    [p["total_vs_expected"] for p in a9]
)

print(f"  n = {len(a9)}")
print(f"  Pearson r (ahead→two-strike LEN gap vs totalVsExpected): {r_ahead_2s_len_tvse}")
print(f"  Pearson r (ahead→two-strike BAT gap vs totalVsExpected): {r_ahead_2s_bat_tvse}")

# Top divergers (biggest ahead vs 2s approach gap)
a9_sorted = sorted(a9, key=lambda p: p["ahead_to_2s_len"], reverse=True)
print("\n  Biggest ahead→two-strike swing length divergence (top 8):")
for p in a9_sorted[:8]:
    print(f"    {p['name']:25s}  ahead_len={fmt(p['swing_len_ahead'])}  2s_len={fmt(p['swing_len_2s'])}  "
          f"gap={fmt(p['ahead_to_2s_len']):+.2f}  tvse={fmt(p['total_vs_expected']):+.2f}  "
          f"abs={p['overturns']}/{p['challenges']}")

analysis_9 = {
    "n": len(a9),
    "pearson_r_ahead_2s_len_gap_vs_total_vs_expected": r_ahead_2s_len_tvse,
    "pearson_r_ahead_2s_bat_gap_vs_total_vs_expected": r_ahead_2s_bat_tvse,
    "top8_biggest_ahead_2s_len_divergence": [
        {"name": p["name"], "team": p["team"],
         "swing_len_ahead": fmt(p["swing_len_ahead"]),
         "swing_len_2s": fmt(p["swing_len_2s"]),
         "ahead_to_2s_len_gap": fmt(p["ahead_to_2s_len"]),
         "bat_speed_ahead": fmt(p["bat_speed_ahead"]),
         "bat_speed_2s": fmt(p["bat_speed_2s"]),
         "total_vs_expected": fmt(p["total_vs_expected"]),
         "overturns": p["overturns"], "challenges": p["challenges"]}
        for p in a9_sorted[:8]
    ],
}

# ---------------------------------------------------------------------------
# ANALYSIS 10: Population-level "discipline score" and ABS correlation
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ANALYSIS 10: Composite discipline score vs. ABS performance")
print("=" * 60)

# Discipline score: lower is more disciplined
# = (ts_len_delta / sd_ts_len_delta) + (ts_bat_delta / sd_ts_bat_delta)
# More negative = shortens more + slows more in two-strike counts

ts_len_vals = [p["ts_len_delta"] for p in joined if p["ts_len_delta"] is not None]
ts_bat_vals = [p["ts_bat_delta"] for p in joined if p["ts_bat_delta"] is not None]

def stdev(vals):
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
    return math.sqrt(var)

sd_len = stdev(ts_len_vals)
sd_bat = stdev(ts_bat_vals)

discipline_players = []
for p in joined:
    if (p["ts_len_delta"] is None or p["ts_bat_delta"] is None
            or sd_len is None or sd_bat is None):
        continue
    z_len = p["ts_len_delta"] / sd_len
    z_bat = p["ts_bat_delta"] / sd_bat
    discipline_score = z_len + z_bat  # more negative = more disciplined
    discipline_players.append({**p, "discipline_score": discipline_score})

r_discipline_tvse = pearson_r(
    [p["discipline_score"] for p in discipline_players],
    [p["total_vs_expected"] for p in discipline_players]
)
r_discipline_overturns = pearson_r(
    [p["discipline_score"] for p in discipline_players],
    [p["overturns"] for p in discipline_players]
)
r_discipline_challenges = pearson_r(
    [p["discipline_score"] for p in discipline_players],
    [p["challenges"] for p in discipline_players]
)

print(f"  n = {len(discipline_players)}")
print(f"  SD of ts_len_delta: {fmt(sd_len)}")
print(f"  SD of ts_bat_delta: {fmt(sd_bat)}")
print(f"  Pearson r (discipline score vs totalVsExpected): {r_discipline_tvse}")
print(f"  Pearson r (discipline score vs overturns): {r_discipline_overturns}")
print(f"  Pearson r (discipline score vs challenges): {r_discipline_challenges}")

most_disciplined = sorted(discipline_players, key=lambda p: p["discipline_score"])[:10]
least_disciplined = sorted(discipline_players, key=lambda p: p["discipline_score"], reverse=True)[:10]

print("\n  Most disciplined (most negative score = shorten + slow down most in 2-strike):")
for p in most_disciplined:
    print(f"    {p['name']:25s}  score={fmt(p['discipline_score']):+.2f}  "
          f"ts_batΔ={fmt(p['ts_bat_delta']):+.2f}  ts_lenΔ={fmt(p['ts_len_delta']):+.2f}  "
          f"abs={p['overturns']}/{p['challenges']}  tvse={fmt(p['total_vs_expected']):+.2f}")

print("\n  Least disciplined (extend and accelerate in 2-strike):")
for p in least_disciplined:
    print(f"    {p['name']:25s}  score={fmt(p['discipline_score']):+.2f}  "
          f"ts_batΔ={fmt(p['ts_bat_delta']):+.2f}  ts_lenΔ={fmt(p['ts_len_delta']):+.2f}  "
          f"abs={p['overturns']}/{p['challenges']}  tvse={fmt(p['total_vs_expected']):+.2f}")

analysis_10 = {
    "n": len(discipline_players),
    "sd_ts_len_delta": fmt(sd_len),
    "sd_ts_bat_delta": fmt(sd_bat),
    "pearson_r_discipline_vs_total_vs_expected": r_discipline_tvse,
    "pearson_r_discipline_vs_overturns": r_discipline_overturns,
    "pearson_r_discipline_vs_challenges": r_discipline_challenges,
    "most_disciplined_10": [
        {"name": p["name"], "team": p["team"], "discipline_score": fmt(p["discipline_score"]),
         "ts_bat_delta": fmt(p["ts_bat_delta"]), "ts_len_delta": fmt(p["ts_len_delta"]),
         "overturns": p["overturns"], "challenges": p["challenges"],
         "total_vs_expected": fmt(p["total_vs_expected"])}
        for p in most_disciplined
    ],
    "least_disciplined_10": [
        {"name": p["name"], "team": p["team"], "discipline_score": fmt(p["discipline_score"]),
         "ts_bat_delta": fmt(p["ts_bat_delta"]), "ts_len_delta": fmt(p["ts_len_delta"]),
         "overturns": p["overturns"], "challenges": p["challenges"],
         "total_vs_expected": fmt(p["total_vs_expected"])}
        for p in least_disciplined
    ],
}

# ---------------------------------------------------------------------------
# Write JSON output
# ---------------------------------------------------------------------------
results = {
    "meta": {
        "n_abs_players": len(abs_data),
        "n_agg_players_2026": sum(1 for p in agg.values() if "2026" in p.get("seasons", {})),
        "n_joined": len(joined),
    },
    "analysis_1_overturn_rate_vs_2s_swing": analysis_1,
    "analysis_2_swing_length_groups": analysis_2,
    "analysis_3_year_over_year_trends": analysis_3,
    "analysis_4_bat_speed_quartiles": analysis_4,
    "analysis_5_protected_ks": analysis_5,
    "analysis_6_top_bottom_abs_performers": analysis_6,
    "analysis_7_2026_vs_career_shifts": analysis_7,
    "analysis_8_count_bucket_approach": analysis_8,
    "analysis_9_ahead_vs_2s_divergence": analysis_9,
    "analysis_10_discipline_score": analysis_10,
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\n\nResults written to {OUT_PATH}")
