import { useEffect, useMemo, useState } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import "./index.css";
import type {
    AggregatesMeta,
    HitterAggregates,
    HitterBucketKey,
    HitterBucketRow,
    AbsData,
    LeagueContext,
    PlayerPercentile2026,
} from "./types";
import {
    fetchAggregates,
    fetchMeta,
    fetchAbs,
    fetchLeagueContext,
} from "./data";

const BUCKET_LABELS: Record<HitterBucketKey, string> = {
    all: "All Counts",
    early: "Early (0-0, 1-0, 0-1)",
    ahead: "Ahead (2-0, 3-0, 3-1, 2-1)",
    behind: "Behind (0-2, 1-2)",
    two_strikes: "Two Strikes",
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
    two_strikes: "Two Strikes",
};

function classifyDelta(
    value: number | null,
    baseline: number | null,
    threshold: number,
) {
    if (value === null || baseline === null)
        return { cls: "text-muted-foreground", text: "–" };
    const diff = value - baseline;
    if (Math.abs(diff) < threshold)
        return { cls: "text-muted-foreground", text: "±0.0" };
    const sign = diff > 0 ? "+" : "";
    return {
        cls: diff > 0 ? "text-emerald-400" : "text-rose-400",
        text: `${sign}${diff.toFixed(1)}`,
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
        "sr.": "Sr.",
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
        const hyphenParts = w.split("-").map((part) => {
            const aposParts = part.split("'").map((p) => {
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
        s.split(/\s+/g).filter(Boolean).map(capWord).join(" ");

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
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value) && value >= MIN_SEASON_YEAR)
        .sort((a, b) => a - b);
    if (eligible.length === 0) return "career";
    return String(eligible[eligible.length - 1]);
}

function stripAccents(s: string): string {
    return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function toAbsKey(raw: string): string {
    let trimmed = raw.trim();
    if (trimmed.includes(",")) {
        const [lastRaw, ...rest] = trimmed.split(",");
        const first = rest.join(",").trim();
        const last = (lastRaw ?? "").trim();
        trimmed = first && last ? `${first} ${last}` : first || last;
    }
    // Normalize accents (Báez -> Baez, Teóscar -> Teoscar, Acuña -> Acuna)
    trimmed = stripAccents(trimmed);
    // Strip trailing generational suffixes (Jr., Sr., II, III, IV, V)
    trimmed = trimmed.replace(/\s+(jr\.?|sr\.?|ii|iii|iv|v)\s*$/i, "").trim();
    return trimmed.toLowerCase();
}

// InsightsView component for displaying ABS analysis findings
function InsightsView() {
    return (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Card className="w-full bg-card/90 border-border/80 shadow-xl backdrop-blur">
                <CardHeader>
                    <CardTitle className="text-lg font-medium">
                        ABS Challenge System Insights
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <p>
                        <strong className="text-foreground">The "Loopy" Hitter Is the Best ABS Challenger</strong> — below-median bat speed, above-median swing length. They dominate with 97% overturn rate and +0.85 avg tvse.
                    </p>
                    <p>
                        <strong className="text-foreground">Decelerating in Two-Strike Counts Predicts Success</strong> — it's not how much you shorten, but how much you slow your bat speed. Decelerators: +0.91 tvse, 96% overturn.
                    </p>
                    <p>
                        <strong className="text-foreground">Longer Swing = Better ABS Outcomes</strong> — Pearson r between swing length and overturn rate = +0.20. Longest hitters win at 96% vs shortest at 82%.
                    </p>
                    <p>
                        <strong className="text-foreground">Career Habits Are Irrelevant</strong> — Pearson r (career ts_len_delta vs tvse) = +0.009. ABS skill is learned in real-time.
                    </p>
                </CardContent>
            </Card>
            <Card className="w-full bg-card/90 border-border/80 shadow-xl backdrop-blur">
                <CardHeader>
                    <CardTitle className="text-lg font-medium">Top ABS Performers</CardTitle>
                </CardHeader>
                <CardContent className="px-0">
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-left text-xs">
                            <thead className="border-b border-border/80 bg-background/40">
                                <tr>
                                    <th className="px-4 py-2 font-medium">Player</th>
                                    <th className="px-4 py-2 font-medium">tvse</th>
                                    <th className="px-4 py-2 font-medium">Overturn</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr className="border-b border-border/60">
                                    <td className="px-4 py-2 font-medium">Ivan Herrera</td>
                                    <td className="px-4 py-2 tabular-nums text-emerald-400">+2.82</td>
                                    <td className="px-4 py-2 tabular-nums">100%</td>
                                </tr>
                                <tr className="border-b border-border/60">
                                    <td className="px-4 py-2 font-medium">Kerry Carpenter</td>
                                    <td className="px-4 py-2 tabular-nums text-emerald-400">+2.80</td>
                                    <td className="px-4 py-2 tabular-nums">100%</td>
                                </tr>
                                <tr className="border-b border-border/60">
                                    <td className="px-4 py-2 font-medium">Coby Mayo</td>
                                    <td className="px-4 py-2 tabular-nums text-emerald-400">+2.63</td>
                                    <td className="px-4 py-2 tabular-nums">100%</td>
                                </tr>
                                <tr className="border-b border-border/60">
                                    <td className="px-4 py-2 font-medium">Aaron Judge</td>
                                    <td className="px-4 py-2 tabular-nums text-emerald-400">+2.46</td>
                                    <td className="px-4 py-2 tabular-nums">100%</td>
                                </tr>
                                <tr><td className="px-4 py-2 font-medium">Tyler Stephenson</td>
                                    <td className="px-4 py-2 tabular-nums text-emerald-400">+2.38</td>
                                    <td className="px-4 py-2 tabular-nums">100%</td></tr>
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
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
    const [autoSeasonHitter, setAutoSeasonHitter] = useState<string | null>(
        null,
    );
    const [absData, setAbsData] = useState<AbsData | null>(null);
    const [leagueContext, setLeagueContext] = useState<LeagueContext | null>(
        null,
    );
    const [view, setView] = useState<"hitters" | "insights">("hitters");

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
                const [agg, m, abs, lc] = await Promise.all([
                    fetchAggregates(),
                    fetchMeta(),
                    fetchAbs(),
                    fetchLeagueContext(),
                ]);
                if (canceled) return;
                setAggregates(agg);
                setMeta(m);
                setAbsData(abs);
                setLeagueContext(lc);
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
        return list.filter((year) => Number(year) >= MIN_SEASON_YEAR);
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
        return allNames.filter((name) => {
            const normName = normalizeName(name);
            return tokens.every((token) => normName.includes(token));
        });
    }, [aggregates, allNames, debouncedSearch]);

    useEffect(() => {
        if (!aggregates) return;
        const query = debouncedSearch.trim();
        if (query === "") return;

        const norm = normalizeName(query);
        const exact =
            allNames.find((name) => normalizeName(name) === norm) ?? null;
        const first = filteredNames[0] ?? null;
        const chosen = exact ?? first ?? null;
        setSelectedName(chosen);

        if (chosen && chosen !== autoSeasonHitter) {
            const hitter = aggregates[chosen];
            const hitterSeasons = Object.keys(hitter.seasons).filter(
                (key) => key !== "career" && Number(key) >= MIN_SEASON_YEAR,
            );
            if (hitterSeasons.length > 0) {
                const latest = hitterSeasons.sort(
                    (a, b) => Number(a) - Number(b),
                )[hitterSeasons.length - 1];
                if (latest) setSeason(latest);
            } else {
                setSeason("career");
            }
            setAutoSeasonHitter(chosen);
        }
    }, [
        aggregates,
        allNames,
        autoSeasonHitter,
        debouncedSearch,
        filteredNames,
    ]);

    const selectedHitter =
        selectedName && aggregates ? aggregates[selectedName] : null;

    const seasonKey = season === "career" ? "career" : season;
    const seasonData = selectedHitter
        ? (selectedHitter.seasons[seasonKey] ?? null)
        : null;
    const careerData = selectedHitter
        ? (selectedHitter.seasons.career ?? null)
        : null;

    useEffect(() => {
        if (season === "career") return;
        if (!seasons.includes(season)) {
            setSeason("career");
        }
    }, [season, seasons]);

    const hasAnySwings = useMemo(() => {
        if (!seasonData) return 0;
        const keys: HitterBucketKey[] = [
            "all",
            "early",
            "ahead",
            "behind",
            "two_strikes",
        ];
        return keys.reduce(
            (sum, key) =>
                sum + (seasonData.buckets[key]?.batSpeed?.swings ?? 0),
            0,
        );
    }, [seasonData]);

    const rows: HitterBucketRow[] = useMemo(() => {
        if (!seasonData) return [];
        const baselineBat = seasonData.buckets.all.batSpeed.avg;
        const baselineLen = seasonData.buckets.all.swingLength.avg;
        return (
            [
                "all",
                "early",
                "ahead",
                "behind",
                "two_strikes",
            ] as HitterBucketKey[]
        ).map((key) => {
            const bucket = seasonData.buckets[key];
            const batDelta = classifyDelta(
                bucket.batSpeed.avg,
                baselineBat,
                BAT_SPEED_DELTA,
            );
            const lenDelta = classifyDelta(
                bucket.swingLength.avg,
                baselineLen,
                SWING_LENGTH_DELTA,
            );
            return {
                key,
                label: BUCKET_LABELS[key],
                batSpeedAvg: bucket.batSpeed.avg,
                batSpeedSwings: bucket.batSpeed.swings,
                batSpeedDelta: batDelta,
                swingLengthAvg: bucket.swingLength.avg,
                swingLengthSwings: bucket.swingLength.swings,
                swingLengthDelta: lenDelta,
            };
        });
    }, [seasonData]);

    const approachInsight = useMemo(() => {
        if (!seasonData) return null;

        const baselineBat = seasonData.buckets.all.batSpeed.avg;
        const baselineLen = seasonData.buckets.all.swingLength.avg;

        type MetricDiff = {
            key: Exclude<HitterBucketKey, "all">;
            diff: number;
        };

        const batDiffs: MetricDiff[] = [];
        const lenDiffs: MetricDiff[] = [];

        (["early", "ahead", "behind", "two_strikes"] as const).forEach(
            (key) => {
                const bucket = seasonData.buckets[key];

                if (
                    baselineBat != null &&
                    bucket.batSpeed.avg != null &&
                    bucket.batSpeed.swings >= MIN_INSIGHT_SWINGS
                ) {
                    batDiffs.push({
                        key,
                        diff: bucket.batSpeed.avg - baselineBat,
                    });
                }

                if (
                    baselineLen != null &&
                    bucket.swingLength.avg != null &&
                    bucket.swingLength.swings >= MIN_INSIGHT_SWINGS
                ) {
                    lenDiffs.push({
                        key,
                        diff: bucket.swingLength.avg - baselineLen,
                    });
                }
            },
        );

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
                    max.diff,
                )} ${unit}) vs all counts`;
            }

            return `${label} peaks in ${maxBucket} (${formatSigned(max.diff)} ${unit}) and dips in ${minBucket} (${formatSigned(
                min.diff,
            )} ${unit}) vs all counts`;
        };

        const batClause = mkClause("Bat speed", "mph", batDiffs);
        const lenClause = mkClause("Swing length", "ft", lenDiffs);

        if (!batClause && !lenClause) {
            return `Approach: Not enough swings (≥${MIN_INSIGHT_SWINGS}) for stable bucket insights.`;
        }

        if (batClause && lenClause)
            return `Approach: ${batClause}. ${lenClause}.`;
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
            seasonBat != null && careerBat != null
                ? seasonBat - careerBat
                : null;
        const lenDiff =
            seasonLen != null && careerLen != null
                ? seasonLen - careerLen
                : null;

        if (batDiff == null && lenDiff == null) return null;

        const parts: string[] = [];
        if (batDiff != null)
            parts.push(`${formatSigned(batDiff)} mph bat speed`);
        if (lenDiff != null)
            parts.push(`${formatSigned(lenDiff)} ft swing length`);

        const directionWord = (value: number) =>
            Math.abs(value) < 0.05
                ? "about the same"
                : value > 0
                  ? "up"
                  : "down";
        const batNarr =
            batDiff != null ? `bat speed ${directionWord(batDiff)}` : null;
        const lenNarr =
            lenDiff != null ? `swing length ${directionWord(lenDiff)}` : null;
        const narr =
            batNarr && lenNarr
                ? `${batNarr}, ${lenNarr}`
                : (batNarr ?? lenNarr);

        return `Season vs career (All Counts): ${parts.join(", ")} (${narr}).`;
    }, [careerData, season, seasonData]);

    const hitterAbs = useMemo(() => {
        if (!absData || !selectedName || season !== "2026") return null;
        const key = toAbsKey(selectedName);
        return absData[key] ?? null;
    }, [absData, selectedName, season]);

    const absInsight = useMemo(() => {
        if (!hitterAbs) return null;
        const {
            challenges,
            overturns,
            confirms,
            walksFlipped,
            strikeoutsFlipped,
            challengesAgainst,
            overturnsAgainst,
        } = hitterAbs;
        if (challenges === 0 && challengesAgainst === 0) return null;

        const parts: string[] = [];
        if (challenges > 0) {
            const record = `${overturns}-${confirms}`;
            parts.push(
                `ABS challenges: ${record} (${overturns} overturned, ${confirms} confirmed)`,
            );
            if (walksFlipped > 0)
                parts.push(
                    `${walksFlipped} walk${walksFlipped > 1 ? "s" : ""} created`,
                );
            if (strikeoutsFlipped > 0)
                parts.push(
                    `${strikeoutsFlipped} K${strikeoutsFlipped > 1 ? "s" : ""} avoided`,
                );
        } else {
            parts.push("ABS challenges: 0 initiated");
        }
        if (challengesAgainst > 0) {
            parts.push(
                `${overturnsAgainst}/${challengesAgainst} overturned against`,
            );
        }
        return parts.join(" · ");
    }, [hitterAbs]);

    const leaguePlayerPct = useMemo((): PlayerPercentile2026 | null => {
        if (!leagueContext || season !== "2026" || !selectedName) return null;
        return leagueContext.playerPercentiles2026[selectedName] ?? null;
    }, [leagueContext, season, selectedName]);

    const leagueContextInsight = useMemo(() => {
        if (!leaguePlayerPct) return null;
        const parts: string[] = [];

        const ordinal = (n: number) => {
            const s = ["th", "st", "nd", "rd"] as const;
            const v = n % 100;
            return `${n}${s[(v - 20) % 10] ?? s[v] ?? "th"}`;
        };

        if (
            leaguePlayerPct.batSpeed != null &&
            leaguePlayerPct.batSpeedPct != null &&
            (leaguePlayerPct.batSpeedSwings ?? 0) >= 30
        ) {
            parts.push(
                `${formatAvg(leaguePlayerPct.batSpeed)} mph bat speed (${ordinal(leaguePlayerPct.batSpeedPct)} among 2026 hitters)`,
            );
        }

        if (
            leaguePlayerPct.tsBatDelta != null &&
            leaguePlayerPct.tsBatDeltaDecelerationPct != null &&
            (leaguePlayerPct.tsBatSwings ?? 0) >= 20
        ) {
            const dir =
                leaguePlayerPct.tsBatDelta <= 0 ? "decelerates" : "accelerates";
            parts.push(
                `${dir} ${formatSigned(leaguePlayerPct.tsBatDelta)} mph in two-strike counts (${ordinal(leaguePlayerPct.tsBatDeltaDecelerationPct)} most)`,
            );
        }

        if (
            leaguePlayerPct.tsLenDelta != null &&
            leaguePlayerPct.tsLenDeltaShorteningPct != null &&
            (leaguePlayerPct.tsLenSwings ?? 0) >= 20
        ) {
            const dir =
                leaguePlayerPct.tsLenDelta <= 0 ? "shortens" : "extends";
            parts.push(
                `${dir} ${formatSigned(leaguePlayerPct.tsLenDelta, 2)} ft swing (${ordinal(leaguePlayerPct.tsLenDeltaShorteningPct)} most)`,
            );
        }

        if (parts.length === 0) return null;
        return "League context (2026): " + parts.join(" · ");
    }, [leaguePlayerPct]);

    const careerLabel = meta?.careerLabel ?? "Career";
    const searchTrimmed = debouncedSearch.trim();
    const noMatch = Boolean(
        aggregates && searchTrimmed && filteredNames.length === 0,
    );

    return (
        <div className="relative z-10 flex w-full justify-center px-4 py-6 sm:px-6 lg:px-8">
            <div className="flex w-full max-w-[880px] flex-col gap-4">
                <header className="flex flex-col gap-1">
                    <h1 className="text-xl font-semibold tracking-wide sm:text-2xl">
                        Swingsplits
                    </h1>
                    <p className="text-base text-muted-foreground">
                        Bat speed and swing length splits by count, powered by
                        Statcast
                    </p>
                </header>

                {/* View Tabs */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setView("hitters")}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            view === "hitters"
                                ? "bg-background text-foreground shadow-sm border border-border"
                                : "text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        Hitters
                    </button>
                    <button
                        onClick={() => setView("insights")}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            view === "insights"
                                ? "bg-background text-foreground shadow-sm border border-border"
                                : "text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        Insights
                    </button>
                </div>

                {view === "insights" ? <InsightsView /> : null}

                <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                    <div className="flex-1 min-w-[180px]">
                        <Label htmlFor="hitter-search" className="sr-only">
                            Search hitter
                        </Label>
                        <Input
                            id="hitter-search"
                            placeholder="Search hitter by name"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    if (e.currentTarget.value.trim() === "") {
                                        setSelectedName(null);
                                        setDebouncedSearch("");
                                        return;
                                    }

                                    const norm = normalizeName(
                                        e.currentTarget.value,
                                    );
                                    const exact =
                                        allNames.find(
                                            (name) =>
                                                normalizeName(name) === norm,
                                        ) ?? null;
                                    const first = filteredNames[0] ?? null;
                                    const chosen = exact ?? first ?? null;
                                    setSelectedName(chosen);
                                    setDebouncedSearch(e.currentTarget.value);
                                    if (chosen && aggregates) {
                                        const hitter = aggregates[chosen];
                                        const hitterSeasons = Object.keys(
                                            hitter.seasons,
                                        ).filter(
                                            (key) =>
                                                key !== "career" &&
                                                Number(key) >= MIN_SEASON_YEAR,
                                        );
                                        if (hitterSeasons.length > 0) {
                                            const latest = hitterSeasons.sort(
                                                (a, b) => Number(a) - Number(b),
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
                            <SelectTrigger
                                id="season-select"
                                className="min-w-[140px]"
                            >
                                <SelectValue placeholder="Season" />
                            </SelectTrigger>
                            <SelectContent align="end">
                                {seasons.map((year) => (
                                    <SelectItem key={year} value={year}>
                                        {year}
                                    </SelectItem>
                                ))}
                                <SelectItem value="career">
                                    {careerLabel}
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="rounded-full border border-border/70 px-3 py-1 text-[0.7rem] text-muted-foreground">
                        Δ thresholds: at least {BAT_SPEED_DELTA} mph bat speed
                        and {SWING_LENGTH_DELTA} ft swing length
                    </div>
                </section>

                <Card className="w-full bg-card/90 border-border/80 shadow-xl backdrop-blur flex flex-col h-[460px]">
                    <CardHeader className="flex flex-col gap-1 border-b border-border/80 sm:flex-row sm:items-baseline sm:justify-between">
                        <div>
                            <CardTitle className="text-lg font-medium">
                                {selectedName
                                    ? formatPlayerDisplayName(selectedName)
                                    : "No hitter selected"}
                            </CardTitle>
                            <CardDescription className="text-sm sm:text-base">
                                {season === "career"
                                    ? careerLabel
                                    : `Season ${season}`}
                            </CardDescription>
                            {selectedName && seasonData && (
                                <div className="mt-1 flex flex-col gap-0.5 text-xs text-muted-foreground">
                                    {approachInsight && (
                                        <div>{approachInsight}</div>
                                    )}
                                    {seasonVsCareerInsight && (
                                        <div>{seasonVsCareerInsight}</div>
                                    )}
                                    {leagueContextInsight && (
                                        <div className="text-sky-400/90">
                                            {leagueContextInsight}
                                        </div>
                                    )}
                                    {absInsight && (
                                        <div className="text-amber-300/90">
                                            {absInsight}
                                        </div>
                                    )}
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
                            <div className="px-6 py-8 text-base text-muted-foreground">
                                Loading Statcast aggregates...
                            </div>
                        ) : loadError ? (
                            <div className="px-6 py-8 text-sm text-rose-400">
                                {loadError}
                            </div>
                        ) : !aggregates ? (
                            <div className="px-6 py-8 text-base text-muted-foreground">
                                Aggregated data file not found. Generate it by
                                running the Statcast precompute script before
                                starting the app.
                            </div>
                        ) : noMatch ? (
                            <div className="px-6 py-8 text-base text-muted-foreground">
                                No hitter found matching &quot;{searchTrimmed}
                                &quot; in available Statcast data.
                            </div>
                        ) : !selectedName || !seasonData ? (
                            <div className="px-6 py-8 text-base text-muted-foreground">
                                Start typing a name to select a hitter. The
                                first matching hitter will be shown.
                            </div>
                        ) : (
                            <>
                                {hasAnySwings === 0 && (
                                    <div className="px-6 pt-4 pb-2 text-base text-amber-400/90">
                                        No bat speed / swing length tracked for
                                        this hitter in Season {season}. Try a
                                        different season or hitter.
                                    </div>
                                )}
                                <div className="w-full h-full overflow-x-auto overflow-y-auto">
                                    <table className="min-w-full text-left text-sm sm:text-base">
                                        <thead className="border-b border-border/80 bg-background/40">
                                            <tr>
                                                <th className="px-4 py-2 font-medium">
                                                    Count bucket
                                                </th>
                                                <th className="px-4 py-2 font-medium">
                                                    Bat speed (mph)
                                                </th>
                                                <th className="px-4 py-2 font-medium">
                                                    Δ vs all
                                                </th>
                                                <th className="px-4 py-2 font-medium text-muted-foreground">
                                                    Swings
                                                </th>
                                                <th className="px-4 py-2 font-medium">
                                                    Swing length (ft)
                                                </th>
                                                <th className="px-4 py-2 font-medium">
                                                    Δ vs all
                                                </th>
                                                <th className="px-4 py-2 font-medium text-muted-foreground">
                                                    Swings
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rows.map((row) => (
                                                <tr
                                                    key={row.key}
                                                    className="border-b border-border/60 odd:bg-background/10 even:bg-background/5"
                                                >
                                                    <td className="px-4 py-2 text-base font-medium">
                                                        {row.label}
                                                    </td>
                                                    <td className="px-4 py-2 tabular-nums">
                                                        {formatAvg(
                                                            row.batSpeedAvg,
                                                        )}
                                                    </td>
                                                    <td
                                                        className={`px-4 py-2 tabular-nums ${row.batSpeedDelta.cls}`}
                                                    >
                                                        {row.batSpeedDelta.text}
                                                    </td>
                                                    <td className="px-4 py-2 text-xs text-muted-foreground">
                                                        {row.batSpeedSwings > 0
                                                            ? row.batSpeedSwings
                                                            : "0"}
                                                    </td>
                                                    <td className="px-4 py-2 tabular-nums">
                                                        {formatAvg(
                                                            row.swingLengthAvg,
                                                        )}
                                                    </td>
                                                    <td
                                                        className={`px-4 py-2 tabular-nums ${row.swingLengthDelta.cls}`}
                                                    >
                                                        {
                                                            row.swingLengthDelta
                                                                .text
                                                        }
                                                    </td>
                                                    <td className="px-4 py-2 text-xs text-muted-foreground">
                                                        {row.swingLengthSwings >
                                                        0
                                                            ? row.swingLengthSwings
                                                            : "0"}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    {hitterAbs && season === "2026" && (
                                        <div className="mx-4 my-3 rounded-md border border-border/60 bg-background/20 p-3">
                                            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                                2026 ABS Challenge System
                                            </div>
                                            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Challenges
                                                    </span>
                                                    <span className="ml-1 tabular-nums font-medium">
                                                        {hitterAbs.challenges >
                                                        0
                                                            ? `${hitterAbs.overturns}W–${hitterAbs.confirms}L`
                                                            : "—"}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Overturn rate
                                                    </span>
                                                    <span className="ml-1 tabular-nums font-medium">
                                                        {hitterAbs.overturnRate !=
                                                        null
                                                            ? `${(hitterAbs.overturnRate * 100).toFixed(0)}%`
                                                            : "—"}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Ks avoided
                                                    </span>
                                                    <span className="ml-1 tabular-nums font-medium">
                                                        {
                                                            hitterAbs.strikeoutsFlipped
                                                        }
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Walks created
                                                    </span>
                                                    <span className="ml-1 tabular-nums font-medium">
                                                        {hitterAbs.walksFlipped}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Against (overturned)
                                                    </span>
                                                    <span className="ml-1 tabular-nums font-medium">
                                                        {hitterAbs.challengesAgainst >
                                                        0
                                                            ? `${hitterAbs.overturnsAgainst}/${hitterAbs.challengesAgainst}`
                                                            : "—"}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Net vs expected
                                                    </span>
                                                    <span
                                                        className={`ml-1 tabular-nums font-medium ${hitterAbs.totalVsExpected >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                                                    >
                                                        {hitterAbs.totalVsExpected >=
                                                        0
                                                            ? "+"
                                                            : ""}
                                                        {hitterAbs.totalVsExpected.toFixed(
                                                            2,
                                                        )}
                                                    </span>
                                                </div>
                                            </div>
                                            {(hitterAbs.walksFlipped > 0 ||
                                                hitterAbs.strikeoutsFlipped >
                                                    0 ||
                                                (seasonData &&
                                                    hitterAbs.challenges >
                                                        0)) && (
                                                <div className="mt-2 text-xs text-muted-foreground">
                                                    {(() => {
                                                        const twoStrikeBat =
                                                            seasonData?.buckets
                                                                .two_strikes
                                                                ?.batSpeed?.avg;
                                                        const allBat =
                                                            seasonData?.buckets
                                                                .all?.batSpeed
                                                                ?.avg;
                                                        const twoStrikeLen =
                                                            seasonData?.buckets
                                                                .two_strikes
                                                                ?.swingLength
                                                                ?.avg;
                                                        const allLen =
                                                            seasonData?.buckets
                                                                .all
                                                                ?.swingLength
                                                                ?.avg;
                                                        const parts: string[] =
                                                            [];
                                                        if (
                                                            twoStrikeBat !=
                                                                null &&
                                                            allBat != null
                                                        ) {
                                                            const diff =
                                                                twoStrikeBat -
                                                                allBat;
                                                            if (
                                                                Math.abs(
                                                                    diff,
                                                                ) >=
                                                                BAT_SPEED_DELTA
                                                            ) {
                                                                parts.push(
                                                                    `${diff > 0 ? "accelerates" : "eases up"} in two-strike counts (${diff > 0 ? "+" : ""}${diff.toFixed(1)} mph)`,
                                                                );
                                                            }
                                                        }
                                                        if (
                                                            twoStrikeLen !=
                                                                null &&
                                                            allLen != null
                                                        ) {
                                                            const diff =
                                                                twoStrikeLen -
                                                                allLen;
                                                            if (
                                                                Math.abs(
                                                                    diff,
                                                                ) >=
                                                                SWING_LENGTH_DELTA
                                                            ) {
                                                                parts.push(
                                                                    `${diff < 0 ? "shortens" : "extends"} swing length (${diff > 0 ? "+" : ""}${diff.toFixed(1)} ft)`,
                                                                );
                                                            }
                                                        }
                                                        if (
                                                            parts.length > 0 &&
                                                            hitterAbs.strikeoutsFlipped >
                                                                0
                                                        ) {
                                                            return `Avoids bad-call Ks while ${parts.join(" and ")} — ${hitterAbs.strikeoutsFlipped} called-strike overturn${hitterAbs.strikeoutsFlipped > 1 ? "s" : ""} this season.`;
                                                        }
                                                        if (
                                                            parts.length > 0 &&
                                                            hitterAbs.challenges >
                                                                0
                                                        ) {
                                                            return `Two-strike approach: ${parts.join(" and ")} · ${hitterAbs.overturns}/${hitterAbs.challenges} challenges overturned.`;
                                                        }
                                                        return null;
                                                    })()}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>

                {leagueContext &&
                    (() => {
                        const trends = leagueContext.leagueTrends;
                        const ctx26 = leagueContext.league2026;
                        const abs26 = ctx26.abs;
                        const trend25 = trends.find((t) => t.year === "2025");
                        const pctShort26 = ctx26.pctShorteners;
                        const pctShort25 = trend25?.pctShorteners ?? null;
                        const shortenerJump =
                            pctShort26 != null && pctShort25 != null
                                ? pctShort26 - pctShort25
                                : null;
                        const overallPct =
                            abs26.overallOverturnRate != null
                                ? Math.round(abs26.overallOverturnRate * 100)
                                : null;

                        return (
                            <Card className="w-full bg-card/90 border-border/80 shadow-xl backdrop-blur">
                                <CardHeader className="border-b border-border/80 pb-3">
                                    <CardTitle className="text-lg font-medium">
                                        League Swing Trends &amp; 2026 ABS
                                        Context
                                    </CardTitle>
                                    {shortenerJump != null &&
                                        pctShort26 != null &&
                                        pctShort25 != null && (
                                            <CardDescription className="mt-1 text-xs leading-snug">
                                                <span className="text-amber-300/90 font-medium">
                                                    {pctShort26.toFixed(1)}% of
                                                    2026 hitters are shortening
                                                    their swing in two-strike
                                                    counts — up{" "}
                                                    {shortenerJump.toFixed(1)}{" "}
                                                    pp from{" "}
                                                    {pctShort25.toFixed(1)}% in
                                                    2025.
                                                </span>{" "}
                                                The ABS challenge system appears
                                                to already be reshaping how
                                                hitters protect the plate. Bat
                                                speed deceleration in two-strike
                                                counts also increased (avg −
                                                {Math.abs(
                                                    ctx26.avgTsBatDelta ?? 0,
                                                ).toFixed(2)}{" "}
                                                mph in 2026 vs −
                                                {Math.abs(
                                                    trend25?.avgTsBatDelta ?? 0,
                                                ).toFixed(2)}{" "}
                                                mph in 2025).
                                            </CardDescription>
                                        )}
                                </CardHeader>
                                <CardContent className="px-0 pt-0">
                                    <div className="overflow-x-auto">
                                        <table className="min-w-full text-left text-xs">
                                            <thead className="border-b border-border/80 bg-background/40">
                                                <tr>
                                                    <th className="px-4 py-2 font-medium">
                                                        Year
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        Hitters (n)
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        Avg bat speed
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        Avg swing len
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        2-strike bat Δ
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        2-strike len Δ
                                                    </th>
                                                    <th className="px-4 py-2 font-medium">
                                                        % shorteners
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {trends.map((t) => {
                                                    const is2026 =
                                                        t.year === "2026";
                                                    const rowCls = is2026
                                                        ? "border-b border-border/60 bg-amber-950/20"
                                                        : "border-b border-border/60 odd:bg-background/10 even:bg-background/5";
                                                    const shortPct =
                                                        t.pctShorteners;
                                                    const prev = trends.find(
                                                        (x) =>
                                                            String(
                                                                Number(x.year) +
                                                                    1,
                                                            ) === t.year,
                                                    );
                                                    const shortDelta =
                                                        shortPct != null &&
                                                        prev?.pctShorteners !=
                                                            null
                                                            ? shortPct -
                                                              prev.pctShorteners
                                                            : null;
                                                    return (
                                                        <tr
                                                            key={t.year}
                                                            className={rowCls}
                                                        >
                                                            <td
                                                                className={`px-4 py-2 font-semibold tabular-nums ${is2026 ? "text-amber-300/90" : ""}`}
                                                            >
                                                                {t.year}
                                                            </td>
                                                            <td className="px-4 py-2 tabular-nums text-muted-foreground">
                                                                {
                                                                    t.nQualifyingAllCount
                                                                }
                                                            </td>
                                                            <td className="px-4 py-2 tabular-nums">
                                                                {t.avgBatSpeed !=
                                                                null
                                                                    ? t.avgBatSpeed.toFixed(
                                                                          1,
                                                                      )
                                                                    : "—"}
                                                            </td>
                                                            <td className="px-4 py-2 tabular-nums">
                                                                {t.avgSwingLength !=
                                                                null
                                                                    ? t.avgSwingLength.toFixed(
                                                                          2,
                                                                      )
                                                                    : "—"}
                                                            </td>
                                                            <td
                                                                className={`px-4 py-2 tabular-nums ${is2026 ? "text-rose-400" : "text-muted-foreground"}`}
                                                            >
                                                                {t.avgTsBatDelta !=
                                                                null
                                                                    ? (t.avgTsBatDelta >
                                                                      0
                                                                          ? "+"
                                                                          : "") +
                                                                      t.avgTsBatDelta.toFixed(
                                                                          2,
                                                                      )
                                                                    : "—"}
                                                            </td>
                                                            <td
                                                                className={`px-4 py-2 tabular-nums ${is2026 ? "text-rose-400" : "text-muted-foreground"}`}
                                                            >
                                                                {t.avgTsLenDelta !=
                                                                null
                                                                    ? (t.avgTsLenDelta >
                                                                      0
                                                                          ? "+"
                                                                          : "") +
                                                                      t.avgTsLenDelta.toFixed(
                                                                          3,
                                                                      )
                                                                    : "—"}
                                                            </td>
                                                            <td
                                                                className={`px-4 py-2 tabular-nums ${is2026 ? "text-amber-300/90 font-semibold" : ""}`}
                                                            >
                                                                {shortPct !=
                                                                null ? (
                                                                    <>
                                                                        {shortPct.toFixed(
                                                                            1,
                                                                        )}
                                                                        %
                                                                        {shortDelta !=
                                                                            null &&
                                                                            shortDelta >
                                                                                0 && (
                                                                                <span className="ml-1 text-emerald-400 text-[10px]">
                                                                                    +
                                                                                    {shortDelta.toFixed(
                                                                                        1,
                                                                                    )}{" "}
                                                                                    pp
                                                                                </span>
                                                                            )}
                                                                    </>
                                                                ) : (
                                                                    "—"
                                                                )}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="mx-4 mt-3 mb-3 flex flex-col gap-2">
                                        {/* ABS league summary row */}
                                        <div className="rounded-md border border-amber-500/20 bg-amber-950/20 px-3 py-2">
                                            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-amber-300/70">
                                                2026 ABS Season — League Wide
                                            </div>
                                            <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
                                                <span>
                                                    <span className="text-muted-foreground">
                                                        Challenges
                                                    </span>
                                                    <span className="ml-1 font-medium tabular-nums">
                                                        {abs26.totalChallenges}
                                                    </span>
                                                </span>
                                                <span>
                                                    <span className="text-muted-foreground">
                                                        Overturns
                                                    </span>
                                                    <span className="ml-1 font-medium tabular-nums">
                                                        {abs26.totalOverturns}
                                                        {overallPct != null && (
                                                            <span className="ml-0.5 text-amber-300/90">
                                                                ({overallPct}%)
                                                            </span>
                                                        )}
                                                    </span>
                                                </span>
                                                <span>
                                                    <span className="text-muted-foreground">
                                                        Ks avoided
                                                    </span>
                                                    <span className="ml-1 font-medium tabular-nums">
                                                        {abs26.totalKsFlipped}
                                                    </span>
                                                </span>
                                                <span>
                                                    <span className="text-muted-foreground">
                                                        Walks created
                                                    </span>
                                                    <span className="ml-1 font-medium tabular-nums">
                                                        {
                                                            abs26.totalWalksFlipped
                                                        }
                                                    </span>
                                                </span>
                                                <span>
                                                    <span className="text-muted-foreground">
                                                        Players tracked
                                                    </span>
                                                    <span className="ml-1 font-medium tabular-nums">
                                                        {abs26.nPlayersWithData}
                                                    </span>
                                                </span>
                                            </div>
                                        </div>

                                        {/* Key findings */}
                                        <div className="rounded-md border border-border/50 bg-background/10 px-3 py-2 text-xs text-muted-foreground space-y-1">
                                            <div className="font-semibold text-foreground/80 text-[10px] uppercase tracking-wider mb-1">
                                                Key findings from cross-analysis
                                            </div>
                                            <div>
                                                <span className="text-sky-400/90">
                                                    Swing discipline ≠ ABS
                                                    success (r ≈ 0.02).
                                                </span>{" "}
                                                How much a hitter shortens or
                                                slows their swing in two-strike
                                                counts barely predicts whether
                                                they win challenges. Knowing
                                                which borderline pitch to
                                                challenge matters more than
                                                approach alone.
                                            </div>
                                            <div>
                                                <span className="text-sky-400/90">
                                                    Mid-range bat speed wins the
                                                    most challenges.
                                                </span>{" "}
                                                Hitters in the 67–72 mph range
                                                overturn calls at 92–94%, while
                                                the fastest swingers (&gt;72
                                                mph) win only 86% — possibly
                                                because elite power hitters
                                                expand their zone on borderline
                                                takes.
                                            </div>
                                            <div>
                                                <span className="text-sky-400/90">
                                                    25 Ks already avoided in
                                                    week 1.
                                                </span>{" "}
                                                Strikeout-saving overturns are
                                                spread across all swing profiles
                                                — shorteners and aggressive
                                                hitters alike. At this pace,
                                                hundreds of Ks could be avoided
                                                league-wide by season end.
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })()}
            </div>
        </div>
    );
}
