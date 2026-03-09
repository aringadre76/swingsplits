import fs from "fs";
import path from "path";
import { parse } from "csv-parse";
import type { HitterAggregates, HitterBucketKey, BucketStats, SeasonStats } from "../src/types";

type RunningStats = {
  batSpeedSum: number;
  batSpeedCount: number;
  swingLengthSum: number;
  swingLengthCount: number;
};

type CsvRow = {
  batter_name?: string;
  batter?: string;
  player_name?: string;
  game_year?: string;
  game_date?: string;
  bat_speed?: string;
  swing_length?: string;
  balls?: string;
  strikes?: string;
};

type BucketMap = { [K in HitterBucketKey]: RunningStats };
type SeasonMap = Record<string, BucketMap>;
type PlayerMap = Record<string, SeasonMap>;

function makeEmptyBucket(): RunningStats {
  return {
    batSpeedSum: 0,
    batSpeedCount: 0,
    swingLengthSum: 0,
    swingLengthCount: 0
  };
}

function ensureBucket(
  map: SeasonMap,
  season: string,
  bucket: HitterBucketKey
): RunningStats | undefined {
  let seasonBuckets: BucketMap | undefined = map[season];
  if (!seasonBuckets) {
    seasonBuckets = {
      all: makeEmptyBucket(),
      early: makeEmptyBucket(),
      ahead: makeEmptyBucket(),
      behind: makeEmptyBucket(),
      two_strikes: makeEmptyBucket()
    };
    map[season] = seasonBuckets;
  }
  return (seasonBuckets as BucketMap)[bucket];
}

function classifyBuckets(balls: number, strikes: number): HitterBucketKey[] {
  const keys: HitterBucketKey[] = ["all"];
  if (
    (balls === 0 && strikes === 0) ||
    (balls === 1 && strikes === 0) ||
    (balls === 0 && strikes === 1)
  ) {
    keys.push("early");
  }
  if (
    (balls === 2 && strikes === 0) ||
    (balls === 3 && strikes === 0) ||
    (balls === 3 && strikes === 1) ||
    (balls === 2 && strikes === 1)
  ) {
    keys.push("ahead");
  }
  if ((balls === 0 && strikes === 2) || (balls === 1 && strikes === 2)) {
    keys.push("behind");
  }
  if (strikes === 2) {
    keys.push("two_strikes");
  }
  return keys;
}

async function processFile(filePath: string, players: PlayerMap) {
  return new Promise<void>((resolve, reject) => {
    const parser = fs
      .createReadStream(filePath)
      .pipe(
        parse({
          columns: true,
          skip_empty_lines: true
        })
      );

    parser.on("data", (row: CsvRow) => {
      const batterName = String(row.batter_name ?? "").trim();
      const batterId = row.batter != null && row.batter !== "" ? String(row.batter) : "";
      const name = batterName || batterId;
      if (!name) return;

      const year = Number(row.game_year || row.game_date?.slice(0, 4));
      if (!year || year < 2023 || year > 2026) return;

      const batSpeed =
        row.bat_speed === "" || row.bat_speed == null ? null : Number(row.bat_speed);
      const swingLength =
        row.swing_length === "" || row.swing_length == null
          ? null
          : Number(row.swing_length);

      const balls = row.balls === "" || row.balls == null ? null : Number(row.balls);
      const strikes =
        row.strikes === "" || row.strikes == null ? null : Number(row.strikes);
      if (balls == null || strikes == null) return;

      if (!players[name]) {
        players[name] = {};
      }
      const seasonKey = String(year);
      const buckets = classifyBuckets(balls, strikes);

      for (const bucket of buckets) {
        const stats = ensureBucket(players[name], seasonKey, bucket);
        if (!stats) {
          continue;
        }
        if (batSpeed != null) {
          stats.batSpeedSum += batSpeed;
          stats.batSpeedCount += 1;
        }
        if (swingLength != null) {
          stats.swingLengthSum += swingLength;
          stats.swingLengthCount += 1;
        }
      }
    });

    parser.on("error", (err: unknown) => reject(err));
    parser.on("end", () => resolve());
  });
}

function toMetricStats(run: RunningStats) {
  const batAvg = run.batSpeedCount > 0 ? run.batSpeedSum / run.batSpeedCount : null;
  const lenAvg =
    run.swingLengthCount > 0 ? run.swingLengthSum / run.swingLengthCount : null;
  return {
    batSpeed: { avg: batAvg, swings: run.batSpeedCount },
    swingLength: { avg: lenAvg, swings: run.swingLengthCount }
  };
}

function buildAggregates(players: PlayerMap): HitterAggregates {
  const result: HitterAggregates = {};

  for (const [name, seasons] of Object.entries(players)) {
    const seasonStats: Record<string, SeasonStats> = {};
    const careerBuckets: BucketMap = {
      all: makeEmptyBucket(),
      early: makeEmptyBucket(),
      ahead: makeEmptyBucket(),
      behind: makeEmptyBucket(),
      two_strikes: makeEmptyBucket()
    };

    for (const [seasonKey, bucketMap] of Object.entries(seasons)) {
      const seasonBuckets: Record<HitterBucketKey, BucketStats> = {
        all: toMetricStats(bucketMap.all),
        early: toMetricStats(bucketMap.early),
        ahead: toMetricStats(bucketMap.ahead),
        behind: toMetricStats(bucketMap.behind),
        two_strikes: toMetricStats(bucketMap.two_strikes)
      };

      for (const key of ["all", "early", "ahead", "behind", "two_strikes"] as HitterBucketKey[]) {
        const src = bucketMap[key]!;
        const dst = careerBuckets[key]!;
        dst.batSpeedSum += src.batSpeedSum;
        dst.batSpeedCount += src.batSpeedCount;
        dst.swingLengthSum += src.swingLengthSum;
        dst.swingLengthCount += src.swingLengthCount;
      }

      seasonStats[seasonKey] = {
        season: seasonKey,
        buckets: seasonBuckets
      };
    }

    const careerSeasonKey = "career";
    const careerSeason: SeasonStats = {
      season: careerSeasonKey,
      buckets: {
        all: toMetricStats(careerBuckets.all),
        early: toMetricStats(careerBuckets.early),
        ahead: toMetricStats(careerBuckets.ahead),
        behind: toMetricStats(careerBuckets.behind),
        two_strikes: toMetricStats(careerBuckets.two_strikes)
      }
    };

    seasonStats[careerSeasonKey] = careerSeason;

    result[name] = {
      name,
      seasons: seasonStats
    };
  }

  return result;
}

async function main() {
  const baseDir = process.cwd();
  const dataDir = path.join(baseDir, "statcast_data");
  const players: PlayerMap = {};
  const seasonYears = new Set<number>();

  let fileNames: string[] = [];
  if (fs.existsSync(dataDir)) {
    fileNames = fs.readdirSync(dataDir);
  }

  const hitterCsvs = fileNames.filter(
    n => n.startsWith("hitters_") && n.endsWith(".csv")
  );
  const batterCsvs = fileNames.filter(
    n => n.startsWith("batters_") && n.endsWith(".csv")
  );
  const csvFileNames = hitterCsvs.length > 0 ? hitterCsvs : batterCsvs;
  const pattern = hitterCsvs.length > 0 ? /hitters_(\d{4})\.csv$/ : /batters_(\d{4})\.csv$/;

  const files = csvFileNames
    .map(name => {
      const match = name.match(pattern);
      if (match) {
        const year = Number(match[1]);
        if (year >= 2023 && year <= 2026) {
          seasonYears.add(year);
        }
      }
      return path.join(dataDir, name);
    })
    .filter(full => fs.existsSync(full));

  if (files.length === 0) {
    console.error("No statcast_data CSVs found.");
    process.exit(1);
  }

  for (const file of files) {
    console.log(`Processing ${path.basename(file)}...`);
    await processFile(file, players);
  }

  const aggregates = buildAggregates(players);
  const outDir = path.join(baseDir, "data");
  const outPath = path.join(outDir, "hitter_aggregates.json");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(aggregates));

  const seasonList = Array.from(seasonYears)
    .sort((a, b) => a - b)
    .map(year => String(year));
  const metaPath = path.join(outDir, "meta.json");
  let careerLabel = "Career";
  if (seasonList.length === 1) {
    careerLabel = `Career (${seasonList[0]})`;
  } else if (seasonList.length > 1) {
    careerLabel = `Career (${seasonList[0]}–${seasonList[seasonList.length - 1]})`;
  }
  const meta = {
    availableSeasons: seasonList,
    careerLabel
  };
  fs.writeFileSync(metaPath, JSON.stringify(meta));

  console.log(`Wrote aggregates for ${Object.keys(aggregates).length} hitters to ${outPath}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

