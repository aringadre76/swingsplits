# Swingsplits × ABS Challenge System: Player Archetype Conclusions

> **Data as of April 2, 2026** — first week of the 2026 MLB season.
> 106 batters appear in both the ABS leaderboard and the Statcast swing-split data.
> All correlations and percentages should be treated as early-season signals, not settled truth.

---

## Executive Summary

The Automated Ball-Strike (ABS) challenge system rewards a specific and somewhat surprising player type. The intuitive prediction — that disciplined, compact-swing "contact hitters" would dominate by making better pitch-recognition decisions — turns out to be wrong. The best ABS challengers are instead **patient hitters with longer swings who dramatically slow their bat speed in two-strike counts**. The worst are **fast-swinging hitters who can't establish a two-strike approach**, and **compact swingers who are systematically getting the zone edge wrong**.

The key dimensions that separate winners from losers are, in order of predictive strength:

1. **Whether a hitter decelerates meaningfully in two-strike counts** (approach)
2. **Swing length** — longer is better, counterintuitively
3. **The "Loopy" archetype** — moderate bat speed, long swing — dominates
4. **Consistency of approach across counts** — wide situational swings hurt

What does *not* predict ABS success: raw bat speed, swing *shortening* in two-strike counts, how much you slow down when *behind* in the count, or how ingrained your career habits are.

---

## Methodology: The Four Swing Archetypes

Players were classified on two dimensions relative to the 2026 cohort median (70.3 mph bat speed, 7.30 ft swing length):

| Archetype | Bat Speed | Swing Length | Description |
|-----------|-----------|--------------|-------------|
| **Power** | High (≥70.3) | Long (≥7.30) | Classic slugger profile |
| **Whip** | High (≥70.3) | Short (<7.30) | Elite bat speed, compact swing |
| **Loopy** | Low (<70.3) | Long (≥7.30) | Slow-to-contact, longer arc |
| **Contact** | Low (<70.3) | Short (<7.30) | Compact, controlled hitter |

Two-strike *approach* was classified separately:

| Approach | Definition |
|----------|-----------|
| **Protector** | Decelerates ≥1 mph **and** shortens ≥0.2 ft in two-strike counts |
| **Decelerator** | Decelerates ≥1 mph but does **not** significantly shorten |
| **Shortener** | Shortens ≥0.2 ft but does **not** significantly decelerate |
| **Extender** | Accelerates ≥1 mph **or** lengthens ≥0.2 ft in two-strike counts |
| **Neutral** | No significant change on either dimension |

---

## Finding 1: The "Loopy" Hitter Is the Best ABS Challenger

The biggest surprise in the data is that the **Loopy archetype** — below-median bat speed, above-median swing length — dramatically outperforms every other swing type.

| Archetype | n | Avg tvse | Avg overturn rate | Ks avoided | Walks created |
|-----------|---|----------|-------------------|------------|---------------|
| **Loopy** | 13 | **+0.85** | **97%** | 7 | 2 |
| Power | 40 | +0.01 | 91% | 9 | 4 |
| Contact | 40 | −0.08 | 88% | 8 | 4 |
| Whip | 13 | −0.14 | 86% | 2 | 0 |

"Loopy" hitters carry a 97% overturn rate and the best average performance vs the model (+0.85). They account for 21% of the top-half of performers but only 4% of the bottom half — a **+17 percentage point overrepresentation** at the top.

### Why does this make sense?

Loopy hitters — slower bat speed, longer swing arc — are by definition committing to their swing later and with a different trajectory than compact swingers. Their longer path through the zone means they can physically make contact on pitches deeper in the zone, so when they *choose to take* a pitch, it is a more deliberate decision. They are not relying on bat speed to bail them out if they guess wrong. Their takes are therefore more meaningful — and more often at pitches that are genuinely off the plate. This makes their challenges more accurate.

Examples from the data: Kerry Carpenter (DET), Josh Bell (MIN), Marcell Ozuna (PIT) — moderate bat speeds, longer swings, strong ABS results.

### The Whip archetype is the worst

Whip hitters (fast but compact) are the opposite of Loopy. At 86% overturn rate and −0.14 avg tvse, they underperform despite the intuition that a fast, short swing should mean better pitch recognition. What likely happens: their elite bat speed means they can still make contact on pitches outside the zone if they commit, so their takes are less selective. When they challenge, they're choosing pitches that are less reliably wrong.

---

## Finding 2: Decelerating in Two-Strike Counts Predicts ABS Success More Than Shortening

The most practically important finding: **it's not how much you shorten your swing with two strikes, but how much you slow your bat speed down**.

| Approach | n | Avg tvse | Avg overturn rate |
|----------|---|----------|-------------------|
| **Decelerator** | 15 | **+0.91** | **96%** |
| Extender | 9 | +0.38 | 94% |
| Protector | 10 | +0.44 | 90% |
| Neutral | 25 | +0.26 | 92% |
| **Shortener** | 4 | **−1.16** | 100% |

**Decelerators** — who meaningfully slow their bat speed in two-strike counts (avg −2.23 mph) without necessarily shortening their swing path — have the best ABS profile in the entire dataset. They win at 96% and are +0.91 vs expected.

**Shorteners** — who compress their swing path but maintain or even gain bat speed — have the worst average tvse (−1.16) despite a 100% overturn rate. The 100% overturn rate tells us they do win the challenges they make, but the negative tvse says they're not challenging *enough* relative to the model's expectation, or challenging at suboptimal moments. Shortening your swing does not, by itself, translate into better challenge decision-making.

### The interpretation

Decelerating in two-strike counts is a marker of a hitter who is **genuinely in a different cognitive and physical mode** with two strikes. They are not protecting the plate by cutting their swing down — they are instead resetting to a slower, more deliberate contact process. This deliberateness probably extends to their take decisions too: they slow down, they see the pitch longer, and when they take a borderline pitch and it's called a strike, they are more confident it was wrong.

Shortening the swing without decelerating may actually reflect *urgency* — a hitter who is trying to get the bat through faster on a shorter path. This is a defensive mechanical adjustment, not a zone-awareness adjustment. It shows in the ABS data.

**In practical terms:** Aaron Judge decelerates −4.1 mph in two-strike counts and went 1-for-1 on ABS challenges. Jose Altuve decelerates −5.0 mph and went 2-for-3. Ivan Herrera decelerates −2.65 mph and is the #1 performer by tvse (+2.82). Meanwhile Spencer Torkelson shortens his swing by −0.24 ft without decelerating — and went 0-for-1 with the worst tvse in the Shortener group.

---

## Finding 3: Longer Swing = Better ABS Outcomes (Counterintuitive)

Across swing length quintiles:

| Quintile | Avg swing length | Avg tvse | Avg overturn rate |
|----------|-----------------|----------|-------------------|
| Q1 (shortest, ≤6.63 ft) | 6.63 ft | +0.07 | 82% |
| Q2 (6.63–7.01 ft) | 7.01 ft | −0.04 | 100% |
| Q3 (7.01–7.30 ft) | 7.30 ft | −0.19 | 83% |
| Q4 (7.30–7.51 ft) | 7.51 ft | +0.26 | 90% |
| **Q5 (longest, ≥7.51 ft)** | 7.87 ft | **+0.21** | **96%** |

The longest-swing hitters (Q5) win at 96% — the best of any length group. The shortest-swing hitters (Q1) win at only 82%. Pearson r between swing length and overturn rate = **+0.20**, the strongest single-variable correlation in the entire dataset for predicting challenge success.

Top ABS performers by tvse include Ivan Herrera (7.92 ft swing — massive), Aaron Judge (8.10 ft), Josh Bell (7.91 ft), Kerry Carpenter (7.80 ft), Austin Wells (7.79 ft, though negative tvse from bad challenge selection).

This aligns with the Loopy archetype finding: a long swing is associated with more patient, deliberate approach, and those hitters' takes are more reliable signals that a pitch was actually off the plate.

**The key exception:** Q2 (mid-short) hits 100% overturn rate in a small sample, likely a noise artifact. The structural trend is that Q1 and Q3 underperform, while Q4 and Q5 outperform.

---

## Finding 4: Power Hitters' ABS Fate Depends on Their Approach — Not Their Power

Power hitters as a group are exactly average (+0.01 tvse, 91% overturn rate). But inside the group, approach archetype creates a massive split:

**Power/Decelerator** (e.g., Aaron Judge: −4.1 mph two-strike bat delta): Top of the leaderboard.
**Power/Protector** (e.g., Ivan Herrera: −2.65 mph bat delta, −0.41 ft length delta): #1 overall.
**Power/Unknown or Power/flat**: Dominates the bottom of the leaderboard — Ronald Acuna Jr. (1/3), Luis Garcia Jr. (0/2), Austin Wells (0/1), Oneil Cruz (0/1), Jake Burger (1/1 but −1.84 tvse).

The implication: **bat speed is neutral**. A 77 mph bat speed (Oneil Cruz) neither helps nor hurts if you're not engaging in any deliberate approach change with two strikes. Power hitters who approach two-strike counts with the same aggression they use when ahead are challenging pitches that, even if borderline, are closer to the zone than they think.

---

## Finding 5: Wide Situational Swing Adjustment Hurts

Hitters were ranked by the gap between their swing length when ahead in the count vs. when they have two strikes. The hypothesis was that a bigger gap = better zone reader = better ABS challenger. The data says the opposite.

| Group | Avg gap | Avg tvse | Avg overturn rate |
|-------|---------|----------|-------------------|
| Wide gap (top third: ≥0.4 ft) | +0.64 ft | −0.17 | 85% |
| Moderate gap (middle third) | +0.09 ft | +0.22 | 95% |
| Narrow gap (bottom third: flat or inverted) | −0.37 ft | +0.23 | 92% |

Pearson r (ahead→two-strike length gap vs tvse) = **−0.12**.

The "range readers" — hitters who expand enormously when ahead and collapse when behind — are the *worst* ABS performers. The hitters with a flat approach across counts are the *best*.

### Why?

Hitters with giant situational swings are essentially "hackers with a panic button." When ahead, they expand their zone and slash. When they have two strikes, they collapse to survival mode. Their takes in two-strike counts come from a completely different mental frame than their takes when ahead, and the challenge decisions from that panicked state may not reflect accurate pitch location perception.

By contrast, hitters with consistent swings across counts are applying the same zone assessment at every pitch. Their takes are more uniform, their take zone is more reliable, and so when a borderline pitch is called a strike, they genuinely know it was wrong. Their challenges are based on calibrated knowledge of the zone, not situational instinct.

---

## Finding 6: No One Escapes Being Overturned Against

When fielders (pitchers/catchers) challenge a called ball — arguing it was actually a strike by the ABS definition — they are winning essentially **100% of the time** regardless of the batter's archetype.

| Swing archetype | Avg overturn rate against |
|-----------------|--------------------------|
| Power | 100% |
| Contact | 95% |
| Whip | 90% |
| Loopy | 83% |

Loopy hitters are best at not getting called: only 83% of fielder challenges against them succeed. But even that is a high number. This means almost every batter, across all styles, is occasionally receiving called balls that are technically within the ABS strike zone definition. The ABS zone (top at 53.5% of height, bottom at 27%, judged at the middle of the plate) creates a zone that is meaningfully different from historical umpire zones — and pitchers and catchers are already learning to exploit this.

The implication for future seasons: as pitching staffs learn which pitch types and locations fall inside the ABS zone but get called as balls by umpires, the fielder challenge will become an increasingly powerful weapon. Every batter profile has vulnerability here.

---

## Finding 7: Career Habits Are Irrelevant — ABS Is Learned in Real Time

Neither a player's career two-strike swing length habit nor their in-season adjustment predicts ABS success:

- Pearson r (career ts_len_delta vs tvse) = **+0.009** — essentially zero
- Pearson r (2026 in-season ts_len_delta vs tvse) = **+0.050** — still negligible

What this means: whether you've spent years shortening your swing in two-strike counts (a deeply ingrained habit) or you're doing it for the first time in 2026, it doesn't make you better or worse at winning ABS challenges. The skill of knowing which borderline take to challenge is not the same as the skill of shortening your swing.

Interestingly, some of the best ABS performers in 2026 have *extended* their two-strike swing length relative to their career norm — Mike Trout (+0.24 ft shift, 3/4 challenges won), Pete Alonso (+0.26 ft shift, 2/2), Ryan Jeffers (+0.35 ft shift, 2/2). These players may be deliberately lengthening in two-strike counts as a strategic posture: swinging deliberately on pitches they choose to swing at, trusting the ABS system to back them up on takes.

The players who shortened dramatically relative to their career norm — Vladimir Guerrero Jr. (−0.47 ft shift, 0/1), Brayan Rocchio (−0.41 ft shift, 0/1), Spencer Torkelson (−0.27 ft shift, 0/1) — are generally underperforming. The "panic shorten" response to having two strikes and the ABS system present is not working.

---

## Finding 8: Behind-Count Approach Tells Us Nothing

Hitters who slow down dramatically when they're behind in the count (0-2, 1-2) have essentially identical ABS performance to hitters who maintain or even increase bat speed when behind:

| Group | Avg behind-count bat delta | Avg tvse | Avg overturn rate |
|-------|--------------------------|----------|-------------------|
| Big droppers (≤−2 mph) | −4.78 mph | +0.16 | 92% |
| Moderate droppers | −1.38 mph | −0.13 | 88% |
| Flat / gainers | +1.04 mph | +0.16 | 91% |

Pearson r (behind-count bat delta vs tvse) = **−0.001** — perfect noise.

This matters because "behind-count approach" is often used as a proxy for plate discipline in traditional analysis. Here it is completely uncorrelated with ABS success. A hitter can be in full panic-protection mode when behind and still challenge or fail to challenge the wrong pitches. The two-strike *take* decision and the two-strike *swing* profile are measuring different things.

---

## The Ideal ABS Challenger — Profile

Based on the combined evidence across all analyses, the player most likely to succeed at ABS challenges has this profile:

1. **Loopy or Power swing archetype** — longer swing path (≥7.30 ft), moderate-to-high bat speed
2. **Decelerator approach in two-strike counts** — slows bat speed by ≥1 mph, does not collapse the swing length
3. **Consistent approach across counts** — the gap between ahead-count and two-strike swing length is small (less than ±0.2 ft)
4. **Not a reactive shortener** — does not panic-shorten when two strikes arrive; instead slows deliberately
5. **Longer swing in general** — in the top two quintiles of swing length

**Archetype in prose:** *A patient hitter with a deliberate, slightly long stroke who genuinely slows everything down with two strikes — not by chopping the swing off, but by resetting into a more controlled mode. When they take a pitch, that take is a considered decision. And when that pitch is called a strike, they know with confidence it was wrong.*

---

## The Worst ABS Challenger — Profile

1. **Whip archetype** — high bat speed, compact swing — or Power hitters with no established two-strike approach
2. **Shortener approach** — compresses swing path in two-strike counts without decelerating
3. **Wide situational swing gap** — hacks enormously when ahead, collapses in two-strike counts
4. **Unknown / inconsistent approach** — not enough two-strike swings to establish a pattern (new players, or players who take very few two-strike swings)
5. **Fastest swingers (Q4 bat speed, >71.9 mph)** — despite enormous bat speed, win only 86%

**Archetype in prose:** *An aggressive hitter who expands their zone when winning and panics mechanically when losing. Their two-strike takes are reactive survival decisions, not calibrated zone-reads. When a borderline pitch is called a strike, they may genuinely not know if it was right or wrong — so their challenge decisions are partly guesswork.*

---

## Notable Individual Players

### The Good

| Player | Team | ABS | tvse | Swing arch | Approach | Why it works |
|--------|------|-----|------|------------|----------|--------------|
| **Ivan Herrera** | STL | 2/2 | +2.82 | Power | Protector | Shortens AND decelerates; the most complete two-strike adjustment |
| **Kerry Carpenter** | DET | 1/1 | +2.80 | Loopy | Decelerator | Classic Loopy/Decelerator profile; slow, deliberate with 2 strikes |
| **Aaron Judge** | NYY | 1/1 | +2.46 | Power | Decelerator | −4.1 mph two-strike bat delta; genuinely shifts into a different mode |
| **Tyler Stephenson** | CIN | 2/2 | +2.38 | Power | — | Insufficient two-strike data but wins everything he challenges |
| **Jonathan Aranda** | TB | 1/1 | +2.12 | Contact | Decelerator | Contact hitter who decelerates well; challenges confidently |
| **Jose Altuve** | HOU | 2/3 | +1.07 | Contact | Decelerator | Most dramatic two-strike deceleration (−5.0 mph); challenges frequently |

### The Struggling

| Player | Team | ABS | tvse | Swing arch | Approach | Why it's hard |
|--------|------|-----|------|------------|----------|---------------|
| **Matt Wallner** | MIN | 1/3 | −2.40 | Whip | Unknown | No two-strike two-strike pattern; challenges often, wins rarely |
| **Wyatt Langford** | TEX | 0/2 | −2.39 | Whip | Unknown | Whip hitters without established approach consistently underperform |
| **Gabriel Arias** | CLE | 0/2 | −2.20 | Whip | Unknown | Same pattern: fast bat, short swing, no two-strike system |
| **Ronald Acuna Jr.** | ATL | 1/3 | −1.75 | Power | Unknown | Insufficient two-strike data; may need to establish a 2026 approach |
| **Leo Rivas** | SEA | 0/2 | −1.82 | Contact | Shortener | Shortens significantly but doesn't decelerate; challenges blindly |
| **Spencer Torkelson** | DET | 0/1 | −1.91 | Power | Shortener | Same Shortener trap as Rivas; mechanics without zone-read |

---

## Team-Level Patterns (Early Signal)

| Team | Players tracked | Avg tvse | Avg win rate |
|------|----------------|----------|--------------|
| LAD | 1 | +1.19 | 100% |
| TB | 3 | +1.01 | 83% |
| STL | 2 | +1.01 | 100% |
| BAL | 5 | +0.97 | 100% |
| CHC | 3 | +0.96 | 100% |
| CIN | 6 | +0.79 | 100% |
| MIN | 6 | +0.50 | 87% |
| ATH | 4 | +0.44 | 100% |

Cincinnati stands out as an early team-wide ABS success story with 6 players tracked, all winning every challenge and a +0.79 avg tvse. Their roster (Stephenson, De La Cruz, Suarez, Benson) spans multiple archetypes — suggesting an organizational approach to challenge selection rather than individual player profiles.

Minnesota is interesting: 6 players tracked, 87% win rate, +0.50 avg tvse — solid but driven by a range of profiles including some strugglers.

Baltimore (5 players, 100% win rate) is notable for having Gunnar Henderson, Pete Alonso, Coby Mayo, Colton Cowser, and Samuel Basallo — a mix that skews Power and Whip but is winning everything so far.

---

## Caveats and Limits

**Small sample size.** The 2026 season is six days old. 163 total batter challenges have been recorded. Many players have only 1 challenge on record, meaning their individual profiles are highly noise-prone. The archetype-level findings (16+ players per group) are more reliable than individual player rankings.

**ABS zone vs perceived zone.** The ABS zone (53.5%/27% of height, judged at the plate midpoint) is a fixed geometric definition. Players may be learning in real time where their personal ABS zone edge sits. Early-season challenge decisions will improve as that learning accumulates. This may cause the patterns here to shift substantially as the season progresses.

**Two-strike swing data requires sufficient swings.** 43 of 106 players are classified as "Unknown" approach because they don't yet have enough two-strike swings in 2026 to compute a reliable delta. As the season grows, this classification will fill in, potentially changing archetype group sizes significantly.

**Correlation ≠ causation.** The finding that Loopy hitters excel doesn't mean any hitter should try to become Loopy. It reflects that hitters with that existing profile happen to make better challenge decisions, likely due to underlying traits (patience, pitch recognition, deliberateness) that are expressed in both their swing profile and their ABS challenge behavior.

**Re-run this analysis.** All scripts are in `scripts/`. Run `python3 scripts/abs_archetypes.py` and `python3 scripts/run_analysis.py` to refresh findings as the season progresses. Run `python3 scripts/download_abs.py && python3 scripts/gen_league_context.py` to refresh the ABS data from Baseball Savant.

---

---

## 2026 Season Progress Update

**New Players:** Several new faces have emerged in the 2026 ABS landscape:
- **Austin Martin (MIN):** 2/2 challenges, +1.43 tvse, Contact archetype with Neutral approach
- **Will Benson (CIN):** 2/2 challenges, +1.61 tvse, Power archetype with Unknown approach
- **Munetaka Murakami (CWS):** 1/1 challenge, +1.45 tvse - elite first-sample performance

**Team Performance Notes:**
- **Cincinnati (CIN):** 6 players tracked, all 100% win rate, avg tvse +0.79 - strongest team showing
- **Baltimore (BAL):** 5 players, 100% win rate, featuring Alonso (+1.58), Mayo (+2.63), Henderson, Cowser, Basallo
- **New York Yankees (NYY):** 7 players, 86% win rate - mixed results despite high-profile names
- **Texas Rangers (TEX):** -1.29 avg tvse - struggling with shortener/whip archetype mix

**Key 2026 Developments:**
- Swing shortening in two-strike counts jumped to 15.3% in 2026 from 3.6% in 2025 - a 4x increase
- League-wide avg bat speed increased to 69.72 mph from 69.18 in 2025
- Two-strike bat delta deepened from -0.69 to -0.99 mph - hitters are consciously slowing down more

**Notable Players Expanding Swing in 2026 vs Career:**
- Ryan Jeffers (+0.35 ft shift, 2/2 ABS, +1.11 tvse) - PD pattern working
- Colton Cowser (+0.19 ft shift, 1/1 ABS, +0.43 tvse) - BAL power hitting
- Mike Trout (+0.24 ft shift, 3/4 ABS, +0.48 tvse) - veteran adaptation
- Pete Alonso (+0.26 ft shift, 2/2 ABS, +1.58 tvse) - swing extension working

*Data updated: April 2, 2026 after latest analysis run. Scripts in `scripts/` can be re-run for current stats.**