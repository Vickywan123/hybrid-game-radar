# 🎯 Hybrid Game Radar

**A Claude Code skill that answers a puzzle developer's most expensive question: *"Has someone already built this idea — and is it working?"***

Give it a concept ("yarn game with conveyor"), a game name, a store link, or just a screenshot — it exhaustively searches the **iOS App Store + Google Play**, judges every candidate's *mechanic* (not its name), and delivers an interactive visual report: every similar puzzle game, cross-store deduplicated, split into **Fresh launches** (your race rivals) and **Established 1M+** (who owns the space), with hover screenshots, install counts, and a fully auditable exclusion list.

Built for the **puzzle vertical of hybrid-casual**, where everyone remixes the same handful of hits — so two studios routinely land on the same idea within weeks of each other. The whole point is to check **before** you build: if someone already shipped your idea, you simply don't build it — and spend those months on an idea that's actually open.

## Why this exists

The existing workflow for checking "is my idea taken?" is broken in three specific ways:

1. **Third-party ranking/publisher platforms can't handle multi-keyword search.** Type "Arrow Bus puzzle" into most industry dashboards and you get *zero results* — the query is matched as one frozen phrase, so multi-mechanic hybrid concepts (which is what everyone builds now) collapse to nothing. Hybrid Game Radar decomposes your keywords into singles, pairs (both word orders — the stores are order-sensitive), and phrases, then pools everything.

2. **There is no unified cross-store search.** Today you search the App Store, then separately search Google Play, then manually reconcile the two lists — same game, different subtitles, different developer legal names per store. Hybrid Game Radar searches both stores in one run and merges duplicates into single cards showing both stores' numbers side by side.

3. **Name search misses mechanic clones.** The game that kills your idea might share zero words with your concept ("Pixel Flow!" vs "This is Blast!"). Only mechanic-level matching — reading store descriptions, mining verified titles for the family's real vocabulary — finds those.

## What a run looks like

```
You:  find games like This is Blast
Bot:  Is this a concept or a specific game?  → specific game
      Search depth? (precise ~2-3 min / standard / comprehensive)  → precise
      Platforms? (both / iOS / Android)  → both

  ~2 min: wave-1 report published (search + mechanic judgment)
  ~5 min: snowball wave update lands at the same URL
```

**Three search depths — start with Precise.** Every run asks you to pick:

| Depth | What it searches | First-run time |
|---|---|---|
| **Precise (recommended)** | your keywords + their combinations | ~2–3 min |
| Standard | + mechanic-word combos (sort/pop/tap…) | ~4–6 min |
| Comprehensive | + synonym families (bead→marble/ball…) | ~8–15 min |

Start with Precise — it covers most checks in a coffee-break; only go deeper when the results look thin. Results are cached, so a follow-up deeper run on the same concept is much faster than its cold estimate.

The report is a single self-contained HTML page: filterable, light/dark aware, monthly time dial for fresh launches, relevance/newest/downloads sorting, per-store `iOS ↗` / `Play ↗` links, hover screenshot panels for fresh games, and the exclusion audit footer.

## Install

Requires: [Claude Code](https://claude.com/claude-code) and Python 3. **Cross-platform** — macOS, Linux, and Windows (image processing uses Pillow, no OS-specific tools).

macOS / Linux:

```bash
git clone https://github.com/Vickywan123/hybrid-game-radar.git
cd hybrid-game-radar
./install.sh          # copies the skill to ~/.claude/skills/hybrid-game-radar + creates its venv
```

Windows (PowerShell):

```powershell
git clone https://github.com/Vickywan123/hybrid-game-radar.git
Copy-Item -Recurse hybrid-game-radar\skill "$env:USERPROFILE\.claude\skills\hybrid-game-radar"
python -m venv "$env:USERPROFILE\.claude\skills\hybrid-game-radar\venv"
& "$env:USERPROFILE\.claude\skills\hybrid-game-radar\venv\Scripts\pip" install google-play-scraper pillow
```

Then in any Claude Code conversation:

> *"recon: merge tower defense"* · *"find games like Seat Away"* · *"check this idea: yarn + conveyor"* · or paste a game screenshot

Dependencies: [`google-play-scraper`](https://pypi.org/project/google-play-scraper/) and [`Pillow`](https://pypi.org/project/pillow/) (installed into the skill's own venv). Apple data comes from the free iTunes Search API. No API keys.

## Architecture

Deterministic work lives in parameterized Python scripts; judgment work is done by Claude at runtime, orchestrated by [SKILL.md](skill/SKILL.md):

```
search_stores.py       term generation (depth tiers, both word orders) → both stores
                       (Apple parallel ×8, Play gently parallel ×3, persistent cache)
merge_score.py         cross-store dedup (subtitle- & studio-variant aware)
                       + tiered relevance (exact title > all words > theme×20 > synonyms > mechanics)
fetch_descriptions.py  judgment set (cache + batched Apple lookups)
      ── Claude reads every description, judges mechanic vs. taxonomy ──
snowball.py            mines vocabulary from verified titles, sweeps again
                       (catches same-mechanic games with zero shared words)
gen_page.py            icons + hover screenshots (cached, parallel ×16) → report.html
```

A cold end-to-end run at precise depth takes ~3 minutes; cached re-runs are far faster. 12 regression tests cover the failure catalog (`skill/tests/`).

## Docs

- [Design spec + 25-entry failure catalog](docs/superpowers/specs/2026-07-11-game-recon-design.md)
- [Implementation plan](docs/superpowers/plans/2026-07-11-game-recon-skill.md)
- [Mechanic taxonomy (user-maintained)](skill/references/mechanic-taxonomy.md)

## Known limits

**Puzzle-genre hybrids only** — the genre gates and mechanic taxonomy are tuned for the puzzle vertical (simulation/arcade/io hybrids are out of scope for now) · US storefront only · revenue ranking disabled pending AppMagic integration · theme subscriptions/notifications on the deferred list.

## License

MIT — see [LICENSE](LICENSE).
