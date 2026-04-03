#!/usr/bin/env python3
"""
Download ABS (Automated Ball-Strike) challenge leaderboard data from Baseball Savant
for the 2026 season and write data/abs_2026.json keyed by normalized player name.

Usage:
    python3 scripts/download_abs.py
"""

import csv
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request


URL = (
    "https://baseballsavant.mlb.com/leaderboard/abs-challenges"
    "?year=2026&type=batter&min=0&csv=true"
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "abs_2026.json")


def strip_accents(s: str) -> str:
    """Remove diacritical marks from a unicode string."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(entity_name: str) -> str:
    """
    Convert an entity_name from Baseball Savant to a normalized lookup key.

    Savant returns names in "First Last" format.  We:
      1. Strip leading/trailing whitespace
      2. Remove diacritical marks  (Teóscar -> Teoscar, Báez -> Baez)
      3. Strip common name suffixes (Jr., Sr., II, III …)
      4. Lowercase the result

    Examples:
        "Elly De La Cruz"      -> "elly de la cruz"
        "Teoscar Hernandez"    -> "teoscar hernandez"
        "Jazz Chisholm Jr."    -> "jazz chisholm"
        "Vladimir Guerrero Jr."-> "vladimir guerrero"
        "Ronald Acuna Jr."     -> "ronald acuna"
    """
    name = strip_accents(entity_name.strip())
    # Remove trailing generational suffixes (case-insensitive)
    name = re.sub(
        r"\s+(jr\.?|sr\.?|ii|iii|iv|v)$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    return name.lower()


def parse_float(value: str) -> float | None:
    """Return a float or None if the value is empty / non-numeric."""
    v = value.strip()
    if v in ("", "null", "NULL", "N/A", "NA", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_int(value: str) -> int:
    """Return an int, defaulting to 0 for empty / non-numeric values."""
    v = value.strip()
    if v in ("", "null", "NULL", "N/A", "NA", "-"):
        return 0
    try:
        return int(float(v))
    except ValueError:
        return 0


def fetch_csv(url: str) -> str:
    print(f"Fetching: {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; SwingsplitsBot/1.0; "
                "+https://github.com/swingsplits)"
            ),
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # Baseball Savant returns UTF-8 (sometimes with a BOM); strip BOM via
    # utf-8-sig, fall back to latin-1 if needed.
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def build_record(row: dict) -> dict:
    """
    Map a CSV row dict to the output AbsStats shape.

    CSV columns used:
        entity_name, team_abbr,
        n_challenges, n_overturns, n_confirms, rate_overturns,
        n_walks_flip, n_strikeouts_flip,
        net_for, total_vs_expected,
        n_challenges_against, n_overturns_against, n_confirms_against,
        rate_overturns_against
    """
    challenges = parse_int(row.get("n_challenges", ""))
    overturns = parse_int(row.get("n_overturns", ""))
    confirms = parse_int(row.get("n_confirms", ""))
    raw_rate = parse_float(row.get("rate_overturns", ""))
    overturn_rate = raw_rate if (challenges > 0 and raw_rate is not None) else None

    challenges_against = parse_int(row.get("n_challenges_against", ""))
    overturns_against = parse_int(row.get("n_overturns_against", ""))
    confirms_against = parse_int(row.get("n_confirms_against", ""))
    raw_rate_against = parse_float(row.get("rate_overturns_against", ""))
    overturn_rate_against = (
        raw_rate_against
        if (challenges_against > 0 and raw_rate_against is not None)
        else None
    )

    net_for = parse_float(row.get("net_for", "")) or 0.0
    total_vs_expected = parse_float(row.get("total_vs_expected", "")) or 0.0

    return {
        "name": row.get("entity_name", "").strip(),
        "team": row.get("team_abbr", "").strip().upper(),
        "challenges": challenges,
        "overturns": overturns,
        "confirms": confirms,
        "overturnRate": overturn_rate,
        "walksFlipped": parse_int(row.get("n_walks_flip", "")),
        "strikeoutsFlipped": parse_int(row.get("n_strikeouts_flip", "")),
        "netFor": round(net_for, 4) if net_for is not None else 0.0,
        "totalVsExpected": round(total_vs_expected, 4) if total_vs_expected is not None else 0.0,
        "challengesAgainst": challenges_against,
        "overturnsAgainst": overturns_against,
        "confirmsAgainst": confirms_against,
        "overturnRateAgainst": overturn_rate_against,
    }


def main() -> None:
    try:
        text = fetch_csv(URL)
    except Exception as exc:
        print(f"ERROR: Failed to download ABS data: {exc}", file=sys.stderr)
        sys.exit(1)

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        print("WARNING: CSV contained no data rows.", file=sys.stderr)

    output: dict = {}
    skipped = 0

    for row in rows:
        entity_name = row.get("entity_name", "").strip()
        if not entity_name:
            skipped += 1
            continue

        key = normalize_name(entity_name)
        record = build_record(row)
        output[key] = record

    out_path = os.path.abspath(OUT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(
        f"Wrote {len(output)} player records to {out_path}"
        + (f" ({skipped} rows skipped)" if skipped else "")
    )


if __name__ == "__main__":
    main()
