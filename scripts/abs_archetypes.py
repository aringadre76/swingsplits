#!/usr/bin/env python3
"""
abs_archetypes.py

Deep-dive player-archetype analysis: what kinds of hitters win ABS challenges,
what kinds lose them, and what the swing-split data tells us about why.

Outputs:
    scripts/archetype_results.json   – structured data for conclusions.md
    stdout                           – human-readable narrative summary

Run:
    python3 scripts/abs_archetypes.py
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
CTX_PATH = os.path.join(BASE, "data", "league_context.json")
OUT_PATH = os.path.join(BASE, "scripts", "archetype_results.json")

# ---------------------------------------------------------------------------
# Name normalisation  (mirrors frontend toAbsKey)
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
    trimmed = re.sub(
        r"\s+(jr\.?|sr\.?|ii|iii|iv|v)\s*$", "", trimmed, flags=re.IGNORECASE
    ).strip()
    return trimmed.lower()


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------


def safe_mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def safe_median(vals):
    vals = sorted(v for v in vals if v is not None)
    n = len(vals)
    if not n:
        return None
    mid = n // 2
    return (vals[mid - 1] + vals[mid]) / 2 if n % 2 == 0 else vals[mid]


def stdev(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def pearson_r(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 4:
        return None
    xs2, ys2 = zip(*pairs)
    n = len(xs2)
    mx = sum(xs2) / n
    my = sum(ys2) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs2, ys2))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs2))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys2))
    return round(num / (dx * dy), 4) if dx > 0 and dy > 0 else None


def fmt(v, d=2):
    return round(v, d) if v is not None else None


def pct_str(rate):
    if rate is None:
        return "—"
    return f"{round(rate * 100)}%"


def sign_str(v, d=2):
    if v is None:
        return "—"
    return f"+{v:.{d}f}" if v >= 0 else f"{v:.{d}f}"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

with open(AGG_PATH, encoding="utf-8") as f:
    agg: dict = json.load(f)

with open(ABS_PATH, encoding="utf-8") as f:
    abs_data: dict = json.load(f)

with open(CTX_PATH, encoding="utf-8") as f:
    ctx: dict = json.load(f)

league_2026 = ctx["league2026"]
pop_pcts = ctx["playerPercentiles2026"]

# Build reverse lookup: abs_key -> agg_name
agg_by_abs_key = {to_abs_key(name): name for name in agg}


# ---------------------------------------------------------------------------
# Helper: pull all bucket metrics for a player / season
# ---------------------------------------------------------------------------


def bucket_vals(agg_name: str, season: str, bucket: str):
    """Return dict with avg and swings for bat_speed and swing_length, or Nones."""
    empty = {
        "bat_speed": None,
        "bat_speed_swings": 0,
        "swing_len": None,
        "swing_len_swings": 0,
    }
    player = agg.get(agg_name)
    if not player:
        return empty
    s = player.get("seasons", {}).get(season)
    if not s:
        return empty
    b = s.get("buckets", {}).get(bucket, {})
    return {
        "bat_speed": b.get("batSpeed", {}).get("avg"),
        "bat_speed_swings": b.get("batSpeed", {}).get("swings", 0),
        "swing_len": b.get("swingLength", {}).get("avg"),
        "swing_len_swings": b.get("swingLength", {}).get("swings", 0),
    }


# ---------------------------------------------------------------------------
# Build the full joined dataset (every ABS player with swing data)
# ---------------------------------------------------------------------------

YEAR = "2026"
MIN_ALL_SW = 20  # minimum all-count swings to include in archetype analysis
# (lower than main analysis to keep more players)

players = []

for abs_key, abs_rec in abs_data.items():
    agg_name = agg_by_abs_key.get(abs_key)
    if not agg_name:
        continue

    all_b = bucket_vals(agg_name, YEAR, "all")
    ts_b = bucket_vals(agg_name, YEAR, "two_strikes")
    ea_b = bucket_vals(agg_name, YEAR, "early")
    ah_b = bucket_vals(agg_name, YEAR, "ahead")
    bh_b = bucket_vals(agg_name, YEAR, "behind")

    if all_b["bat_speed"] is None or all_b["bat_speed_swings"] < MIN_ALL_SW:
        continue

    has_ts = (
        ts_b["bat_speed"] is not None
        and ts_b["bat_speed_swings"] >= 15
        and all_b["swing_len"] is not None
    )

    ts_bat_delta = (ts_b["bat_speed"] - all_b["bat_speed"]) if has_ts else None
    ts_len_delta = (
        (ts_b["swing_len"] - all_b["swing_len"])
        if has_ts and ts_b["swing_len"] is not None and all_b["swing_len"] is not None
        else None
    )

    # Ahead-to-two-strike swing length gap (proxy for situational range)
    ah2ts_len = (
        (ah_b["swing_len"] - ts_b["swing_len"])
        if (ah_b["swing_len"] is not None and ts_b["swing_len"] is not None)
        else None
    )

    # Behind-count bat-speed drop (proxy for protection mode engagement)
    bh_bat_delta = (
        (bh_b["bat_speed"] - all_b["bat_speed"])
        if bh_b["bat_speed"] is not None
        else None
    )

    # Career two-strike length delta (stability / habit)
    career_ts_len = None
    car_all_b = bucket_vals(agg_name, "career", "all")
    car_ts_b = bucket_vals(agg_name, "career", "two_strikes")
    if (
        car_all_b["swing_len"] is not None
        and car_ts_b["swing_len"] is not None
        and car_ts_b["swing_len_swings"] >= 20
    ):
        career_ts_len = car_ts_b["swing_len"] - car_all_b["swing_len"]

    # tvse percentile within ABS cohort (computed later)
    players.append(
        {
            "name": abs_rec["name"],
            "agg_name": agg_name,
            "team": abs_rec["team"],
            # ABS raw
            "challenges": abs_rec["challenges"],
            "overturns": abs_rec["overturns"],
            "confirms": abs_rec["confirms"],
            "overturn_rate": abs_rec["overturnRate"],
            "walks_flipped": abs_rec["walksFlipped"],
            "ks_flipped": abs_rec["strikeoutsFlipped"],
            "net_for": abs_rec["netFor"],
            "tvse": abs_rec["totalVsExpected"],  # total vs expected
            "chal_against": abs_rec["challengesAgainst"],
            "otr_against": abs_rec["overturnRateAgainst"],
            # Swing profile
            "bat_speed": all_b["bat_speed"],
            "swing_len": all_b["swing_len"],
            "all_swings": all_b["bat_speed_swings"],
            "ts_bat_delta": ts_bat_delta,
            "ts_len_delta": ts_len_delta,
            "has_ts": has_ts,
            "ts_swings": ts_b["bat_speed_swings"],
            "ah2ts_len": ah2ts_len,
            "bh_bat_delta": bh_bat_delta,
            "career_ts_len": career_ts_len,
            # Derived
            "challenged": abs_rec["challenges"] > 0,
        }
    )

print(f"Joined dataset: {len(players)} players\n")

# ---------------------------------------------------------------------------
# Population medians for bat speed and swing length (to split archetypes)
# ---------------------------------------------------------------------------

all_bat_speeds = [p["bat_speed"] for p in players if p["bat_speed"] is not None]
all_swing_lens = [p["swing_len"] for p in players if p["swing_len"] is not None]

med_bat = safe_median(all_bat_speeds)
med_len = safe_median(all_swing_lens)
sd_bat = stdev(all_bat_speeds)
sd_len = stdev(all_swing_lens)

print(
    f"Population (n={len(players)}):  median bat speed={med_bat:.2f} mph  "
    f"median swing len={med_len:.2f} ft\n"
)


# ---------------------------------------------------------------------------
# ARCHETYPE CLASSIFICATION
#
# We use two dimensions:
#   1. Bat speed (relative to population median):  HIGH / LOW
#   2. Swing length (relative to population median): LONG / SHORT
#
# This gives four quadrants:
#   Fast + Long  = "Power"       (typical slugger profile)
#   Fast + Short = "Whip"        (elite bat speed, compact swing — rare)
#   Slow + Long  = "Loopy"       (long, moderate-speed swing — often free-swingers)
#   Slow + Short = "Contact"     (short, controlled swing)
#
# We also classify two-strike APPROACH type for players with enough data:
#   Protector  : ts_len_delta < -0.2  AND ts_bat_delta < -1.0
#   Decelerator: ts_bat_delta < -1.0  (slows but doesn't shorten much)
#   Shortener  : ts_len_delta < -0.2  (shortens but maintains speed)
#   Extender   : ts_len_delta > +0.2  OR ts_bat_delta > +1.0
#   Neutral    : everything else
# ---------------------------------------------------------------------------


def swing_archetype(bat_speed, swing_len):
    if bat_speed is None or swing_len is None:
        return "Unknown"
    fast = bat_speed >= med_bat
    long_ = swing_len >= med_len
    if fast and long_:
        return "Power"
    if fast and not long_:
        return "Whip"
    if not fast and long_:
        return "Loopy"
    return "Contact"


def approach_archetype(ts_bat_delta, ts_len_delta):
    if ts_bat_delta is None or ts_len_delta is None:
        return "Unknown"
    protects = ts_len_delta < -0.2 and ts_bat_delta < -1.0
    decelerates = ts_bat_delta < -1.0
    shortens = ts_len_delta < -0.2
    extends = ts_len_delta > +0.2 or ts_bat_delta > +1.0

    if protects:
        return "Protector"
    if decelerates and not shortens:
        return "Decelerator"
    if shortens and not decelerates:
        return "Shortener"
    if extends:
        return "Extender"
    return "Neutral"


for p in players:
    p["swing_arch"] = swing_archetype(p["bat_speed"], p["swing_len"])
    p["approach_arch"] = approach_archetype(p["ts_bat_delta"], p["ts_len_delta"])


# ---------------------------------------------------------------------------
# Group stats helper
# ---------------------------------------------------------------------------


def group_summary(grp, label):
    n = len(grp)
    challengers = [p for p in grp if p["challenged"]]
    nc = len(challengers)

    tvse_all = [p["tvse"] for p in grp if p["tvse"] is not None]
    otr_all = [
        p["overturn_rate"] for p in challengers if p["overturn_rate"] is not None
    ]
    chal_cnt = [p["challenges"] for p in grp]
    net_for = [p["net_for"] for p in challengers]
    ks = sum(p["ks_flipped"] for p in challengers)
    walks = sum(p["walks_flipped"] for p in challengers)
    otr_ag = [p["otr_against"] for p in grp if p["otr_against"] is not None]
    bh_delta = [p["bh_bat_delta"] for p in grp if p["bh_bat_delta"] is not None]
    ts_bat = [p["ts_bat_delta"] for p in grp if p["ts_bat_delta"] is not None]
    ts_len = [p["ts_len_delta"] for p in grp if p["ts_len_delta"] is not None]
    bs_vals = [p["bat_speed"] for p in grp if p["bat_speed"] is not None]
    sl_vals = [p["swing_len"] for p in grp if p["swing_len"] is not None]
    ah2ts = [p["ah2ts_len"] for p in grp if p["ah2ts_len"] is not None]

    return {
        "label": label,
        "n": n,
        "n_challengers": nc,
        "pct_challenged": fmt(nc / n * 100 if n else None, 1),
        "avg_bat_speed": fmt(safe_mean(bs_vals), 2),
        "avg_swing_len": fmt(safe_mean(sl_vals), 3),
        "avg_ts_bat_delta": fmt(safe_mean(ts_bat), 3),
        "avg_ts_len_delta": fmt(safe_mean(ts_len), 3),
        "avg_tvse": fmt(safe_mean(tvse_all), 3),
        "avg_overturn_rate": fmt(safe_mean(otr_all), 3),
        "avg_challenges": fmt(safe_mean(chal_cnt), 2),
        "avg_net_for": fmt(safe_mean(net_for), 3),
        "total_ks_flipped": ks,
        "total_walks_flipped": walks,
        "avg_otr_against": fmt(safe_mean(otr_ag), 3),
        "avg_bh_bat_delta": fmt(safe_mean(bh_delta), 3),
        "avg_ah2ts_len_gap": fmt(safe_mean(ah2ts), 3),
    }


# ---------------------------------------------------------------------------
# ANALYSIS A: Swing archetype vs ABS performance
# ---------------------------------------------------------------------------
print("=" * 70)
print("A. SWING ARCHETYPE vs ABS PERFORMANCE")
print("=" * 70)

arch_groups = {}
for arch in ["Power", "Whip", "Contact", "Loopy"]:
    grp = [p for p in players if p["swing_arch"] == arch]
    s = group_summary(grp, arch)
    arch_groups[arch] = s
    challengers_str = f"{s['n_challengers']}/{s['n']} challenged"
    print(
        f"\n  {arch:10s} ({challengers_str})"
        f"\n    bat_speed={s['avg_bat_speed']} mph   swing_len={s['avg_swing_len']} ft"
        f"\n    avg_tvse={sign_str(s['avg_tvse'])}   avg_overturn_rate={pct_str(s['avg_overturn_rate'])}"
        f"\n    ts_bat_delta={sign_str(s['avg_ts_bat_delta'], 3)}   ts_len_delta={sign_str(s['avg_ts_len_delta'], 3)}"
        f"\n    Ks avoided={s['total_ks_flipped']}   walks created={s['total_walks_flipped']}"
        f"\n    otr_against (how often opponents flip calls vs them)={pct_str(s['avg_otr_against'])}"
    )

# ---------------------------------------------------------------------------
# ANALYSIS B: Two-strike approach archetype vs ABS performance
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("B. TWO-STRIKE APPROACH ARCHETYPE vs ABS PERFORMANCE")
print("=" * 70)

approach_groups = {}
for arch in ["Protector", "Decelerator", "Shortener", "Neutral", "Extender", "Unknown"]:
    grp = [p for p in players if p["approach_arch"] == arch]
    if not grp:
        continue
    s = group_summary(grp, arch)
    approach_groups[arch] = s
    print(
        f"\n  {arch:14s} (n={s['n']}, {s['n_challengers']} challenged)"
        f"\n    avg_tvse={sign_str(s['avg_tvse'])}   avg_overturn_rate={pct_str(s['avg_overturn_rate'])}"
        f"\n    ts_bat_delta={sign_str(s['avg_ts_bat_delta'], 3)} mph   ts_len_delta={sign_str(s['avg_ts_len_delta'], 3)} ft"
    )

# ---------------------------------------------------------------------------
# ANALYSIS C: Who wins most vs expected? Granular player examination
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("C. BEST AND WORST ABS PERFORMERS — FULL PROFILE")
print("=" * 70)

challengers_only = [p for p in players if p["challenged"]]
tvse_sorted = sorted(challengers_only, key=lambda p: p["tvse"], reverse=True)


def full_profile(p):
    return (
        f"    {p['name']:26s} ({p['team']:3s})  "
        f"ABS={p['overturns']}/{p['challenges']}  "
        f"tvse={sign_str(p['tvse'])}  "
        f"swing={p['swing_arch']:8s}  "
        f"approach={p['approach_arch']:12s}  "
        f"bs={fmt(p['bat_speed'], 1)}  sl={fmt(p['swing_len'], 2)}  "
        f"ts_batΔ={sign_str(p['ts_bat_delta'], 2)}  ts_lenΔ={sign_str(p['ts_len_delta'], 3)}"
    )


print("\n  TOP 15 (total vs expected):")
for p in tvse_sorted[:15]:
    print(full_profile(p))

print("\n  BOTTOM 15 (total vs expected):")
for p in tvse_sorted[-15:]:
    print(full_profile(p))

# ---------------------------------------------------------------------------
# ANALYSIS D: Bat-speed quartile breakdown with approach archetype composition
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("D. BAT-SPEED QUARTILE × APPROACH ARCHETYPE COMPOSITION")
print("=" * 70)

bs_sorted = sorted(players, key=lambda p: p["bat_speed"] or 0)
q = len(bs_sorted) // 4
quartile_bins = [
    ("Q1 slowest", bs_sorted[:q]),
    ("Q2", bs_sorted[q : 2 * q]),
    ("Q3", bs_sorted[2 * q : 3 * q]),
    ("Q4 fastest", bs_sorted[3 * q :]),
]

quartile_arch_breakdown = []
for qlabel, grp in quartile_bins:
    qs = group_summary(grp, qlabel)
    approach_counts = defaultdict(int)
    for p in grp:
        approach_counts[p["approach_arch"]] += 1
    prot_pct = approach_counts["Protector"] / len(grp) * 100 if grp else 0
    print(
        f"\n  {qlabel:14s}  bat=[{fmt(grp[0]['bat_speed'], 1)}-{fmt(grp[-1]['bat_speed'], 1)}]  "
        f"n={len(grp)}  "
        f"tvse={sign_str(qs['avg_tvse'])}  "
        f"win%={pct_str(qs['avg_overturn_rate'])}"
    )
    print(f"    Approach split: ", end="")
    for arch in [
        "Protector",
        "Decelerator",
        "Shortener",
        "Neutral",
        "Extender",
        "Unknown",
    ]:
        cnt = approach_counts.get(arch, 0)
        if cnt:
            print(f"{arch}={cnt}", end="  ")
    print()
    quartile_arch_breakdown.append(
        {
            "quartile": qlabel,
            "n": len(grp),
            "bat_range": [fmt(grp[0]["bat_speed"], 1), fmt(grp[-1]["bat_speed"], 1)],
            "summary": qs,
            "approach_counts": dict(approach_counts),
        }
    )

# ---------------------------------------------------------------------------
# ANALYSIS E: Ahead-to-two-strike swing gap as zone-reading proxy
#
# Hypothesis: a hitter who swings MUCH longer when ahead (hacking) but
# compresses sharply with two strikes is a good "situational reader" —
# and should therefore also recognise and challenge bad called strikes well.
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("E. SITUATIONAL-RANGE (ahead→2-strike length gap) vs ABS SUCCESS")
print("=" * 70)

with_gap = [p for p in players if p["ah2ts_len"] is not None]
r_gap_tvse = pearson_r(
    [p["ah2ts_len"] for p in with_gap], [p["tvse"] for p in with_gap]
)
r_gap_otr = pearson_r(
    [p["ah2ts_len"] for p in with_gap if p["challenged"]],
    [
        p["overturn_rate"]
        for p in with_gap
        if p["challenged"] and p["overturn_rate"] is not None
    ],
)

# Tertile split by gap size
gap_sorted = sorted(with_gap, key=lambda p: p["ah2ts_len"], reverse=True)
t = len(gap_sorted) // 3
gap_groups = [
    ("Wide gap (range readers)", gap_sorted[:t]),
    ("Moderate gap", gap_sorted[t : 2 * t]),
    ("Narrow gap (flat approach)", gap_sorted[2 * t :]),
]
print(f"\n  Pearson r (ah→2s length gap vs tvse): {r_gap_tvse}")
print(f"  Pearson r (ah→2s length gap vs overturn rate): {r_gap_otr}")
gap_group_results = []
for label, grp in gap_groups:
    gs = group_summary(grp, label)
    print(
        f"\n  {label:30s}  n={gs['n']}  "
        f"avg_gap={fmt(safe_mean([p['ah2ts_len'] for p in grp]), 3)} ft  "
        f"tvse={sign_str(gs['avg_tvse'])}  win%={pct_str(gs['avg_overturn_rate'])}"
    )
    gap_group_results.append(
        {
            "label": label,
            "n": gs["n"],
            "avg_gap": fmt(safe_mean([p["ah2ts_len"] for p in grp]), 3),
            "summary": gs,
        }
    )

# ---------------------------------------------------------------------------
# ANALYSIS F: "Leaky takers" — players who give up overturns AGAINST them
#
# If a fielder successfully challenges a called ball to flip it to a strike,
# that's an overturn "against" the batter. These are called balls (presumably
# on borderline pitches) that the batter DIDN'T challenge even though the ABS
# system agreed they were strikes. Batters with high otr_against are letting
# bad calls slide.
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("F. 'LEAKY TAKERS' — WHO GIVES UP THE MOST OVERTURNS AGAINST THEM")
print("=" * 70)

with_against = [
    p for p in players if p["chal_against"] > 0 and p["otr_against"] is not None
]
leaky = sorted(
    with_against, key=lambda p: (p["otr_against"], p["chal_against"]), reverse=True
)

print(f"\n  Players with challenges made AGAINST them (n={len(with_against)}):")
print(
    f"  {'Name':26s}  {'otr_against':12s}  {'chal_against':13s}  {'swing_arch':10s}  {'approach':12s}"
)
for p in leaky[:20]:
    print(
        f"    {p['name']:26s}  {pct_str(p['otr_against']):12s}  "
        f"{p['chal_against']:13d}  {p['swing_arch']:10s}  {p['approach_arch']:12s}"
    )

# Summarise leaky by swing archetype
leaky_by_arch = defaultdict(list)
for p in with_against:
    leaky_by_arch[p["swing_arch"]].append(p["otr_against"])

print("\n  Average otr_against by swing archetype:")
for arch in ["Power", "Whip", "Contact", "Loopy"]:
    vals = leaky_by_arch.get(arch, [])
    if vals:
        print(f"    {arch:10s}: {pct_str(safe_mean(vals))}  (n={len(vals)})")

r_bs_otr_against = pearson_r(
    [p["bat_speed"] for p in with_against], [p["otr_against"] for p in with_against]
)
print(f"\n  Pearson r (bat_speed vs otr_against): {r_bs_otr_against}")

# ---------------------------------------------------------------------------
# ANALYSIS G: Behind-count bat-speed drop as pitch-discipline proxy
#
# Hitters who slow down a lot when behind in the count (0-2, 1-2) are in
# "protect the plate" mode. Do they translate this mode into better ABS
# challenge decisions?
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("G. BEHIND-COUNT DECELERATION vs ABS PERFORMANCE")
print("=" * 70)

with_bh = [p for p in players if p["bh_bat_delta"] is not None]
r_bh_tvse = pearson_r(
    [p["bh_bat_delta"] for p in with_bh], [p["tvse"] for p in with_bh]
)
r_bh_otr = pearson_r(
    [
        p["bh_bat_delta"]
        for p in with_bh
        if p["challenged"] and p["overturn_rate"] is not None
    ],
    [
        p["overturn_rate"]
        for p in with_bh
        if p["challenged"] and p["overturn_rate"] is not None
    ],
)
print(f"\n  n = {len(with_bh)}")
print(f"  Pearson r (behind-count bat delta vs tvse): {r_bh_tvse}")
print(f"  Pearson r (behind-count bat delta vs overturn rate): {r_bh_otr}")

# Tertile split: big droppers vs small droppers
bh_sorted = sorted(with_bh, key=lambda p: p["bh_bat_delta"])
tb = len(bh_sorted) // 3
bh_groups = [
    ("Big droppers (≤-2 mph behind)", bh_sorted[:tb]),
    ("Moderate droppers", bh_sorted[tb : 2 * tb]),
    ("Flat / gainers", bh_sorted[2 * tb :]),
]
bh_group_results = []
for label, grp in bh_groups:
    gs = group_summary(grp, label)
    avg_bh = safe_mean([p["bh_bat_delta"] for p in grp])
    print(
        f"\n  {label:33s}  n={gs['n']}  "
        f"avg_bh_bat_delta={sign_str(avg_bh, 2)} mph  "
        f"tvse={sign_str(gs['avg_tvse'])}  win%={pct_str(gs['avg_overturn_rate'])}"
    )
    bh_group_results.append(
        {
            "label": label,
            "n": gs["n"],
            "avg_bh_bat_delta": fmt(avg_bh, 3),
            "summary": gs,
        }
    )

# ---------------------------------------------------------------------------
# ANALYSIS H: Career habit consistency — does the career ts_len_delta
# (established habit of how much a hitter shortens in 2-strike counts)
# predict ABS success better than the 2026 in-season number?
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("H. CAREER TWO-STRIKE HABIT vs ABS SUCCESS")
print("=" * 70)

with_career = [p for p in players if p["career_ts_len"] is not None]
r_career_tvse = pearson_r(
    [p["career_ts_len"] for p in with_career], [p["tvse"] for p in with_career]
)
r_career_otr = pearson_r(
    [
        p["career_ts_len"]
        for p in with_career
        if p["challenged"] and p["overturn_rate"] is not None
    ],
    [
        p["overturn_rate"]
        for p in with_career
        if p["challenged"] and p["overturn_rate"] is not None
    ],
)
r_2026_tvse = pearson_r(
    [p["ts_len_delta"] for p in players if p["ts_len_delta"] is not None],
    [p["tvse"] for p in players if p["ts_len_delta"] is not None],
)
print(f"\n  n with career data = {len(with_career)}")
print(f"  Pearson r (CAREER ts_len_delta vs tvse): {r_career_tvse}")
print(f"  Pearson r (2026 in-season ts_len_delta vs tvse): {r_2026_tvse}")
print(f"  Pearson r (career ts_len_delta vs overturn rate): {r_career_otr}")

# Identify "changed habits" — players whose 2026 ts_len is very different from career
habit_shifts = []
for p in with_career:
    if p["ts_len_delta"] is not None:
        shift = p["ts_len_delta"] - p["career_ts_len"]
        habit_shifts.append({**p, "habit_shift": shift})

habit_shifts.sort(key=lambda p: p["habit_shift"])
print(
    "\n  Players who shortened MOST relative to career habit (possible ABS adaptation):"
)
for p in habit_shifts[:10]:
    print(
        f"    {p['name']:26s}  career_ts_len={sign_str(p['career_ts_len'], 3)}  "
        f"2026_ts_len={sign_str(p['ts_len_delta'], 3)}  "
        f"shift={sign_str(p['habit_shift'], 3)}  "
        f"ABS={p['overturns']}/{p['challenges']}  tvse={sign_str(p['tvse'])}"
    )

print(
    "\n  Players who EXTENDED most relative to career habit (possibly distracted by ABS):"
)
for p in habit_shifts[-10:]:
    print(
        f"    {p['name']:26s}  career_ts_len={sign_str(p['career_ts_len'], 3)}  "
        f"2026_ts_len={sign_str(p['ts_len_delta'], 3)}  "
        f"shift={sign_str(p['habit_shift'], 3)}  "
        f"ABS={p['overturns']}/{p['challenges']}  tvse={sign_str(p['tvse'])}"
    )

# ---------------------------------------------------------------------------
# ANALYSIS I: Zone-edge profile
#
# Best ABS challengers should be taking pitches near the zone edge —
# they challenge called strikes that are just barely off the plate.
# Proxy: "contact" / "whip" hitters with short swing length and high bat speed
# may have better zone-edge awareness than long-swinging power hitters.
# Use swing_len as the proxy for zone-width: shorter swing = quicker path
# = can lay off later = more borderline takes = more challengeable pitches.
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("I. SWING LENGTH AS ZONE-EDGE PROXY")
print("=" * 70)

r_sl_tvse = pearson_r(
    [p["swing_len"] for p in players if p["swing_len"] is not None],
    [p["tvse"] for p in players if p["swing_len"] is not None],
)
r_sl_otr = pearson_r(
    [
        p["swing_len"]
        for p in players
        if p["swing_len"] is not None
        and p["challenged"]
        and p["overturn_rate"] is not None
    ],
    [
        p["overturn_rate"]
        for p in players
        if p["swing_len"] is not None
        and p["challenged"]
        and p["overturn_rate"] is not None
    ],
)
r_bs_tvse = pearson_r(
    [p["bat_speed"] for p in players if p["bat_speed"] is not None],
    [p["tvse"] for p in players],
)
print(f"\n  Pearson r (swing_length vs tvse): {r_sl_tvse}")
print(f"  Pearson r (swing_length vs overturn rate): {r_sl_otr}")
print(f"  Pearson r (bat_speed vs tvse): {r_bs_tvse}")

# Swing length quintiles vs ABS
sl_sorted = sorted(players, key=lambda p: p["swing_len"] or 0)
qn = len(sl_sorted) // 5
sl_quintile_results = []
for i, label in enumerate(["Q1 (shortest)", "Q2", "Q3", "Q4", "Q5 (longest)"]):
    grp = sl_sorted[i * qn : (i + 1) * qn] if i < 4 else sl_sorted[i * qn :]
    gs = group_summary(grp, label)
    avg_sl = safe_mean([p["swing_len"] for p in grp])
    print(
        f"  {label:16s}: sl={fmt(avg_sl, 2)}  tvse={sign_str(gs['avg_tvse'])}  "
        f"win%={pct_str(gs['avg_overturn_rate'])}  n={gs['n']}"
    )
    sl_quintile_results.append(
        {"label": label, "n": gs["n"], "avg_swing_len": fmt(avg_sl, 3), "summary": gs}
    )

# ---------------------------------------------------------------------------
# ANALYSIS J: Cross-dimension winners
#
# The "ideal" ABS challenger: moderate or compact swing + disciplined approach
# Find players who are both (a) in the top half of tvse AND
# (b) have specific swing/approach characteristics.
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("J. THE IDEAL ABS CHALLENGER — MULTI-FACTOR WINNERS")
print("=" * 70)

# Top half of tvse (among challengers)
tvse_vals = sorted([p["tvse"] for p in challengers_only])
tvse_median = safe_median(tvse_vals)
top_performers = [p for p in challengers_only if p["tvse"] >= (tvse_median or 0)]
bottom_performers = [p for p in challengers_only if p["tvse"] < (tvse_median or 0)]

print(f"\n  Challengers: n={len(challengers_only)}  tvse_median={fmt(tvse_median)}")

tp_arch = defaultdict(int)
bp_arch = defaultdict(int)
tp_approach = defaultdict(int)
bp_approach = defaultdict(int)

for p in top_performers:
    tp_arch[p["swing_arch"]] += 1
    tp_approach[p["approach_arch"]] += 1

for p in bottom_performers:
    bp_arch[p["swing_arch"]] += 1
    bp_approach[p["approach_arch"]] += 1

print("\n  Swing archetype distribution:")
print(f"    {'Arch':12s}  {'Top half':12s}  {'Bottom half':12s}  Diff")
for arch in ["Power", "Whip", "Contact", "Loopy"]:
    tp_n = tp_arch.get(arch, 0)
    bp_n = bp_arch.get(arch, 0)
    tp_pct = tp_n / len(top_performers) * 100 if top_performers else 0
    bp_pct = bp_n / len(bottom_performers) * 100 if bottom_performers else 0
    print(
        f"    {arch:12s}  {tp_pct:5.1f}%  ({tp_n:3d})  {bp_pct:5.1f}%  ({bp_n:3d})  {tp_pct - bp_pct:+.1f} pp"
    )

print("\n  Approach archetype distribution:")
print(f"    {'Approach':14s}  {'Top half':12s}  {'Bottom half':12s}  Diff")
for arch in ["Protector", "Decelerator", "Shortener", "Neutral", "Extender", "Unknown"]:
    tp_n = tp_approach.get(arch, 0)
    bp_n = bp_approach.get(arch, 0)
    tp_pct = tp_n / len(top_performers) * 100 if top_performers else 0
    bp_pct = bp_n / len(bottom_performers) * 100 if bottom_performers else 0
    print(
        f"    {arch:14s}  {tp_pct:5.1f}%  ({tp_n:3d})  {bp_pct:5.1f}%  ({bp_n:3d})  {tp_pct - bp_pct:+.1f} pp"
    )

# Key cross stats
print(
    f"\n  Top-half vs bottom-half avg bat speed: "
    f"{fmt(safe_mean([p['bat_speed'] for p in top_performers]), 2)} vs "
    f"{fmt(safe_mean([p['bat_speed'] for p in bottom_performers]), 2)} mph"
)
print(
    f"  Top-half vs bottom-half avg swing len: "
    f"{fmt(safe_mean([p['swing_len'] for p in top_performers if p['swing_len']]), 3)} vs "
    f"{fmt(safe_mean([p['swing_len'] for p in bottom_performers if p['swing_len']]), 3)} ft"
)
print(
    f"  Top-half vs bottom-half avg ts_bat_delta: "
    f"{fmt(safe_mean([p['ts_bat_delta'] for p in top_performers if p['ts_bat_delta']]), 3)} vs "
    f"{fmt(safe_mean([p['ts_bat_delta'] for p in bottom_performers if p['ts_bat_delta']]), 3)} mph"
)
print(
    f"  Top-half vs bottom-half avg ts_len_delta: "
    f"{fmt(safe_mean([p['ts_len_delta'] for p in top_performers if p['ts_len_delta']]), 3)} vs "
    f"{fmt(safe_mean([p['ts_len_delta'] for p in bottom_performers if p['ts_len_delta']]), 3)} ft"
)

# ---------------------------------------------------------------------------
# ANALYSIS K: Team-level ABS culture
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("K. TEAM-LEVEL ABS PATTERNS")
print("=" * 70)

by_team = defaultdict(list)
for p in players:
    by_team[p["team"]].append(p)

team_summaries = []
for team, grp in by_team.items():
    gs = group_summary(grp, team)
    team_summaries.append(gs)

team_summaries.sort(
    key=lambda s: s["avg_tvse"] if s["avg_tvse"] is not None else -999, reverse=True
)

print(
    f"\n  {'Team':6s}  {'n':4s}  {'avg_tvse':9s}  {'win%':7s}  {'avg_bs':8s}  {'avg_sl':8s}"
)
for ts in team_summaries:
    print(
        f"  {ts['label']:6s}  {ts['n']:4d}  "
        f"{sign_str(ts['avg_tvse']):9s}  "
        f"{pct_str(ts['avg_overturn_rate']):7s}  "
        f"{fmt(ts['avg_bat_speed'], 1) or '—':8}  "
        f"{fmt(ts['avg_swing_len'], 2) or '—':8}"
    )

# ---------------------------------------------------------------------------
# Compile and write output
# ---------------------------------------------------------------------------

results = {
    "meta": {
        "n_players": len(players),
        "n_challengers": len(challengers_only),
        "median_bat_speed": fmt(med_bat),
        "median_swing_len": fmt(med_len),
        "sd_bat_speed": fmt(sd_bat),
        "sd_swing_len": fmt(sd_len),
    },
    "analysis_A_swing_archetypes": list(arch_groups.values()),
    "analysis_B_approach_archetypes": list(approach_groups.values()),
    "analysis_C_top15_players": [
        {
            "name": p["name"],
            "team": p["team"],
            "swing_arch": p["swing_arch"],
            "approach_arch": p["approach_arch"],
            "bat_speed": fmt(p["bat_speed"], 1),
            "swing_len": fmt(p["swing_len"], 2),
            "ts_bat_delta": fmt(p["ts_bat_delta"], 2),
            "ts_len_delta": fmt(p["ts_len_delta"], 3),
            "challenges": p["challenges"],
            "overturns": p["overturns"],
            "tvse": fmt(p["tvse"]),
        }
        for p in tvse_sorted[:15]
    ],
    "analysis_C_bottom15_players": [
        {
            "name": p["name"],
            "team": p["team"],
            "swing_arch": p["swing_arch"],
            "approach_arch": p["approach_arch"],
            "bat_speed": fmt(p["bat_speed"], 1),
            "swing_len": fmt(p["swing_len"], 2),
            "ts_bat_delta": fmt(p["ts_bat_delta"], 2),
            "ts_len_delta": fmt(p["ts_len_delta"], 3),
            "challenges": p["challenges"],
            "overturns": p["overturns"],
            "tvse": fmt(p["tvse"]),
        }
        for p in tvse_sorted[-15:]
    ],
    "analysis_D_quartile_breakdown": quartile_arch_breakdown,
    "analysis_E_situational_range": {
        "pearson_r_gap_vs_tvse": r_gap_tvse,
        "pearson_r_gap_vs_overturn_rate": r_gap_otr,
        "groups": gap_group_results,
    },
    "analysis_F_leaky_takers": {
        "n_with_challenges_against": len(with_against),
        "r_bat_speed_vs_otr_against": r_bs_otr_against,
        "by_swing_arch": {
            arch: fmt(safe_mean(leaky_by_arch.get(arch, [])), 3)
            for arch in ["Power", "Whip", "Contact", "Loopy"]
        },
        "top20_most_overturned_against": [
            {
                "name": p["name"],
                "team": p["team"],
                "otr_against": fmt(p["otr_against"], 3),
                "chal_against": p["chal_against"],
                "swing_arch": p["swing_arch"],
                "approach_arch": p["approach_arch"],
            }
            for p in leaky[:20]
        ],
    },
    "analysis_G_behind_count_deceleration": {
        "pearson_r_bh_bat_delta_vs_tvse": r_bh_tvse,
        "pearson_r_bh_bat_delta_vs_overturn_rate": r_bh_otr,
        "groups": bh_group_results,
    },
    "analysis_H_career_habit": {
        "n_with_career_data": len(with_career),
        "pearson_r_career_ts_len_vs_tvse": r_career_tvse,
        "pearson_r_2026_ts_len_vs_tvse": r_2026_tvse,
        "pearson_r_career_ts_len_vs_overturn_rate": r_career_otr,
        "most_shortened_vs_habit": [
            {
                "name": p["name"],
                "career_ts_len": fmt(p["career_ts_len"], 3),
                "ts_len_2026": fmt(p["ts_len_delta"], 3),
                "habit_shift": fmt(p["habit_shift"], 3),
                "overturns": p["overturns"],
                "challenges": p["challenges"],
                "tvse": fmt(p["tvse"]),
            }
            for p in habit_shifts[:10]
        ],
        "most_extended_vs_habit": [
            {
                "name": p["name"],
                "career_ts_len": fmt(p["career_ts_len"], 3),
                "ts_len_2026": fmt(p["ts_len_delta"], 3),
                "habit_shift": fmt(p["habit_shift"], 3),
                "overturns": p["overturns"],
                "challenges": p["challenges"],
                "tvse": fmt(p["tvse"]),
            }
            for p in habit_shifts[-10:]
        ],
    },
    "analysis_I_swing_length_zone_edge": {
        "pearson_r_sl_vs_tvse": r_sl_tvse,
        "pearson_r_sl_vs_overturn_rate": r_sl_otr,
        "pearson_r_bs_vs_tvse": r_bs_tvse,
        "swing_len_quintiles": sl_quintile_results,
    },
    "analysis_J_multi_factor": {
        "tvse_median": fmt(tvse_median),
        "n_top_half": len(top_performers),
        "n_bottom_half": len(bottom_performers),
        "top_half_avg_bat_speed": fmt(
            safe_mean([p["bat_speed"] for p in top_performers]), 2
        ),
        "bottom_half_avg_bat_speed": fmt(
            safe_mean([p["bat_speed"] for p in bottom_performers]), 2
        ),
        "top_half_avg_swing_len": fmt(
            safe_mean([p["swing_len"] for p in top_performers if p["swing_len"]]), 3
        ),
        "bottom_half_avg_swing_len": fmt(
            safe_mean([p["swing_len"] for p in bottom_performers if p["swing_len"]]), 3
        ),
        "top_half_avg_ts_bat_delta": fmt(
            safe_mean([p["ts_bat_delta"] for p in top_performers if p["ts_bat_delta"]]),
            3,
        ),
        "bottom_half_avg_ts_bat_delta": fmt(
            safe_mean(
                [p["ts_bat_delta"] for p in bottom_performers if p["ts_bat_delta"]]
            ),
            3,
        ),
        "top_half_avg_ts_len_delta": fmt(
            safe_mean([p["ts_len_delta"] for p in top_performers if p["ts_len_delta"]]),
            3,
        ),
        "bottom_half_avg_ts_len_delta": fmt(
            safe_mean(
                [p["ts_len_delta"] for p in bottom_performers if p["ts_len_delta"]]
            ),
            3,
        ),
        "swing_arch_top_half": dict(tp_arch),
        "swing_arch_bottom_half": dict(bp_arch),
        "approach_arch_top_half": dict(tp_approach),
        "approach_arch_bottom_half": dict(bp_approach),
    },
    "analysis_K_team_level": team_summaries,
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\n\nResults written to {OUT_PATH}")
print(f"Size: {os.path.getsize(OUT_PATH) / 1024:.1f} KB")
