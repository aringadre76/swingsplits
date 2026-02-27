import type { AggregatesMeta, HitterAggregates } from "./types";

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

