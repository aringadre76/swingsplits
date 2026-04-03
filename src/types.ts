export type HitterBucketKey =
    | "all"
    | "early"
    | "ahead"
    | "behind"
    | "two_strikes";

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

export type AbsStats = {
    name: string;
    team: string;
    challenges: number;
    overturns: number;
    confirms: number;
    overturnRate: number | null;
    walksFlipped: number;
    strikeoutsFlipped: number;
    netFor: number;
    totalVsExpected: number;
    challengesAgainst: number;
    overturnsAgainst: number;
    confirmsAgainst: number;
    overturnRateAgainst: number | null;
};

export type AbsData = Record<string, AbsStats>;

export type LeagueTrend = {
    year: string;
    nQualifyingAllCount: number;
    nQualifyingTwoStrike: number;
    avgBatSpeed: number | null;
    avgSwingLength: number | null;
    avgTsBatDelta: number | null;
    avgTsLenDelta: number | null;
    pctShorteners: number | null;
    pctExtenders: number | null;
    pctNeutral: number | null;
    nShorteners: number;
    nExtenders: number;
    nNeutral: number;
};

export type AbsLeagueContext = {
    nPlayersWithData: number;
    nWhoHaveChallenged: number;
    totalChallenges: number;
    totalOverturns: number;
    totalConfirms: number;
    overallOverturnRate: number | null;
    avgPlayerOverturnRate: number | null;
    totalWalksFlipped: number;
    totalKsFlipped: number;
    avgTotalVsExpected: number | null;
    sdTotalVsExpected: number | null;
};

export type League2026 = LeagueTrend & { abs: AbsLeagueContext };

export type PlayerPercentile2026 = {
    hasAll: boolean;
    hasTs: boolean;
    batSpeed?: number;
    swingLength?: number;
    batSpeedSwings?: number;
    batSpeedPct?: number;
    tsBatDelta?: number;
    tsLenDelta?: number;
    tsBatSwings?: number;
    tsLenSwings?: number;
    tsBatDeltaDecelerationPct?: number;
    tsLenDeltaShorteningPct?: number;
};

export type LeagueContext = {
    generated: string;
    leagueTrends: LeagueTrend[];
    league2026: League2026;
    playerPercentiles2026: Record<string, PlayerPercentile2026>;
    thresholds: {
        minAllSwings: number;
        minTsSwings: number;
        lenThresholdFt: number;
        batThresholdMph: number;
    };
};
