---
name: game-recon
description: Search iOS App Store + Google Play for games similar to a concept, game name, store link, or screenshot, and deliver a visual competitive-landscape report page (Fresh launches vs Established 1M+). Use this whenever a game developer wants to know if an idea already exists, asks for similar games, competitor check, market check for a hybrid-game idea, shares a game screenshot or store link asking what's like it, or says "recon", "similar games", "check this idea", "has someone made this", "查竞品", "找类似游戏", "有没有类似的游戏". Trigger even if they don't say "search" — any question about whether a game idea is already taken belongs here.
---

# Game Recon

Find every similar game on both stores so a hybrid-game developer never builds something that already exists. The binding design contract is `docs/superpowers/specs/2026-07-11-game-recon-design.md` in the game-recon repo — its §6 failure table records real misses users caught; never reintroduce them.

Two principles override everything:
1. **Completeness beats tidiness.** A missed competitor costs the user months of wasted development. Never cap, trim, or curate results.
2. **Show results, never advise.** The page contains no verdicts, no "crowded space" warnings, no build/skip suggestions. The user judges; you report.

`$SKILL_DIR` = this skill's directory. Python = `$SKILL_DIR/venv/bin/python` — never system python (PEP 668). Create a fresh workdir in the session scratchpad per run; all files below live there.

## Step 0 — Classify the input (always, before anything else)

- **Apple/Play URL** → Case A. Look the game up; keywords = exact title words.
- **Screenshot** → Case A. Identify the exact game via reverse image search (Google Lens: open images.google.com in the browser, upload the image, read "Exact matches"). If the upload is blocked, ask the user to do it themselves (10 seconds) and paste the top link — or proceed with the identity labeled "unconfirmed candidate". Never assert an identity you didn't verify: an earlier session confidently misidentified a game this way, and the whole report anchored on the wrong keywords.
- **Any text** → ask, always, even when it looks obvious:
  > "Is this a **concept** (find everything in this space) or a **specific game** (find that game + its rivals)?"

  Why always: "arrow drop" is simultaneously a valid concept and an exact game title, and the two cases anchor keywords differently.

## Step 1 — Write config.json

Derive with judgment (this is your creative contribution; the scripts are mechanical):

- `input_words` — Case A: the game title's meaningful words (drop "3D", "Game", punctuation). Case B: the user's own words. Ranking anchors to these exact words, never to your interpretation.
- `synonyms` — the object noun's family (bead → marble, ball, pearl). Studios name the same object differently; this net caught games the literal words missed.
- `mechanics` — action words for the concept family (sort, pull, pop, drop, loop, out, chain, tap). Some games name only actions, never the object.
- `query` — Case A: the exact game name as the store shows it. Case B: the user's phrase verbatim. This becomes the page title.
- `subline` — one neutral factual sentence (what's included, how sections split). No advice.
- `filter_hint` — 2–3 example filter words in curly quotes.
- `pin` — Case A only: the exact game name, so it appears as the first card.

```json
{"query":"Arrow Drop","input_words":["arrow","drop"],
 "synonyms":["marble","bead","ball"],
 "mechanics":["sort","pull","pop","loop","out","chain","tap"],
 "subline":"Every similar game across the App Store and Google Play, nothing capped. Fresh launches follow the time dial; Established = 1M+ downloads.",
 "filter_hint":"“sort”, “pop”","pin":"Arrow Drop",
 "workdir":"<absolute workdir path>"}
```

## Step 2 — Run the search pipeline

```bash
PY=$SKILL_DIR/venv/bin/python
$PY $SKILL_DIR/scripts/search_stores.py      <workdir>/config.json   # ~2–4 min, both stores
$PY $SKILL_DIR/scripts/merge_score.py        <workdir>/config.json   # cross-store merge + tiers
$PY $SKILL_DIR/scripts/fetch_descriptions.py <workdir>/config.json   # judgment set
```

Individual term failures print `skip` and continue — that is by design (unstable VPN); the term list is redundant. Only worry if entire stages fail.

## Step 3 — Mechanic judgment (you, not a regex)

Read `<workdir>/descriptions.json` and judge each game: does its *described mechanic* match the concept family? A shared noun is not a match — "Marble …" titles are frequently Zuma chain-shooters (vocabulary: shoot, aim, chain of balls), a completely different genre; bow/archery and board-game vocabularies are other known impostors. Keep borderline cases — a wrong exclusion is invisible to the user, a wrong inclusion is easy for them to spot. Write the exact `name` strings to reject into `<workdir>/exclusions.json` (JSON array of strings), then:

```bash
$PY $SKILL_DIR/scripts/apply_exclusions.py <workdir>/config.json
$PY $SKILL_DIR/scripts/gen_page.py         <workdir>/config.json    # icons + report.html
```

## Step 4 — Deliver

Publish `<workdir>/report.html` as an Artifact. Favicon: 🎯 for concept input, 📷 for screenshot-origin; keep the same emoji across updates of the same report. Re-running the same concept: republish the same file path so the URL stays stable.

Reply with the link plus 2–3 sentences of plain-language facts (how many games, how many fresh, notable exact matches). Counts only — no advice, no "crowded/open" judgment.

## When the user reports a miss

Diagnose the systematic cause (term generation? gate? merge? scoring?), fix the *class* of miss rather than hand-adding the one game, and record it in the spec's §6 failure table. Every rule in this skill exists because a user caught a real miss; the table is the tool's institutional memory.

## Known limits

US storefront only (CN deferred) · revenue ranking disabled until AppMagic integration · theme subscriptions/notifications deferred · full deferred list in spec §7.
