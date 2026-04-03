import type {
    AggregatesMeta,
    HitterAggregates,
    AbsData,
    LeagueContext,
} from "./types";

export async function fetchAggregates(): Promise<HitterAggregates | null> {
    try {
        const res = await fetch("/data/hitter_aggregates.json");
        if (!res.ok) return null;
        return (await res.json()) as HitterAggregates;
    } catch {
        return null;
    }
}

export async function fetchMeta(): Promise<AggregatesMeta | null> {
    try {
        const res = await fetch("/data/meta.json");
        if (!res.ok) return null;
        return (await res.json()) as AggregatesMeta;
    } catch {
        return null;
    }
}

export async function fetchAbs(): Promise<AbsData | null> {
    try {
        const res = await fetch("/data/abs_2026.json");
        if (!res.ok) return null;
        return (await res.json()) as AbsData;
    } catch {
        return null;
    }
}

export async function fetchLeagueContext(): Promise<LeagueContext | null> {
    try {
        const res = await fetch("/data/league_context.json");
        if (!res.ok) return null;
        return (await res.json()) as LeagueContext;
    } catch {
        return null;
    }
}
