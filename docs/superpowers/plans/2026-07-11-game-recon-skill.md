# Game Recon Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the prototype validated in the design session into an installable Claude Code skill (`game-recon`) that searches iOS + Google Play for similar games and produces the approved report page.

**Architecture:** Deterministic work (store search, gating, merging, scoring, page generation) lives in parameterized Python scripts driven by a per-run `config.json`. Judgment work (input-type question, keyword/synonym derivation, description-based mechanic verification, reverse-image identification) is done by Claude at runtime, orchestrated by SKILL.md. Skill source is developed in the `game-recon` git repo under `skill/` and installed to `~/.claude/skills/game-recon/` by `install.sh`.

**Tech Stack:** Python 3 (venv), `google-play-scraper` (only dependency), iTunes Search API, macOS `sips` for icon resizing, Claude Code Artifact for page delivery.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-11-game-recon-design.md` — every rule cited by section number below is normative.
- Python venv lives at `skill/venv/` (PEP 668 — never pip install into system Python).
- No display caps anywhere (§3.6). All request code: 20s timeout, 3 retries, failures skip the term, never abort (§3.5).
- Relevance anchored to user's exact input words, tiered 1000/500+/scored (§3.4).
- Page template = the session-approved `template5.html` (monthly dial, relevance-default sorts, no verdict banner, per-store link badges, date-unknown chip).
- Prototype source of truth (vendored in Task 1, this session's scratchpad):
  `/private/tmp/claude-501/-Users-vickywan-Documents-Claude-Workspace/5348d5c4-19ea-4736-b860-4ee59b274185/scratchpad/`

---

### Task 1: Scaffold, vendor template, create venv

**Files:**
- Create: `skill/assets/template.html` (copy of scratchpad `template5.html`)
- Create: `skill/scripts/` (empty dir), `skill/tests/fixtures/` (empty dir)
- Create: `install.sh`

**Interfaces:**
- Produces: `skill/venv/bin/python` with `google_play_scraper` importable; `skill/assets/template.html` containing placeholders `{{ALL_ROWS}}` and `{{NTOTAL}}`.

- [ ] **Step 1: Create directory layout and vendor the template**

```bash
cd "/Users/vickywan/Documents/Claude Workspace/game-recon"
mkdir -p skill/scripts skill/assets skill/tests/fixtures
cp "/private/tmp/claude-501/-Users-vickywan-Documents-Claude-Workspace/5348d5c4-19ea-4736-b860-4ee59b274185/scratchpad/template5.html" skill/assets/template.html
```

- [ ] **Step 2: Verify the vendored template is the approved version**

Run:
```bash
grep -c 'value="122"' skill/assets/template.html   # monthly dial: 4 months option
grep -c 'class="verdict"' skill/assets/template.html || echo "no-verdict OK"
grep -c "estabSort==='recency'" skill/assets/template.html
```
Expected: `1`, `no-verdict OK` (grep exits 1), `1`.

- [ ] **Step 3: Create the venv with the one dependency**

```bash
python3 -m venv skill/venv
skill/venv/bin/pip install --quiet google-play-scraper
skill/venv/bin/python -c "import google_play_scraper; print('import OK')"
```
Expected: `import OK`.

- [ ] **Step 4: Write install.sh**

```bash
cat > install.sh <<'SH'
#!/bin/bash
# Install/refresh the game-recon skill into ~/.claude/skills
set -e
SRC="$(cd "$(dirname "$0")/skill" && pwd)"
DST="$HOME/.claude/skills/game-recon"
mkdir -p "$DST"
rsync -a --delete --exclude venv "$SRC/" "$DST/"
if [ ! -d "$DST/venv" ]; then
  python3 -m venv "$DST/venv"
  "$DST/venv/bin/pip" install --quiet google-play-scraper
fi
echo "installed to $DST"
SH
chmod +x install.sh
```

- [ ] **Step 5: Commit**

```bash
git add skill/assets/template.html install.sh && git add -A skill/scripts skill/tests 2>/dev/null
printf 'venv/\n' > skill/.gitignore && git add skill/.gitignore
git commit -m "feat: scaffold game-recon skill, vendor approved page template

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Parameterize the template header

**Files:**
- Modify: `skill/assets/template.html` (title/H1/sub-line/filter-placeholder lines)

**Interfaces:**
- Produces: placeholders `{{QUERY}}`, `{{SUBLINE}}`, `{{FILTER_HINT}}` consumed by `gen_page.py` (Task 6). Existing `{{ALL_ROWS}}`/`{{NTOTAL}}` unchanged.

- [ ] **Step 1: Replace the hardcoded concept text with placeholders**

In `skill/assets/template.html` make exactly these three edits:

1. `<title>Game Recon — arrow sand puzzle</title>` → `<title>Game Recon — {{QUERY}}</title>`
2. `<h1>Similar games for <span class="q">arrow sand puzzle</span></h1>` → `<h1>Similar games for <span class="q">{{QUERY}}</span></h1>`
3. The `<div class="sub">…</div>` line (begins `Complete list — every arrow/sand game`) → `<div class="sub">{{SUBLINE}}</div>`
4. In the filter input, `e.g. “sort”, “out”, “voodoo”` → `e.g. {{FILTER_HINT}}`

- [ ] **Step 2: Verify placeholders and absence of stale text**

Run:
```bash
grep -o '{{[A-Z_]*}}' skill/assets/template.html | sort -u
grep -c "arrow sand" skill/assets/template.html || echo "stale text gone"
```
Expected: list contains `{{ALL_ROWS}} {{FILTER_HINT}} {{NTOTAL}} {{QUERY}} {{SUBLINE}}`; second command prints `stale text gone`.

- [ ] **Step 3: Commit**

```bash
git add skill/assets/template.html
git commit -m "feat: parameterize template header for any query

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: search_stores.py — term generation + store search + gates

**Files:**
- Create: `skill/scripts/search_stores.py`
- Test: `skill/tests/test_terms.py`

**Interfaces:**
- Consumes: `config.json` (written by Claude at runtime):
  ```json
  {
    "query": "arrow drop",
    "input_words": ["arrow", "drop"],
    "synonyms": ["marble", "bead", "ball"],
    "mechanics": ["sort", "pull", "pop", "loop", "out", "chain", "tap"],
    "workdir": "/absolute/path/to/run/dir"
  }
  ```
- Produces: `<workdir>/pool.json` — list of records `{name, studio, days, ios:{rating,ratings,url,icon}|null, android:{installs,num,score,url,icon}|null}`; and function `gen_terms(input_words, synonyms, mechanics) -> list[str]` used by tests.

- [ ] **Step 1: Write the failing test for term generation (§3.1: both orders, singles, phrase)**

```python
# skill/tests/test_terms.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from search_stores import gen_terms

def test_gen_terms():
    terms = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"])
    # full phrase
    assert "arrow drop" in terms
    # BOTH word orders of every pair (failure mode #8)
    assert "drop arrow" in terms
    assert "arrow sort" in terms and "sort arrow" in terms
    assert "marble sort" in terms and "sort marble" in terms
    # singles for every input + synonym word (failure mode #16)
    for w in ["arrow", "drop", "marble"]:
        assert w in terms
    # no duplicates
    assert len(terms) == len(set(terms))
    print("test_gen_terms OK")

test_gen_terms()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `skill/venv/bin/python skill/tests/test_terms.py`
Expected: `ModuleNotFoundError: No module named 'search_stores'`

- [ ] **Step 3: Write search_stores.py**

```python
# skill/scripts/search_stores.py
"""Search Apple + Google Play for a concept. Spec: design doc §3.1-3.3, 3.5, 3.6."""
import urllib.request, urllib.parse, ssl, json, re, sys, time
from datetime import date, datetime

CTX = ssl.create_default_context()
OK_APPLE = {"Puzzle", "Casual", "Board", "Strategy"}
BLOCK_APPLE = {"Sports", "Racing"}
OK_GP = ("puzzle", "casual", "board")
BLOCK_GP = ("sports", "racing")
TODAY = date.today()

def gen_terms(input_words, synonyms, mechanics):
    words = list(dict.fromkeys(input_words + synonyms))
    terms = [" ".join(input_words)]                      # full phrase
    for a in words:                                      # pairs, both orders
        for b in list(dict.fromkeys(input_words + mechanics)):
            if a != b:
                terms += [f"{a} {b}", f"{b} {a}"]
    terms += words                                       # singles
    return list(dict.fromkeys(terms))

def get_json(url, tries=3):
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=20, context=CTX) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(2)
    return None                                          # §3.5: skip, never abort

def days_from_iso(iso):
    try:
        y, m, d = map(int, iso[:10].split("-")); return (TODAY - date(y, m, d)).days
    except Exception:
        return None

def days_from_gp(s):
    try:
        return (TODAY - datetime.strptime(s, "%b %d, %Y").date()).days
    except Exception:
        return None

def installs_num(s):
    m = re.search(r"([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m else 0

def title_gate(name, input_words, synonyms, mechanics):
    n = name.lower()
    fam = input_words + synonyms
    if any(w in n for w in fam):
        return True
    return sum(1 for w in mechanics if w in n) >= 2      # gate 3

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    iw, syn, mech = cfg["input_words"], cfg["synonyms"], cfg["mechanics"]
    terms = gen_terms(iw, syn, mech)
    print(f"{len(terms)} search terms")

    pool = {}
    # ---- Apple ----
    for i, t in enumerate(terms):
        limit = 200 if " " not in t else 50
        d = get_json("https://itunes.apple.com/search?term="
                     f"{urllib.parse.quote(t)}&entity=software&limit={limit}&country=us")
        if not d:
            print(f"  apple skip: {t}"); continue
        for r in d.get("results", []):
            if r.get("primaryGenreName") != "Games": continue          # gate 1
            g = set(r.get("genres", []))
            if (g & BLOCK_APPLE) or not (g & OK_APPLE): continue       # gate 2
            if not title_gate(r["trackName"], iw, syn, mech): continue # gate 3
            key = ("a", r["trackId"])
            pool[key] = {
                "name": r["trackName"], "studio": r["artistName"],
                "days": days_from_iso(r.get("releaseDate", "")),
                "ios": {"rating": r.get("averageUserRating", 0) or 0,
                        "ratings": r.get("userRatingCount", 0) or 0,
                        "url": r["trackViewUrl"], "icon": r.get("artworkUrl100")},
                "android": None}
        if i % 10 == 0: print(f"  apple {i}/{len(terms)}")

    # ---- Google Play ----
    from google_play_scraper import app as gp_app, search as gp_search
    seen_gp = set()
    for i, t in enumerate(terms):
        try:
            hits = gp_search(t, lang="en", country="us", n_hits=25)
        except Exception:
            print(f"  gp skip: {t}"); continue
        for r in hits:
            if r["appId"] in seen_gp: continue
            if not title_gate(r["title"], iw, syn, mech): continue
            seen_gp.add(r["appId"])
            try:
                d = gp_app(r["appId"], lang="en", country="us")
            except Exception:
                continue
            genre = (d.get("genre") or "").lower()
            if any(b in genre for b in BLOCK_GP): continue
            if not any(g in genre for g in OK_GP): continue
            pool[("g", r["appId"])] = {
                "name": d["title"], "studio": d["developer"],
                "days": days_from_gp(d.get("released") or ""),
                "ios": None,
                "android": {"installs": d.get("installs", "?"),
                            "num": installs_num(d.get("installs")),
                            "score": d.get("score") or 0,
                            "url": f"https://play.google.com/store/apps/details?id={r['appId']}",
                            "icon": d.get("icon")}}
        if i % 10 == 0: print(f"  gp {i}/{len(terms)}")

    out = list(pool.values())
    dst = f"{cfg['workdir']}/pool.json"
    json.dump(out, open(dst, "w"))
    print(f"pool: {len(out)} records -> {dst}")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run the term test to verify it passes**

Run: `skill/venv/bin/python skill/tests/test_terms.py`
Expected: `test_gen_terms OK`

- [ ] **Step 5: Network smoke test (proves failure modes #3 and #8 stay fixed)**

```bash
mkdir -p /tmp/gr_smoke
cat > /tmp/gr_smoke/config.json <<'EOF'
{"query":"arrow drop","input_words":["arrow","drop"],"synonyms":[],"mechanics":["pop"],"workdir":"/tmp/gr_smoke"}
EOF
skill/venv/bin/python skill/scripts/search_stores.py /tmp/gr_smoke/config.json
skill/venv/bin/python -c "
import json; p=json.load(open('/tmp/gr_smoke/pool.json'))
names=[r['name'].lower() for r in p]
assert any('arrow drop'==n or 'arrow drop'in n for n in names), 'Arrow Drop missing'
assert any(r['android'] for r in p), 'no Play records'
print('smoke OK:', len(p), 'records')"
```
Expected: `smoke OK: <n> records` (n > 20). Requires network; on VPN failure re-run once.

- [ ] **Step 6: Commit**

```bash
git add skill/scripts/search_stores.py skill/tests/test_terms.py
git commit -m "feat: store search with dual-order terms and four gates

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: merge_score.py — cross-store merge + tiered relevance

**Files:**
- Create: `skill/scripts/merge_score.py`
- Test: `skill/tests/test_merge.py`, fixture `skill/tests/fixtures/pool_fixture.json`

**Interfaces:**
- Consumes: `<workdir>/pool.json` (Task 3 shape), `config.json`.
- Produces: `<workdir>/games.json` — pool records plus `reach:int` and `rel:int`; merged per §4.2. Testable helpers: `merge(records) -> list`, `score(records, input_words, synonyms, mechanics) -> None` (mutates).

- [ ] **Step 1: Write the failing test**

```python
# skill/tests/test_merge.py
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from merge_score import merge, score

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "pool_fixture.json")

def test_merge_and_tiers():
    recs = json.load(open(FIX))
    out = merge(recs)
    names = [r["name"] for r in out]
    # subtitle-aware cross-store merge (failure mode #5)
    sand = [r for r in out if "Sand Balls" in r["name"] and "Gravity" not in r["name"]]
    assert len(sand) == 1 and sand[0]["ios"] and sand[0]["android"]
    # different-dev same-noun game NOT merged (safety lock §4.2.3)
    assert any("Gravity Sand Balls" in n for n in names)
    # tiered scoring anchored to input (failure mode #15)
    score(out, ["arrow", "drop"], ["marble"], ["sort", "pop"])
    by = {r["name"]: r["rel"] for r in out}
    assert by["Arrow Drop"] == 1000                      # tier 0
    assert 500 <= by["Drop Arrow Pop"] < 1000            # tier 1
    assert by["Marble Sort! - Color Puzzle"] < 500       # tier 2
    print("test_merge_and_tiers OK")

test_merge_and_tiers()
```

```json
// skill/tests/fixtures/pool_fixture.json
[
 {"name":"Sand Balls - Digger Puzzle","studio":"SayGames LTD","days":900,
  "ios":{"rating":4.6,"ratings":283875,"url":"https://apps.apple.com/x","icon":null},"android":null},
 {"name":"Sand Balls - Puzzle Game","studio":"SayGames Ltd","days":880,
  "ios":null,"android":{"installs":"100,000,000+","num":100000000,"score":4.4,"url":"https://play.google.com/store/apps/details?id=x","icon":null}},
 {"name":"Gravity Sand Balls","studio":"Atta Mohi Ud Din","days":100,
  "ios":{"rating":0,"ratings":0,"url":"https://apps.apple.com/y","icon":null},"android":null},
 {"name":"Arrow Drop","studio":"Larisa Games","days":53,
  "ios":null,"android":{"installs":"1,000+","num":1000,"score":4.4,"url":"https://play.google.com/store/apps/details?id=com.drop.arrow","icon":null}},
 {"name":"Drop Arrow Pop","studio":"Babil Studios","days":51,
  "ios":{"rating":1.0,"ratings":1,"url":"https://apps.apple.com/z","icon":null},"android":null},
 {"name":"Marble Sort! - Color Puzzle","studio":"VOODOO","days":257,
  "ios":null,"android":{"installs":"5,000,000+","num":5000000,"score":4.5,"url":"https://play.google.com/store/apps/details?id=m","icon":null}}
]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `skill/venv/bin/python skill/tests/test_merge.py`
Expected: `ModuleNotFoundError: No module named 'merge_score'`

- [ ] **Step 3: Write merge_score.py**

```python
# skill/scripts/merge_score.py
"""Cross-store merge + tiered relevance. Spec: design doc §3.4, §4."""
import json, re, sys

def na(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def base(name):
    return na(re.split(r"\s*[-:–—|·]\s*", name, maxsplit=1)[0])

def merge(records):
    by_studio = {}
    for r in records:
        by_studio.setdefault(na(r["studio"]), []).append(r)
    gone = set()
    for grp in by_studio.values():
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                if id(a) in gone or id(b) in gone: continue
                an, bn = na(a["name"]), na(b["name"])
                if not (an.startswith(bn) or bn.startswith(an)
                        or (base(a["name"]) and base(a["name"]) == base(b["name"]))):
                    continue
                if a["ios"] and not a["android"] and b["android"] and not b["ios"]:
                    keep, drop = a, b
                elif b["ios"] and not b["android"] and a["android"] and not a["ios"]:
                    keep, drop = b, a
                else:
                    continue                       # safety lock §4.2.3
                keep["android"] = drop["android"]
                if drop["days"] is not None and (keep["days"] is None or drop["days"] < keep["days"]):
                    keep["days"] = drop["days"]
                gone.add(id(drop))
    return [r for r in records if id(r) not in gone]

def reach(r):
    a = r["android"]["num"] if r["android"] else 0
    i = (r["ios"]["ratings"] * 30) if r["ios"] else 0    # reviews ~3% of installs
    return max(a, i)

def score(records, input_words, synonyms, mechanics):
    q = na(" ".join(input_words))
    fam = input_words + synonyms
    for r in records:
        n = r["name"].lower()
        r["reach"] = reach(r)
        if na(r["name"]) == q:
            r["rel"] = 1000                                            # tier 0
        elif all(w in n for w in input_words):
            r["rel"] = 500 + sum(1 for w in mechanics if w in n)       # tier 1
        else:                                                          # tier 2
            r["rel"] = (sum(1 for w in input_words if w in n) * 10
                        + sum(1 for w in fam if w in n) * 3
                        + min(sum(1 for w in mechanics if w in n), 3) * 2)

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    recs = json.load(open(f"{cfg['workdir']}/pool.json"))
    out = merge(recs)
    score(out, cfg["input_words"], cfg["synonyms"], cfg["mechanics"])
    json.dump(out, open(f"{cfg['workdir']}/games.json", "w"))
    print(f"merged: {len(recs)} -> {len(out)} games")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `skill/venv/bin/python skill/tests/test_merge.py`
Expected: `test_merge_and_tiers OK`

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/merge_score.py skill/tests/test_merge.py skill/tests/fixtures/pool_fixture.json
git commit -m "feat: cross-store merge and tiered relevance scoring

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: descriptions round-trip for Claude's mechanic judgment

**Files:**
- Create: `skill/scripts/fetch_descriptions.py`
- Create: `skill/scripts/apply_exclusions.py`
- Test: `skill/tests/test_exclusions.py`

**Interfaces:**
- Consumes: `<workdir>/games.json`.
- Produces: `fetch_descriptions.py` writes `<workdir>/descriptions.json` = `[{name, studio, desc}]` for every game with `reach >= 1_000_000` plus the 40 highest-`rel` others — the set Claude reads and judges (§3.3 gate 4). Claude then writes `<workdir>/exclusions.json` = `["exact name", ...]`; `apply_exclusions.py` filters `games.json` in place and prints what it removed.

- [ ] **Step 1: Write the failing test for apply_exclusions**

```python
# skill/tests/test_exclusions.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from apply_exclusions import apply

def test_apply():
    games = [{"name": "Arrow Drop"}, {"name": "Marble Woka Woka: Jungle Blast"}]
    with tempfile.TemporaryDirectory() as d:
        json.dump(games, open(f"{d}/games.json", "w"))
        json.dump(["Marble Woka Woka: Jungle Blast"], open(f"{d}/exclusions.json", "w"))
        removed = apply(d)
        left = json.load(open(f"{d}/games.json"))
    assert removed == 1 and len(left) == 1 and left[0]["name"] == "Arrow Drop"
    print("test_apply OK")

test_apply()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `skill/venv/bin/python skill/tests/test_exclusions.py`
Expected: `ModuleNotFoundError: No module named 'apply_exclusions'`

- [ ] **Step 3: Write both scripts**

```python
# skill/scripts/fetch_descriptions.py
"""Dump store descriptions for the judgment set (spec §3.3 gate 4)."""
import json, re, ssl, sys, time, urllib.request

CTX = ssl.create_default_context()

def apple_desc(url):
    m = re.search(r"/id(\d+)", url or "")
    if not m: return ""
    for _ in range(3):
        try:
            with urllib.request.urlopen(
                    f"https://itunes.apple.com/lookup?id={m.group(1)}&country=us",
                    timeout=20, context=CTX) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            return (d["results"][0].get("description") or "") if d["resultCount"] else ""
        except Exception:
            time.sleep(2)
    return ""

def play_desc(url):
    from google_play_scraper import app as gp_app
    m = re.search(r"id=([\w.]+)", url or "")
    if not m: return ""
    try:
        return gp_app(m.group(1), lang="en", country="us").get("description") or ""
    except Exception:
        return ""

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    games = json.load(open(f"{cfg['workdir']}/games.json"))
    big = [g for g in games if g.get("reach", 0) >= 1_000_000]
    rest = sorted((g for g in games if g not in big), key=lambda g: -g.get("rel", 0))[:40]
    out = []
    for g in big + rest:
        desc = (apple_desc(g["ios"]["url"]) if g.get("ios")
                else play_desc(g["android"]["url"]) if g.get("android") else "")
        out.append({"name": g["name"], "studio": g["studio"], "desc": desc[:600]})
    json.dump(out, open(f"{cfg['workdir']}/descriptions.json", "w"))
    print(f"descriptions: {len(out)} games -> descriptions.json")

if __name__ == "__main__":
    main(sys.argv[1])
```

```python
# skill/scripts/apply_exclusions.py
"""Remove Claude-judged wrong-mechanic games from games.json."""
import json, sys

def apply(workdir):
    games = json.load(open(f"{workdir}/games.json"))
    excl = set(json.load(open(f"{workdir}/exclusions.json")))
    keep = [g for g in games if g["name"] not in excl]
    removed = len(games) - len(keep)
    json.dump(keep, open(f"{workdir}/games.json", "w"))
    for n in sorted(excl):
        print(f"  excluded: {n}")
    print(f"removed {removed}; {len(keep)} remain")
    return removed

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    apply(cfg["workdir"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `skill/venv/bin/python skill/tests/test_exclusions.py`
Expected: `test_apply OK`

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/fetch_descriptions.py skill/scripts/apply_exclusions.py skill/tests/test_exclusions.py
git commit -m "feat: description round-trip for mechanic judgment

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: gen_page.py — icons + cards + template render

**Files:**
- Create: `skill/scripts/gen_page.py`
- Test: `skill/tests/test_page.py`

**Interfaces:**
- Consumes: `<workdir>/games.json`, `skill/assets/template.html`, config keys `query`, `subline`, `filter_hint`, optional `pin` (exact name to place first).
- Produces: `<workdir>/report.html`. Testable helper: `render(games, template_str, query, subline, filter_hint, pin=None) -> str` (no network, icons already in records as `iconData`).

- [ ] **Step 1: Write the failing test**

```python
# skill/tests/test_page.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from gen_page import render

TPL = open(os.path.join(os.path.dirname(__file__), "..", "assets", "template.html")).read()

def test_render():
    games = [
        {"name": "Arrow Drop", "studio": "Larisa Games", "days": 53, "reach": 1000, "rel": 1000,
         "ios": None, "iconData": "",
         "android": {"installs": "1,000+", "num": 1000, "score": 4.4, "url": "https://play.google.com/x", "icon": None}},
        {"name": "Old Nameless", "studio": "S", "days": None, "reach": 0, "rel": 0,
         "ios": {"rating": 0, "ratings": 0, "url": "https://apps.apple.com/x", "icon": None},
         "android": None, "iconData": ""},
    ]
    h = render(games, TPL, "arrow drop", "sub line here", "“drop”")
    assert "{{" not in h                                  # no leftover placeholders
    assert h.count('class="card"') == 2
    assert "date unknown" in h                            # failure mode #14
    assert 'href="https://play.google.com/x"' in h        # per-store link badge
    assert "arrow drop" in h and "sub line here" in h
    # pin: pinned game must be the first card
    h2 = render(list(reversed(games)), TPL, "arrow drop", "s", "x", pin="Arrow Drop")
    assert h2.find("Arrow Drop") < h2.find("Old Nameless")
    print("test_render OK")

test_render()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `skill/venv/bin/python skill/tests/test_page.py`
Expected: `ModuleNotFoundError: No module named 'gen_page'`

- [ ] **Step 3: Write gen_page.py**

```python
# skill/scripts/gen_page.py
"""Render games.json into the approved report page. Spec: design doc §5."""
import base64, html, json, os, re, ssl, subprocess, sys, tempfile, time, urllib.request

CTX = ssl.create_default_context()

def esc(s):
    return html.escape(str(s))

def fetch_icon_64(url):
    """Download an icon and shrink to 64px JPEG (macOS sips). Empty string on failure."""
    if not url: return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            raw = r.read()
        with tempfile.TemporaryDirectory() as d:
            src, dst = f"{d}/i.bin", f"{d}/o.jpg"
            open(src, "wb").write(raw)
            p = subprocess.run(["sips", "-Z", "64", "-s", "format", "jpeg",
                                "-s", "formatOptions", "70", src, "--out", dst],
                               capture_output=True)
            if p.returncode == 0:
                return "data:image/jpeg;base64," + base64.b64encode(open(dst, "rb").read()).decode()
    except Exception:
        pass
    return ""

def badges(r):
    b = ""
    if r["days"] is not None:
        cls = "hot" if r["days"] <= 21 else "warn"
        b += f'<span class="badge age {cls}">◷ {r["days"]}d ago</span>'
    else:
        b += '<span class="badge unk">◷ date unknown</span>'
    if r.get("ios"):
        b += f'<a class="badge store ios" href="{esc(r["ios"]["url"])}" target="_blank" rel="noopener">iOS ↗</a>'
    if r.get("android"):
        b += f'<a class="badge store and" href="{esc(r["android"]["url"])}" target="_blank" rel="noopener">Play ↗</a>'
    return b

def num_line(r):
    parts = []
    if r.get("android"):
        parts.append(f'<span class="badge dl">▼ {esc(r["android"]["installs"])}</span>')
    if r.get("ios"):
        if r["ios"]["ratings"]:
            parts.append(f'<span class="badge ap">★ {r["ios"]["rating"]:.1f} · {r["ios"]["ratings"]:,}</span>')
        else:
            parts.append('<span class="badge ap muted">no ratings yet</span>')
    return "".join(parts)

def card(r):
    days = "" if r["days"] is None else str(r["days"])
    return (f'<div class="card" data-days="{days}" data-reach="{r.get("reach",0)}" '
            f'data-rel="{r.get("rel",0)}">'
            f'<img class="icon" src="{r.get("iconData","")}" alt="" loading="lazy" width="64" height="64">'
            f'<div class="body"><div class="name">{esc(r["name"])}</div>'
            f'<div class="studio">{esc(r["studio"])}</div>'
            f'<div class="reach">{badges(r)}</div>'
            f'<div class="reach">{num_line(r)}</div></div></div>')

def render(games, template_str, query, subline, filter_hint, pin=None):
    if pin:
        games = sorted(games, key=lambda g: 0 if g["name"] == pin else 1)
        for g in games:
            if g["name"] == pin:
                g = dict(g); g["rel"] = 1000
    rows = "\n".join(card(g) for g in games)
    return (template_str
            .replace("{{ALL_ROWS}}", rows)
            .replace("{{NTOTAL}}", str(len(games)))
            .replace("{{QUERY}}", esc(query))
            .replace("{{SUBLINE}}", esc(subline))
            .replace("{{FILTER_HINT}}", esc(filter_hint)))

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    wd = cfg["workdir"]
    games = json.load(open(f"{wd}/games.json"))
    for i, g in enumerate(games):
        if not g.get("iconData"):
            src = (g.get("ios") or {}).get("icon") or (g.get("android") or {}).get("icon")
            g["iconData"] = fetch_icon_64(src)
        if i % 25 == 0: print(f"  icons {i}/{len(games)}")
    tpl = open(os.path.join(os.path.dirname(__file__), "..", "assets", "template.html")).read()
    out = render(games, tpl, cfg["query"], cfg.get("subline", ""),
                 cfg.get("filter_hint", "“sort”"), cfg.get("pin"))
    open(f"{wd}/report.html", "w").write(out)
    print(f"report: {wd}/report.html ({len(out)//1024} KB, {len(games)} cards)")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `skill/venv/bin/python skill/tests/test_page.py`
Expected: `test_render OK`

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/gen_page.py skill/tests/test_page.py
git commit -m "feat: report page renderer with pin and date-unknown chip

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: SKILL.md — the runbook

**Files:**
- Create: `skill/SKILL.md`

**Interfaces:**
- Consumes: all scripts above via `$SKILL_DIR/venv/bin/python $SKILL_DIR/scripts/<script>.py <workdir>/config.json`.
- Produces: the complete skill instruction file.

- [ ] **Step 1: Write SKILL.md with exactly this content**

````markdown
---
name: game-recon
description: Search iOS + Google Play for games similar to a concept, game name, store link, or screenshot, and produce a visual competitive-landscape report page. Use when a game developer asks "has someone built this?", wants similar-game recon, competitor check for a hybrid game idea, or shares a game screenshot/link asking for lookalikes. Triggers: "recon", "similar games", "check this idea", "查竞品", "有没有类似的游戏".
---

# Game Recon

Produce a complete, nothing-missed report of similar games across the App Store and Google Play. The design contract lives in `docs/superpowers/specs/2026-07-11-game-recon-design.md` of the game-recon repo; its §6 failure table is binding. **The page shows results only — never add verdicts or build/skip advice.**

`$SKILL_DIR` below = this skill's directory. Python = `$SKILL_DIR/venv/bin/python` (never system python). Create a fresh workdir per run in the session scratchpad; write `config.json` there.

## Step 0 — Classify the input (ALWAYS)

- Apple/Play **URL** → Case A. Look the game up; keywords = exact title words.
- **Screenshot** → Case A. Identify via reverse image search (Google Lens in the browser: images.google.com, upload). If blocked, ask the user to upload it to Google Images themselves and paste the top result link — or proceed labeling the identity "unconfirmed candidate". NEVER assert an unverified identity.
- **Any text** → ASK, always, even if it looks obvious:
  > "Is this a **concept** (find everything in this space) or a **specific game** (find that game + its rivals)?"

## Step 1 — Build config.json

Derive, using judgment:
- `input_words`: Case A = the game title's meaningful words (drop "3D", "Game", punctuation). Case B = the user's words.
- `synonyms`: family of the object noun (bead → marble, ball, pearl). Case B especially; Case A still include as secondary net.
- `mechanics`: action words for this concept family (sort, pull, pop, drop, loop, out, chain, tap ...).
- `query`: Case A = the exact game name as the store shows it; Case B = the user's phrase verbatim.
- `subline`: one neutral factual sentence (what's included; Fresh = time dial, Established = 1M+). No advice.
- `filter_hint`: 2–3 example filter words with curly quotes.
- `pin` (Case A only): the exact game name.

```json
{"query":"Arrow Drop","input_words":["arrow","drop"],
 "synonyms":["marble","bead","ball"],
 "mechanics":["sort","pull","pop","loop","out","chain","tap"],
 "subline":"Every similar game across the App Store and Google Play, nothing capped. Fresh launches follow the time dial; Established = 1M+ downloads.",
 "filter_hint":"“sort”, “pop”","pin":"Arrow Drop",
 "workdir":"<abs workdir>"}
```

## Step 2 — Run the pipeline

```bash
PY=$SKILL_DIR/venv/bin/python
$PY $SKILL_DIR/scripts/search_stores.py  <workdir>/config.json   # ~2-4 min
$PY $SKILL_DIR/scripts/merge_score.py    <workdir>/config.json
$PY $SKILL_DIR/scripts/fetch_descriptions.py <workdir>/config.json
```

## Step 3 — Mechanic judgment (YOU, not a regex)

Read `<workdir>/descriptions.json`. For each game decide: does its described mechanic match the concept family? Reject wrong-world genres wearing the same noun (Zuma/marble-shooter vocabulary: shoot, aim, chain of balls; bow/archery; board/mancala). Keep borderline cases. Write the exact `name` strings to reject into `<workdir>/exclusions.json` (JSON array), then:

```bash
$PY $SKILL_DIR/scripts/apply_exclusions.py <workdir>/config.json
$PY $SKILL_DIR/scripts/gen_page.py         <workdir>/config.json
```

## Step 4 — Deliver

Publish `<workdir>/report.html` as an Artifact (favicon 🎯 concept / 📷 screenshot-origin; keep the same emoji when updating the same report). Reply with the link + 2-3 sentences of what's on the page (counts only, no advice). Same concept re-run → republish the same file path to keep the URL.

## Standing rule

User reports a missed or wrong game → diagnose the systematic cause → fix the class (term generation / gates / merge / scoring), not the single game → record it in the spec's §6 table.

## Known limits

US storefront only (CN deferred) · revenue sort disabled until AppMagic integration · subscriptions/notifications deferred — see spec §7.
````

- [ ] **Step 2: Verify frontmatter and completeness**

Run:
```bash
head -5 skill/SKILL.md | grep -c "name: game-recon"
grep -c "Step 0" skill/SKILL.md
grep -c "exclusions.json" skill/SKILL.md
```
Expected: `1`, `1`, `2` (or more).

- [ ] **Step 3: Commit**

```bash
git add skill/SKILL.md
git commit -m "feat: game-recon skill runbook

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Install + end-to-end smoke test

**Files:**
- Modify: none (runs `install.sh`, exercises the installed skill's scripts end to end)

**Interfaces:**
- Consumes: everything above.
- Produces: installed skill at `~/.claude/skills/game-recon/`; a real `report.html` for input "arrow drop" (Case A).

- [ ] **Step 1: Install**

Run: `./install.sh`
Expected: `installed to /Users/vickywan/.claude/skills/game-recon` and venv creation output on first run.

- [ ] **Step 2: Full pipeline run against the known case**

```bash
DST=~/.claude/skills/game-recon
mkdir -p /tmp/gr_e2e
cat > /tmp/gr_e2e/config.json <<'EOF'
{"query":"Arrow Drop","input_words":["arrow","drop"],
 "synonyms":["marble","bead"],
 "mechanics":["sort","pull","pop","loop","out","tap"],
 "subline":"Every similar game across the App Store and Google Play, nothing capped.",
 "filter_hint":"“sort”, “pop”","pin":"Arrow Drop","workdir":"/tmp/gr_e2e"}
EOF
$DST/venv/bin/python $DST/scripts/search_stores.py /tmp/gr_e2e/config.json
$DST/venv/bin/python $DST/scripts/merge_score.py /tmp/gr_e2e/config.json
$DST/venv/bin/python $DST/scripts/fetch_descriptions.py /tmp/gr_e2e/config.json
echo '[]' > /tmp/gr_e2e/exclusions.json
$DST/venv/bin/python $DST/scripts/apply_exclusions.py /tmp/gr_e2e/config.json
$DST/venv/bin/python $DST/scripts/gen_page.py /tmp/gr_e2e/config.json
```
Expected: each stage prints its summary; final line `report: /tmp/gr_e2e/report.html (...)`.

- [ ] **Step 3: Assert the report matches the spec's acid tests**

```bash
$DST/venv/bin/python - <<'PY'
h = open('/tmp/gr_e2e/report.html').read()
assert "{{" not in h, "unfilled placeholder"
assert h.count('class="card"') >= 50, "suspiciously few games"
assert "Arrow Drop" in h, "exact game missing (failure modes 8/15)"
first = h.find('class="card"'); assert "Arrow Drop" in h[first:first+900], "pin not first"
assert "date unknown" in h or "d ago" in h
print("E2E OK:", h.count('class="card"'), "cards")
PY
```
Expected: `E2E OK: <n> cards`.

- [ ] **Step 4: Commit any fixes, tag done**

```bash
git add -A && git commit -m "chore: e2e smoke verified against Arrow Drop case

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || echo "nothing to commit"
```

---

## Self-review notes

- **Spec coverage:** §2 input rules → Task 7 (SKILL.md Step 0); §3.1–3.3 → Task 3; §3.4 + §4 → Task 4; §3.3 gate 4 → Tasks 5 + 7 (Step 3); §5 → Tasks 2 + 6 (template itself vendored, already approved); §6 acid cases → tests in Tasks 3/4/6/8; §7 deferred — intentionally no tasks.
- **Reverse image search (§2)** is a runtime judgment flow in SKILL.md, not a script — Google gates uploads; automation is best-effort by Claude in the browser with the documented user fallback.
- **Type consistency:** record shape `{name, studio, days, ios, android, reach, rel, iconData}` is identical across Tasks 3→6; config keys consistent across all scripts.
