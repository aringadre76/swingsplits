import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import "./index.css";
import type { AggregatesMeta, HitterAggregates, HitterBucketKey, HitterBucketRow } from "./types";
import { fetchAggregates, fetchMeta } from "./data";

const BUCKET_LABELS: Record<HitterBucketKey, string> = {
  all: "All Counts",
  early: "Early (0-0, 1-0, 0-1)",
  ahead: "Ahead (2-0, 3-0, 3-1, 2-1)",
  behind: "Behind (0-2, 1-2)",
  two_strikes: "Two Strikes"
};

const BAT_SPEED_DELTA = 1;
const SWING_LENGTH_DELTA = 0.2;
const MIN_SEASON_YEAR = 2023;
const SEARCH_DEBOUNCE_MS = 200;
const MIN_INSIGHT_SWINGS = 100;

const BUCKET_SHORT_LABELS: Record<Exclude<HitterBucketKey, "all">, string> = {
  early: "Early",
  ahead: "Ahead",
  behind: "Behind",
  two_strikes: "Two Strikes"
};

function classifyDelta(value: number | null, baseline: number | null, threshold: number) {
  if (value === null || baseline === null) return { cls: "text-muted-foreground", text: "–" };
  const diff = value - baseline;
  if (Math.abs(diff) < threshold) return { cls: "text-muted-foreground", text: "±0.0" };
  const sign = diff > 0 ? "+" : "";
  return {
    cls: diff > 0 ? "text-emerald-400" : "text-rose-400",
    text: `${sign}${diff.toFixed(1)}`
  };
}

function formatAvg(value: number | null, digits = 1) {
  if (value === null) return "–";
  return value.toFixed(digits);
}

function formatSigned(value: number, digits = 1) {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(digits)}`;
}

function sortNames(names: string[]) {
  return [...names].sort((a, b) => a.localeCompare(b));
}

function normalizeName(value: string) {
  return value.toLowerCase().replace(/,/g, " ").replace(/\s+/g, " ").trim();
}

function formatPlayerDisplayName(raw: string) {
  const value = raw.trim();
  if (!value) return value;

  const suffixMap: Record<string, string> = {
    jr: "Jr.",
    "jr.": "Jr.",
    sr: "Sr.",
    "sr.": "Sr."
  };

  const roman = /^(i|ii|iii|iv|v|vi|vii|viii|ix|x)$/i;

  const capSegment = (seg: string) => {
    if (!seg) return seg;
    return seg[0]!.toUpperCase() + seg.slice(1).toLowerCase();
  };

  const capWord = (word: string) => {
    const w = word.trim();
    if (!w) return w;

    const lower = w.toLowerCase();
    if (suffixMap[lower]) return suffixMap[lower]!;
    if (roman.test(w)) return w.toUpperCase();

    // preserve punctuation but title-case the letter segments
    const hyphenParts = w.split("-").map(part => {
      const aposParts = part.split("'").map(p => {
        const pLower = p.toLowerCase();
        if (pLower.startsWith("mc") && p.length > 2) {
          return "Mc" + capSegment(p.slice(2));
        }
        return capSegment(p);
      });
      return aposParts.join("'");
    });
    return hyphenParts.join("-");
  };

  const toTitle = (s: string) =>
    s
      .split(/\s+/g)
      .filter(Boolean)
      .map(capWord)
      .join(" ");

  if (value.includes(",")) {
    const [lastRaw, ...rest] = value.split(",");
    const firstRaw = rest.join(",").trim();
    const last = toTitle(lastRaw ?? "");
    const first = toTitle(firstRaw);
    if (!first) return last;
    if (!last) return first;
    return `${first} ${last}`;
  }

  return toTitle(value);
}

function getSeasonInitial(meta: AggregatesMeta | null): string {
  if (!meta || meta.availableSeasons.length === 0) return "career";
  const eligible = meta.availableSeasons
    .map(value => Number(value))
    .filter(value => Number.isFinite(value) && value >= MIN_SEASON_YEAR)
    .sort((a, b) => a - b);
  if (eligible.length === 0) return "career";
  return String(eligible[eligible.length - 1]);
}

export function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
    return () => {
      document.documentElement.classList.remove("dark");
    };
  }, []);

  const [aggregates, setAggregates] = useState<HitterAggregates | null>(null);
  const [meta, setMeta] = useState<AggregatesMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [season, setSeason] = useState<string>("career");
  const [autoSeasonHitter, setAutoSeasonHitter] = useState<string | null>(null);

  useEffect(() => {
    if (search.trim() === "") {
      setSelectedName(null);
    }
  }, [search]);

  useEffect(() => {
    if (search.trim() === "") {
      setDebouncedSearch("");
      return;
    }
    const handle = setTimeout(() => {
      setDebouncedSearch(search);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [search]);

  useEffect(() => {
    let canceled = false;
    async function load() {
      try {
        const [agg, m] = await Promise.all([fetchAggregates(), fetchMeta()]);
        if (canceled) return;
        setAggregates(agg);
        setMeta(m);
        if (m && m.availableSeasons.length > 0) {
          setSeason(getSeasonInitial(m));
        }
      } catch {
        if (!canceled) {
          setLoadError("Failed to load data");
        }
      } finally {
        if (!canceled) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      canceled = true;
    };
  }, []);

  const seasons = useMemo(() => {
    const list = meta?.availableSeasons ?? [];
    return list.filter(year => Number(year) >= MIN_SEASON_YEAR);
  }, [meta]);

  const allNames = useMemo(() => {
    if (!aggregates) return [];
    return sortNames(Object.keys(aggregates));
  }, [aggregates]);

  const filteredNames = useMemo(() => {
    if (!aggregates) return [];
    const normQuery = normalizeName(debouncedSearch);
    if (!normQuery) return allNames;
    const tokens = normQuery.split(" ");
    return allNames.filter(name => {
      const normName = normalizeName(name);
      return tokens.every(token => normName.includes(token));
    });
  }, [aggregates, allNames, debouncedSearch]);

  useEffect(() => {
    if (!aggregates) return;
    const query = debouncedSearch.trim();
    if (query === "") return;

    const norm = normalizeName(query);
    const exact = allNames.find(name => normalizeName(name) === norm) ?? null;
    const first = filteredNames[0] ?? null;
    const chosen = exact ?? first ?? null;
    setSelectedName(chosen);

    if (chosen && chosen !== autoSeasonHitter) {
      const hitter = aggregates[chosen];
      const hitterSeasons = Object.keys(hitter.seasons).filter(
        key => key !== "career" && Number(key) >= MIN_SEASON_YEAR
      );
      if (hitterSeasons.length > 0) {
        const latest = hitterSeasons.sort((a, b) => Number(a) - Number(b))[
          hitterSeasons.length - 1
        ];
        if (latest) setSeason(latest);
      } else {
        setSeason("career");
      }
      setAutoSeasonHitter(chosen);
    }
  }, [aggregates, allNames, autoSeasonHitter, debouncedSearch, filteredNames]);

  const selectedHitter = selectedName && aggregates ? aggregates[selectedName] : null;

  const seasonKey = season === "career" ? "career" : season;
  const seasonData = selectedHitter ? selectedHitter.seasons[seasonKey] ?? null : null;
  const careerData = selectedHitter ? selectedHitter.seasons.career ?? null : null;

  useEffect(() => {
    if (season === "career") return;
    if (!seasons.includes(season)) {
      setSeason("career");
    }
  }, [season, seasons]);

  const hasAnySwings = useMemo(() => {
    if (!seasonData) return 0;
    const keys: HitterBucketKey[] = ["all", "early", "ahead", "behind", "two_strikes"];
    return keys.reduce(
      (sum, key) => sum + (seasonData.buckets[key]?.batSpeed?.swings ?? 0),
      0
    );
  }, [seasonData]);

  const rows: HitterBucketRow[] = useMemo(() => {
    if (!seasonData) return [];
    const baselineBat = seasonData.buckets.all.batSpeed.avg;
    const baselineLen = seasonData.buckets.all.swingLength.avg;
    return (["all", "early", "ahead", "behind", "two_strikes"] as HitterBucketKey[]).map(
      key => {
        const bucket = seasonData.buckets[key];
        const batDelta = classifyDelta(bucket.batSpeed.avg, baselineBat, BAT_SPEED_DELTA);
        const lenDelta = classifyDelta(
          bucket.swingLength.avg,
          baselineLen,
          SWING_LENGTH_DELTA
        );
        return {
          key,
          label: BUCKET_LABELS[key],
          batSpeedAvg: bucket.batSpeed.avg,
          batSpeedSwings: bucket.batSpeed.swings,
          batSpeedDelta: batDelta,
          swingLengthAvg: bucket.swingLength.avg,
          swingLengthSwings: bucket.swingLength.swings,
          swingLengthDelta: lenDelta
        };
      }
    );
  }, [seasonData]);

  const approachInsight = useMemo(() => {
    if (!seasonData) return null;

    const baselineBat = seasonData.buckets.all.batSpeed.avg;
    const baselineLen = seasonData.buckets.all.swingLength.avg;

    type MetricDiff = { key: Exclude<HitterBucketKey, "all">; diff: number };

    const batDiffs: MetricDiff[] = [];
    const lenDiffs: MetricDiff[] = [];

    (["early", "ahead", "behind", "two_strikes"] as const).forEach(key => {
      const bucket = seasonData.buckets[key];

      if (
        baselineBat != null &&
        bucket.batSpeed.avg != null &&
        bucket.batSpeed.swings >= MIN_INSIGHT_SWINGS
      ) {
        batDiffs.push({ key, diff: bucket.batSpeed.avg - baselineBat });
      }

      if (
        baselineLen != null &&
        bucket.swingLength.avg != null &&
        bucket.swingLength.swings >= MIN_INSIGHT_SWINGS
      ) {
        lenDiffs.push({ key, diff: bucket.swingLength.avg - baselineLen });
      }
    });

    const mkClause = (label: string, unit: string, diffs: MetricDiff[]) => {
      if (diffs.length === 0) return null;
      let max = diffs[0]!;
      let min = diffs[0]!;
      for (const d of diffs) {
        if (d.diff > max.diff) max = d;
        if (d.diff < min.diff) min = d;
      }
      const maxBucket = BUCKET_SHORT_LABELS[max.key];
      const minBucket = BUCKET_SHORT_LABELS[min.key];

      if (diffs.length === 1 || max.key === min.key) {
        return `${label} leans ${max.diff >= 0 ? "higher" : "lower"} in ${maxBucket} (${formatSigned(
          max.diff
        )} ${unit}) vs all counts`;
      }

      return `${label} peaks in ${maxBucket} (${formatSigned(max.diff)} ${unit}) and dips in ${minBucket} (${formatSigned(
        min.diff
      )} ${unit}) vs all counts`;
    };

    const batClause = mkClause("Bat speed", "mph", batDiffs);
    const lenClause = mkClause("Swing length", "ft", lenDiffs);

    if (!batClause && !lenClause) {
      return `Approach: Not enough swings (≥${MIN_INSIGHT_SWINGS}) for stable bucket insights.`;
    }

    if (batClause && lenClause) return `Approach: ${batClause}. ${lenClause}.`;
    return `Approach: ${batClause ?? lenClause}.`;
  }, [seasonData]);

  const seasonVsCareerInsight = useMemo(() => {
    if (season === "career") return null;
    if (!seasonData || !careerData) return null;

    const swingsAllBat = seasonData.buckets.all.batSpeed.swings;
    const swingsAllLen = seasonData.buckets.all.swingLength.swings;
    const swingsAll = Math.max(swingsAllBat ?? 0, swingsAllLen ?? 0);
    if (swingsAll < MIN_INSIGHT_SWINGS) {
      return `Season vs career (All Counts): not enough swings in this season (fewer than ${MIN_INSIGHT_SWINGS}) for a stable comparison.`;
    }

    const seasonBat = seasonData.buckets.all.batSpeed.avg;
    const careerBat = careerData.buckets.all.batSpeed.avg;
    const seasonLen = seasonData.buckets.all.swingLength.avg;
    const careerLen = careerData.buckets.all.swingLength.avg;

    const batDiff =
      seasonBat != null && careerBat != null ? seasonBat - careerBat : null;
    const lenDiff =
      seasonLen != null && careerLen != null ? seasonLen - careerLen : null;

    if (batDiff == null && lenDiff == null) return null;

    const parts: string[] = [];
    if (batDiff != null) parts.push(`${formatSigned(batDiff)} mph bat speed`);
    if (lenDiff != null) parts.push(`${formatSigned(lenDiff)} ft swing length`);

    const directionWord = (value: number) => (Math.abs(value) < 0.05 ? "about the same" : value > 0 ? "up" : "down");
    const batNarr = batDiff != null ? `bat speed ${directionWord(batDiff)}` : null;
    const lenNarr = lenDiff != null ? `swing length ${directionWord(lenDiff)}` : null;
    const narr = batNarr && lenNarr ? `${batNarr}, ${lenNarr}` : batNarr ?? lenNarr;

    return `Season vs career (All Counts): ${parts.join(", ")} (${narr}).`;
  }, [careerData, season, seasonData]);

  const careerLabel = meta?.careerLabel ?? "Career";
  const searchTrimmed = debouncedSearch.trim();
  const noMatch = Boolean(aggregates && searchTrimmed && filteredNames.length === 0);

  return (
    <div className="relative z-10 flex w-full justify-center px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex w-full max-w-[880px] flex-col gap-4">
        <header className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-wide sm:text-2xl">Swingsplits</h1>
          <p className="text-sm text-muted-foreground">
            Bat speed and swing length splits by count, powered by Statcast
          </p>
        </header>

        <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex-1 min-w-[180px]">
            <Label htmlFor="hitter-search" className="sr-only">
              Search hitter
            </Label>
            <Input
              id="hitter-search"
              placeholder="Search hitter by name"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") {
                  if (e.currentTarget.value.trim() === "") {
                    setSelectedName(null);
                    setDebouncedSearch("");
                    return;
                  }

                  const norm = normalizeName(e.currentTarget.value);
                  const exact =
                    allNames.find(name => normalizeName(name) === norm) ?? null;
                  const first = filteredNames[0] ?? null;
                  const chosen = exact ?? first ?? null;
                  setSelectedName(chosen);
                  setDebouncedSearch(e.currentTarget.value);
                  if (chosen && aggregates) {
                    const hitter = aggregates[chosen];
                    const hitterSeasons = Object.keys(hitter.seasons).filter(
                      key => key !== "career" && Number(key) >= MIN_SEASON_YEAR
                    );
                    if (hitterSeasons.length > 0) {
                      const latest = hitterSeasons.sort(
                        (a, b) => Number(a) - Number(b)
                      )[hitterSeasons.length - 1];
                      setSeason(latest);
                    } else {
                      setSeason("career");
                    }
                    setAutoSeasonHitter(chosen);
                  }
                }
              }}
            />
          </div>

          <div className="flex items-center gap-2">
            <Label htmlFor="season-select" className="sr-only">
              Season
            </Label>
            <Select value={season} onValueChange={setSeason}>
              <SelectTrigger id="season-select" className="min-w-[140px]">
                <SelectValue placeholder="Season" />
              </SelectTrigger>
              <SelectContent align="end">
                {seasons.map(year => (
                  <SelectItem
                    key={year}
                    value={year}
                  >
                    {year}
                  </SelectItem>
                ))}
                <SelectItem value="career">{careerLabel}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-full border border-border/70 px-3 py-1 text-[0.7rem] text-muted-foreground">
            Δ thresholds: at least {BAT_SPEED_DELTA} mph bat speed and{" "}
            {SWING_LENGTH_DELTA} ft swing length
          </div>
        </section>

        <Card className="w-full bg-card/90 border-border/80 shadow-xl backdrop-blur flex flex-col h-[460px]">
          <CardHeader className="flex flex-col gap-1 border-b border-border/80 sm:flex-row sm:items-baseline sm:justify-between">
            <div>
              <CardTitle className="text-base font-medium">
                {selectedName ? formatPlayerDisplayName(selectedName) : "No hitter selected"}
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                {season === "career" ? careerLabel : `Season ${season}`}
              </CardDescription>
              {selectedName && seasonData && (
                <div className="mt-1 flex flex-col gap-0.5 text-xs text-muted-foreground">
                  {approachInsight && <div>{approachInsight}</div>}
                  {seasonVsCareerInsight && <div>{seasonVsCareerInsight}</div>}
                </div>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {hasAnySwings === 0 && selectedName && seasonData
                ? "No tracked bat speed / swing length swings for this hitter in the selected season."
                : "Swings with both bat speed and swing length available"}
            </div>
          </CardHeader>
          <CardContent className="px-0 flex-1 overflow-hidden">
            {loading ? (
              <div className="px-6 py-8 text-sm text-muted-foreground">
                Loading Statcast aggregates...
              </div>
            ) : loadError ? (
              <div className="px-6 py-8 text-sm text-rose-400">{loadError}</div>
            ) : !aggregates ? (
              <div className="px-6 py-8 text-sm text-muted-foreground">
                Aggregated data file not found. Generate it by running the Statcast
                precompute script before starting the app.
              </div>
            ) : noMatch ? (
              <div className="px-6 py-8 text-sm text-muted-foreground">
                No hitter found matching &quot;{searchTrimmed}&quot; in available Statcast data.
              </div>
            ) : !selectedName || !seasonData ? (
              <div className="px-6 py-8 text-sm text-muted-foreground">
                Start typing a name to select a hitter. The first matching hitter will
                be shown.
              </div>
            ) : (
              <>
                {hasAnySwings === 0 && (
                  <div className="px-6 pt-4 pb-2 text-sm text-amber-400/90">
                    No bat speed / swing length tracked for this hitter in Season {season}. Try a different season or hitter.
                  </div>
                )}
              <div className="w-full h-full overflow-x-auto overflow-y-auto">
                <table className="min-w-full text-left text-xs sm:text-sm">
                  <thead className="border-b border-border/80 bg-background/40">
                    <tr>
                      <th className="px-4 py-2 font-medium">Count bucket</th>
                      <th className="px-4 py-2 font-medium">Bat speed (mph)</th>
                      <th className="px-4 py-2 font-medium">Δ vs all</th>
                      <th className="px-4 py-2 font-medium text-muted-foreground">
                        Swings
                      </th>
                      <th className="px-4 py-2 font-medium">Swing length (ft)</th>
                      <th className="px-4 py-2 font-medium">Δ vs all</th>
                      <th className="px-4 py-2 font-medium text-muted-foreground">
                        Swings
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => (
                      <tr
                        key={row.key}
                        className="border-b border-border/60 odd:bg-background/10 even:bg-background/5"
                      >
                        <td className="px-4 py-2 text-sm font-medium">{row.label}</td>
                        <td className="px-4 py-2 tabular-nums">
                          {formatAvg(row.batSpeedAvg)}
                        </td>
                        <td className={`px-4 py-2 tabular-nums ${row.batSpeedDelta.cls}`}>
                          {row.batSpeedDelta.text}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {row.batSpeedSwings > 0 ? row.batSpeedSwings : "0"}
                        </td>
                        <td className="px-4 py-2 tabular-nums">
                          {formatAvg(row.swingLengthAvg)}
                        </td>
                        <td className={`px-4 py-2 tabular-nums ${row.swingLengthDelta.cls}`}>
                          {row.swingLengthDelta.text}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {row.swingLengthSwings > 0 ? row.swingLengthSwings : "0"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default App;
