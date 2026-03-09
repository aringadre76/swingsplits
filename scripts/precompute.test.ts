import { afterEach, describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, mkdirSync, writeFileSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

const createdDirs: string[] = [];

afterEach(() => {
  for (const dir of createdDirs.splice(0)) {
    rmSync(dir, { recursive: true, force: true });
  }
});

describe("precompute season metadata", () => {
  test("excludes empty future season files from availableSeasons", () => {
    const workspaceDir = mkdtempSync(join(tmpdir(), "swingsplits-precompute-"));
    createdDirs.push(workspaceDir);

    const statcastDir = join(workspaceDir, "statcast_data");
    mkdirSync(statcastDir, { recursive: true });

    const csvHeader = "batter_name,batter,game_year,bat_speed,swing_length,balls,strikes\n";
    const csvRow = "Judge,99,2025,75.1,7.2,0,0\n";

    writeFileSync(join(statcastDir, "hitters_2025.csv"), csvHeader + csvRow);
    writeFileSync(join(statcastDir, "hitters_2026.csv"), csvHeader);

    const result = Bun.spawnSync({
      cmd: ["bun", "/home/robot/swingsplits/scripts/precompute.ts"],
      cwd: workspaceDir,
      stdout: "pipe",
      stderr: "pipe"
    });

    expect(result.exitCode).toBe(0);

    const meta = JSON.parse(
      readFileSync(join(workspaceDir, "data", "meta.json"), "utf8")
    ) as { availableSeasons: string[]; careerLabel: string };

    expect(meta.availableSeasons).toEqual(["2025"]);
    expect(meta.careerLabel).toBe("Career (2025)");
  });
});
