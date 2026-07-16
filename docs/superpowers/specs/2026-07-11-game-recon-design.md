# Hybrid Game Radar (né Game Recon) — Design Spec (v1)

**Date:** 2026-07-11 · **Status:** Approved by user after 6 rounds of adversarial prototype testing
**Prototype pages:** [concept demo](https://claude.ai/code/artifact/936f6a65-823c-4a0c-b117-aeded5202452) · [Case A demo](https://claude.ai/code/artifact/a5a250a6-747b-4289-b0d2-1b46e2d5d82c)

## 1. Purpose

A Claude Code skill for hybrid-game developers answering one question fast: **"Has someone already built this idea, and is it working?"** Given a concept, game name, store link, or screenshot, it searches iOS + Google Play exhaustively and returns a visual report page. Success criterion = **no relevant game missed** (the user's #1 requirement). The page shows results only — no verdicts, no recommendations; conclusions are the user's.

## 2. Inputs

**Rule zero: always confirm input type before running.** For any text input (name or phrase), ask one question first:

> "Is this a **concept** (find everything in this space) or a **specific game** (find that game + its rivals)?"

No auto-detection — "arrow drop" is both a valid concept and an exact game title, and the two cases run differently.

| Input | Route |
|---|---|
| Apple/Play **URL** | Case A directly (unambiguous) |
| **Screenshot** | Reverse image search → Case A directly |
| **Any text** | **Ask first** → Case A or Case B |

**Case A — specific game:** keywords = the exact words of the game's title (from link lookup, store search, or image match). Exact title words are primary (drive relevance); synonym families still run as a secondary net. The identified game is pinned as the first card, with an honesty tag: "verified by image match" or "unconfirmed candidate".

**Screenshot sub-flow:** reverse image search (Google Lens via browser) to establish identity. If blocked: ask the user to run it (10 seconds) or present "top candidates, unconfirmed" — never assert an unverified identity.

**Case B — concept:** full creative pipeline — keyword decomposition, synonym families, mechanic combos.

## 3. Search rules

### 3.1 Term generation — three user-selected depths

**The user always chooses search depth before a run** (with time estimates; Precise recommended): **Precise** = input words + their pair combos only (~1–2 min) · **Standard** = + mechanic combos (~3–5 min) · **Comprehensive** = + synonym family (~8–15 min). Both word orders at every depth. Rationale: time scales with term count; only the user knows if this is a quick check or a due-diligence sweep. (Amended 2026-07-11 after v1 measured ~10 min for the always-full net.)

Term building blocks:
- **Singles** — every input/theme word alone (Apple limit 200, Play 25 hits)
- **Pairs** — every two-word combo, **in both word orders** (Play's search is order-sensitive: "arrow drop" ≠ "drop arrow")
- **Full phrase** — the input as typed
- **Synonym family** — object noun → its family (bead → marble, ball, pearl); each synonym gets singles + pairs
- **Mechanic combos** — action words without the object ("arrow drop", "drop sort", "arrow pop")

### 3.2 Sources & platform choice
Apple iTunes Search API (free, keyless) + Google Play via `google-play-scraper`. US storefront default. **The user chooses platforms per run: both (default) / Apple only / Android only.** Apple requests run in parallel (8 workers); Google Play searches are serial but detail fetches run gently parallel (3 workers, jittered). Snowball GP details capped at 100. Descriptions come from the gp_app cache + batched Apple lookups. Two-phase delivery: wave-1 page published at ~2–3 min, snowball updates the same URL. (Amended 2026-07-11 for the 3-minute target.)

### 3.3 Filtering — four gates
1. **Games only** (Apple `primaryGenreName == "Games"`)
2. **Genre gate + blocklist** — genres must include Puzzle/Casual/Board/Strategy AND must NOT include Sports or Racing (blocklist beats co-tags)
3. **Relevance gate** — title contains a theme-family word OR ≥2 mechanic words
4. **Mechanic verification** — read the store description; the mechanic vocabulary must match the concept family (tap/pull/drop/sort), and exclusion families (shoot/aim/zuma/cannon = Zuma shooters; bow/archery = shooting; board-game terms) reject the game even when the noun matches. In the skill this is Claude reading and judging, not a regex; borderline cases are kept and flagged, not silently dropped.

### 3.4 Relevance — tiered, anchored to the user's exact input words
- **Tier 0** — normalized title equals the input → always first, above any ranking
- **Tier 1** — title contains every input word → next
- **Tier 2** — remainder scored with THEME dominance (amended 2026-07-11, failure #22): theme input words ×20 · synonyms ×8 · mechanic-type input words ×5 · general mechanic words ×2 (capped at 3) · ties broken by downloads. Claude classifies each input word as theme (object/skin noun) or mechanic before the run; pure-mechanic concepts have no theme words and anchor on mechanics + description judgment.

Never anchor scoring to Claude's interpretation of the input — only to the user's words.

### 3.5 Network resilience & cache
20s timeout, 3 retries per request; failed terms are skipped, never fatal — the term list is deliberately redundant so one lost term ≠ one lost game. Designed for unstable VPN conditions. **Persistent cache** (`skill/cache/`, survives reinstalls): search results 1 day, per-game details 7 days — repeat and overlapping searches skip re-fetching. (Amended 2026-07-11.)

### 3.6 No caps
Every game passing the gates goes on the page. Completeness > tidiness.

## 4. Merging & dedup

**4.1 Within-store:** dedupe by store ID, then normalized name.

**4.2 Cross-store merge** — pass 0: identical normalized full title + complementary stores merges regardless of studio spelling (legal names differ per store). Then one card when ALL three hold:
1. Same studio (normalized, case/punctuation-insensitive)
2. Name match, subtitle-aware — prefix match OR equal base names after stripping past a separator (`-` `:` `–` `|`); unites "Sand Balls - Puzzle Game" / "Sand Balls - Digger Puzzle"
3. Complementary stores (one iOS-only + one Play-only) — the safety lock preventing two different iOS games from merging

**4.3 Merged card:** both store links, earliest release date, both stores' numbers side by side.

**4.4 Philosophy:** merge on the loose side — a wrong merge is visible, a missed merge is invisible.

## 5. Output page

One self-contained web page (Artifact), fresh data per run, one page per concept/game (re-runs update in place). Light/dark theme aware.

**5.1 Header** — Case A: title = **the exact game name**, never abstracted keywords. Case B: the concept as typed. One neutral factual sub-line. **No verdict banner, no counts-as-advice, no recommendations.**

**5.2 Case A pin** — the identified game as the first card with its honesty tag.

**5.3 Two sections:**

| Section | Contains | Controls |
|---|---|---|
| 🌱 **Fresh launches** | Every game under 1M downloads, filtered by time dial | Dial: **1–12 months (monthly steps)** + "1 year + (all)"; default 2 months · Sort: **most relevant (default)** / newest / most downloaded |
| 🏆 **Established** | Every game with 1M+ downloads, any age | Sort: **most relevant (default)** / most downloaded / newest / revenue (disabled until AppMagic) |

No long-tail bucket — it lives at the dial's "all" stop. Hidden-count hint ("+N older games not shown — widen the period"). Nothing silently dropped.

**5.4 Cards** — 64px embedded icon · name + studio · age badge (red ≤3 weeks / amber older / dashed **"date unknown"** / red **"upcoming"** for future dates) · separately clickable **iOS ↗ / Play ↗** badges · Play installs + Apple ★rating·reviews side by side. **Hover screenshot panel** (up to 4 store screenshots, 200px, embedded): **Fresh-tier games only** — devs already know the 1M+ hits (user decision 2026-07-11).

**5.5 Filter box** — live text filter; if a query only matches dial-hidden games, the page auto-widens to "all" — search never falsely empty.

## 6. Known failure modes & fixes (institutional memory)

| # | Failure | Real example | Fix |
|---|---|---|---|
| 1 | Multi-keyword search → 0 results | LionSense "arrow sand puzzle" | Decompose into singles/pairs/phrase (§3.1) |
| 2 | Found but not shown | Sand Loop, Sand Crush | No display caps (§3.6) |
| 3 | Android invisible | com.pc.sand.loop | Both stores, every term (§3.2) |
| 4 | New-but-tiny game buried | Sand Arrow Out (0 reviews, 25d) | Fresh lane, 0-download games first-class (§5.3) |
| 5 | Same game twice | Sand Balls (two subtitles) | Base-name + studio merge (§4.2) |
| 6 | Synonym blindness | Marble Arrows in a "bead" search | Synonym families (§3.1) |
| 7 | Action-named games missed | Drop Arrow Pop | Mechanic combos (§3.1) |
| 8 | Play word-order sensitivity | "arrow drop" ≠ "drop arrow" | Both orders always (§3.1) |
| 9 | Wrong exact-match claimed | Bead Loop asserted; truth = Arrow Drop | Reverse image search; unverified = labeled candidates (§2) |
| 10 | Off-genre co-tag leak | Marble Arena - Football Cup (Sports+Casual) | Genre blocklist (§3.3) |
| 11 | Off-theme vocabulary leak | Stack Ball in "arrow sand" | Score anchored to input words (§3.4) |
| 12 | Term dies on bad network | 2 terms failed mid-run (VPN) | Retries + redundant terms (§3.5) |
| 13 | Same noun, wrong mechanic | 67 Zuma shooters titled "Marble…" | Description-level mechanic verification (§3.3) |
| 14 | Missing release dates | Play omits dates on old games | "date unknown" chip, never blank (§5.4) |
| 15 | Ranking ignored exact match | Arrow Drop at bottom of its own search | Tier 0/1/2 relevance (§3.4) |
| 16 | Input-word lineage missing | No arrow hits in Established | Every input word runs as full single term (§3.1) |
| 17 | Same mechanic, zero shared title words | "Pixel Flow!" invisible to every "blast" net | Post-judgment snowball: mine verified titles for new vocabulary, sweep again (snowball.py). Mining the raw pool fails — impostor genres dominate (measured) |
| 18 | Same game, different legal studio names per store | Pixel Flow! (Loom Games Oyun… / Loom Games A.Ş.) shown twice | Merge pass 0: identical normalized title + complementary stores merges regardless of studio (§4.2) |
| 19 | Future-dated release ranks first under "newest" | King Match 3D showed "-52d ago" at position 1 | Negative days → "upcoming" badge, sorts as day 0 (§5.4) |
| 20 | Irrelevant games outrank true matches under "most relevant" | Coffee Craze (mined-word hits) above Thread Jam in yarn run | Snowball additions scored with the user's synonyms only; mined words widen the net, never the ranking (§3.4) |
| 21 | Snowball mines generic vocabulary | color/away/sorting mined from yarn titles → 445 noise candidates | Known-word variants + hyper-casual filler in STOP; variant-aware known check (§3.1) |
| 22 | Mechanic-word-only games outrank theme games | "conveyor jam" above yarn games in yarn run | Theme/mechanic input-word classification; theme ×20 dominates (§3.4) |
| 23 | Same-mechanic games excluded for wearing a different skin | Bus Jam / Car Match judged out of the Block Jam run | Skin is never grounds for exclusion; jam/collection genres span blocks/buses/cars/goods. Wrong exclusions also starve the snowball (§3.3) |
| 24 | Mined single word drags in whole genres | "find"/"logic"/"frenzy" flooded Seat Away with hidden-object, logic-grid, bingo | Mined singles need ≥3 verified-title occurrences; combos always allowed (verified combos still catch Pixel Flow) (§3.1) |
| 25 | Lazy round-2 judgment (sampling + regex) | Bingo Frenzy, Cooking Madness reached Established | Round 2 must read every snowball name; no sampling (§3.3) |
| 26 | Taxonomy used for judgment but not for search seeding | Ant picture-clearing concept missed its family's canonical hits (This is Blast, Pixel Flow — queue family, ants are just the skin) | Classify concept into a taxonomy family BEFORE config; family's canonical hits + skins + vocab seed the search (§3.1, SKILL.md Step 1) |
| 27 | Exclusion misses punctuation variants of the same title | "Block Blast!" survived an exclusion written "Block Blast！" (full-width bang) | apply_exclusions matches normalized names, same standard as the merge (§3.3) |
| 28 | Universal filler words mined as family vocabulary | "block"/"escape" from arrow-out titles pulled in 240 grid-fill + room-escape games | STOP list covers industry-wide fillers (block/escape/room/wood/tap/drop/jewel/cube/slide/maze) (§3.1) |

**Standing rule:** user reports a miss → diagnose → fix the class, not the instance → add a row here.

## 7. Deferred features (parked, decide later)

1. **Theme subscription + notifications** — scheduled re-runs per subscribed theme; notify only on new games vs. last run. Supersedes the "merge LionSense/YouTube/WeChat feeds" idea.
2. **AppMagic revenue** — enables the revenue sort (dropdown already present, disabled). Needs user's logged-in browser.
3. **Non-US storefronts** — CN etc., for Asia soft-launches.
4. **Website version** — same engine, team-facing; costs: hosting, server-side Play scraping fragility, paid vision API for screenshots.

## 8. Technical notes

- **Data:** iTunes Search API · `google-play-scraper` (Python, venv) · Google Lens reverse image search (browser, user-assisted fallback)
- **Runtime:** ~2–5 min/run (Play detail fetches + icons dominate); icons resized to 64px via `sips`
- **Prototype provenance:** validated scripts in session scratchpad — `build_final.py` (search+gate pipeline), merge/rescore snippets, `gen5.py`/`gen_bead.py` (page generators), `template5.html` (final page template). The skill packages this logic.
