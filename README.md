# 🎯 Game Recon

**A Claude Code skill that answers a game developer's most expensive question: *"Has someone already built this idea — and is it working?"***

Give it a concept ("yarn game with conveyor"), a game name, a store link, or just a screenshot — it exhaustively searches the **iOS App Store + Google Play**, judges every candidate's *mechanic* (not its name), and delivers an interactive visual report: every similar game, cross-store deduplicated, split into **Fresh launches** (your race rivals) and **Established 1M+** (who owns the space), with hover screenshots, install counts, and a fully auditable exclusion list.

Built for hybrid-casual game developers, where two studios routinely ship the same remix within weeks of each other — and finding out *after* three months of development is the most expensive way to learn.

## Why this exists

The existing workflow for checking "is my idea taken?" is broken in three specific ways:

1. **Third-party ranking/publisher platforms can't handle multi-keyword search.** Type "arrow sand puzzle" into most industry dashboards and you get *zero results* — the query is matched as one frozen phrase, so multi-mechanic hybrid concepts (which is what everyone builds now) collapse to nothing. Game Recon decomposes your keywords into singles, pairs (both word orders — the stores are order-sensitive), and phrases, then pools everything.

2. **There is no unified cross-store search.** Today you search the App Store, then separately search Google Play, then manually reconcile the two lists — same game, different subtitles, different developer legal names per store. Game Recon searches both stores in one run and merges duplicates into single cards showing both stores' numbers side by side.

3. **Name search misses mechanic clones.** The game that kills your idea might share zero words with your concept ("Pixel Flow!" vs "This is Blast!"). Only mechanic-level matching — reading store descriptions, mining verified titles for the family's real vocabulary — finds those.

## Why it's different

**It was adversarially built.** Every rule in this tool exists because a real hybrid-game developer caught a real miss during development. The design spec carries a [25-entry failure catalog](docs/superpowers/specs/2026-07-11-game-recon-design.md) — each entry a genuine bug (missed game, wrong ranking, false merge) with its root cause and the systematic fix, locked by a regression test. Highlights:

- **"drop arrow" ≠ "arrow drop"** — Google Play's search is word-order sensitive. Every keyword pair is searched in both orders.
- **Same game, different subtitles per store** — "Sand Balls - Puzzle Game" (Play) and "Sand Balls - Digger Puzzle" (iOS) merge into one card.
- **Same mechanic, zero shared words** — "Pixel Flow!" is invisible to every "blast" search. The *snowball wave* mines new vocabulary from mechanic-verified titles and sweeps again.
- **The skin is never the mechanic** — "Marble Legend" titles are usually Zuma shooters (impostors); Bus Jam and Block Jam are the same genre in different skins (family). Judgment reads store *descriptions*, guided by a [user-maintained mechanic taxonomy](skill/references/mechanic-taxonomy.md).
- **Wrong exclusions must be visible** — every judged-out game appears in a collapsed audit footer on the report, so a mistaken exclusion is catchable at a glance.

## What a run looks like

```
You:  有没有类似 this is blast 的游戏
Bot:  Is this a concept or a specific game?  → specific game
      Search depth? (precise ~2-3 min / standard / comprehensive)  → precise
      Platforms? (both / iOS / Android)  → both

  ~2 min: wave-1 report published (search + mechanic judgment)
  ~5 min: snowball wave update lands at the same URL
```

The report is a single self-contained HTML page: filterable, light/dark aware, monthly time dial for fresh launches, relevance/newest/downloads sorting, per-store `iOS ↗` / `Play ↗` links, hover screenshot panels for fresh games, and the exclusion audit footer.

## Install

Requires: [Claude Code](https://claude.com/claude-code), Python 3, macOS (uses `sips` for image resizing — Linux users: swap in Pillow).

```bash
git clone https://github.com/Vickywan123/game-recon.git
cd game-recon
./install.sh          # copies the skill to ~/.claude/skills/game-recon + creates its venv
```

Then in any Claude Code conversation:

> *"recon: merge tower defense"* · *"find games like Seat Away"* · *"查竞品：毛线+传送带"* · or paste a game screenshot

The only dependency is [`google-play-scraper`](https://pypi.org/project/google-play-scraper/) (installed into the skill's own venv). Apple data comes from the free iTunes Search API. No API keys.

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

US storefront only (for now) · revenue ranking disabled pending AppMagic integration · theme subscriptions/notifications on the deferred list · macOS image tooling.

## 中文简介

**为什么做这个工具**：现有的第三方排行/发行平台大多不支持多关键词搜索——输入"arrow sand puzzle"直接零结果，混合玩法概念根本查不了；而且查竞品要先搜 iOS、再单独搜安卓，同一款游戏两边名字还不一样，全靠人肉对账。

Game Recon 是一个 Claude Code 技能：输入玩法概念、游戏名、商店链接或截图，**一次跑完苹果+谷歌双商店**，多关键词自动拆解组合（正反词序都搜），按**机制**（而非名字）判断相似性，双商店同款自动合并，输出可交互的竞品全景报告——新品雷达 + 1M+ 老将、悬停截图、可审计的剔除清单。为混合休闲游戏开发者打造：在立项前发现"这个想法有没有人做过、做得怎么样"。工具的全部 25 条规则都来自真实开发者的实测纠错，每条都有回归测试锁定。

## License

MIT — see [LICENSE](LICENSE).
