export type HitterBucketKey = "all" | "early" | "ahead" | "behind" | "two_strikes";

export type MetricStats = {
  avg: number | null;
  swings: number;
};

export type BucketStats = {
  batSpeed: MetricStats;
  swingLength: MetricStats;
};

export type SeasonStats = {
  season: string;
  buckets: Record<HitterBucketKey, BucketStats>;
};

export type HitterRecord = {
  name: string;
  seasons: Record<string, SeasonStats>;
};

export type HitterAggregates = Record<string, HitterRecord>;

export type DeltaDisplay = {
  cls: string;
  text: string;
};

export type HitterBucketRow = {
  key: HitterBucketKey;
  label: string;
  batSpeedAvg: number | null;
  batSpeedSwings: number;
  batSpeedDelta: DeltaDisplay;
  swingLengthAvg: number | null;
  swingLengthSwings: number;
  swingLengthDelta: DeltaDisplay;
};

export type AggregatesMeta = {
  availableSeasons: string[];
  careerLabel: string;
};

