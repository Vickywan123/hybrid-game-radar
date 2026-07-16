# skill/scripts/search_stores.py
"""Search Apple + Google Play for a concept. Spec: design doc §3.1-3.3, 3.5, 3.6.
The post-judgment snowball wave lives in snowball.py (spec failure #17)."""
import urllib.request, urllib.parse, ssl, json, re, sys, time
import concurrent.futures, hashlib, os, random
from collections import Counter
from datetime import date, datetime

CTX = ssl.create_default_context()
OK_APPLE = {"Puzzle", "Casual", "Board", "Strategy"}
BLOCK_APPLE = {"Sports", "Racing"}
OK_GP = ("puzzle", "casual", "board")
BLOCK_GP = ("sports", "racing")
TODAY = date.today()

# --- cache: search results live 1 day, per-game details 7 days ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
TTL = {"apple_search": 86400, "gp_search": 86400, "gp_app": 7 * 86400}

def cache_get(kind, key):
    try:
        p = os.path.join(CACHE_DIR, f"{kind}_{hashlib.md5(key.encode()).hexdigest()}.json")
        d = json.load(open(p))
        if time.time() - d["ts"] <= TTL[kind]:
            return d["data"]
    except Exception:
        pass
    return None

def cache_put(kind, key, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        p = os.path.join(CACHE_DIR, f"{kind}_{hashlib.md5(key.encode()).hexdigest()}.json")
        json.dump({"ts": time.time(), "data": data}, open(p, "w"))
    except Exception:
        pass

def gen_terms(input_words, synonyms, mechanics, depth="precise"):
    """depth: precise = user's words only; standard = + mechanic combos;
    full = + synonym family. Both word orders always (store search is
    order-sensitive — spec failure #8)."""
    iw = list(dict.fromkeys(input_words))
    terms = [" ".join(iw)]                               # full phrase
    for a in iw:                                         # input pairs, both orders
        for b in iw:
            if a != b:
                terms.append(f"{a} {b}")
    terms += iw                                          # singles
    if depth in ("standard", "full"):
        for a in iw:                                     # + mechanic combos
            for m in mechanics:
                terms += [f"{a} {m}", f"{m} {a}"]
    if depth == "full":
        for s in synonyms:                               # + synonym family
            terms.append(s)
            for b in list(dict.fromkeys(iw + mechanics)):
                terms += [f"{s} {b}", f"{b} {s}"]
    return list(dict.fromkeys(terms))

# --- snowball vocabulary mining (spec failure #17: same mechanic, zero
# shared title words — "Pixel Flow!" vs "This is Blast!"). Mining must use
# MECHANIC-VERIFIED titles only: mining the raw pool surfaces the loudest
# impostor genres instead (measured: bubble/ball/marble from the blast pool). ---
STOP = {"game", "games", "puzzle", "puzzles", "free", "new", "best", "fun",
        "master", "mania", "legend", "saga", "classic", "pro", "super",
        "plus", "king", "big", "little", "the", "and", "for", "with", "your",
        "of", "my", "in", "out", "up", "go", "no", "is", "it", "this",
        "2d", "3d", "offline", "online", "adventure", "challenge", "brain",
        "epic", "ultimate", "crazy", "happy", "world", "story", "journey",
        "color", "colors", "colorful", "away", "craze", "crush", "rescue",
        "match", "matching", "relax", "relaxing", "cozy", "satisfying",
        "asmr", "art", "hero", "jam", "blast", "pop", "sort", "sorting",
        "block", "blocks", "escape", "room", "rooms", "wood", "wooden",
        "woody", "tap", "drop", "jewel", "gem", "cube", "slide", "maze"}

def _is_known(w, known):
    """Word variants count as known: 'sorting'~'sort', 'colors'~'color'."""
    if w in known:
        return True
    return any((len(k) >= 4 and w.startswith(k)) or (len(w) >= 4 and k.startswith(w))
               for k in known)

def mine_new_words(verified_names, known_words, top_n=5, with_counts=False):
    """Extract the most frequent unknown words from mechanic-verified titles."""
    known = {w.lower() for w in known_words} | STOP
    counts = Counter()
    for name in verified_names:
        for w in re.findall(r"[a-z]{3,}", name.lower()):
            if not _is_known(w, known):
                counts[w] += 1
    top = counts.most_common(top_n)
    return top if with_counts else [w for w, _ in top]

def snowball_terms(verified_names, input_words, known_words, max_terms=20):
    """Build wave-2 terms from words mined out of verified titles:
    mined singles + mined pairs + mined×input combos, both orders."""
    iw = [w.lower() for w in input_words]
    mined_counts = mine_new_words(verified_names, list(known_words) + iw, with_counts=True)
    mined = [w for w, _ in mined_counts]
    terms = []
    for a, c in mined_counts:
        # a mined word searched ALONE drags in whole genres ("find" -> hidden
        # object, "logic" -> logic grids: failure #24). Singles need strong
        # family evidence (>=3 verified titles); combos below are always safe.
        if c >= 3:
            terms.append(a)
    for a in mined:                                      # mined × input combos
        for w in iw:
            terms += [f"{a} {w}", f"{w} {a}"]
    for i, a in enumerate(mined):                        # mined pairs, both orders
        for b in mined[i + 1:]:
            terms += [f"{a} {b}", f"{b} {a}"]
    return mined, list(dict.fromkeys(terms))[:max_terms]

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

def title_gate(name, fam, mechanics):
    n = name.lower()
    if any(w in n for w in fam):
        return True
    return sum(1 for w in mechanics if w in n) >= 2      # gate 3

def apple_fetch(t):
    # genreId=6014 = Apple's "Games" umbrella (covers Puzzle AND Casual sub-tags):
    # server-side filtering means all 200 result slots go to actual games
    # instead of being wasted on wallpaper/tool apps. Never filter to the
    # Puzzle sub-genre (7012) — many hybrid games are tagged Casual.
    cached = cache_get("apple_search", "g6014:" + t)
    if cached is not None:
        return t, cached
    limit = 200 if " " not in t else 50
    d = get_json("https://itunes.apple.com/search?term="
                 f"{urllib.parse.quote(t)}&entity=software&limit={limit}&country=us&genreId=6014")
    results = d.get("results", []) if d else None
    if results is not None:
        cache_put("apple_search", "g6014:" + t, results)
    return t, results

def run_sweep(pool, terms, fam, mech, platforms, label, gp_detail_cap=None):
    """Sweep both stores for `terms`, adding gate-passing games to `pool`
    (dict keyed by (store, id)). Reused by search_stores and snowball."""
    # ---- Apple: cached + parallel (Apple tolerates concurrency) ----
    if platforms in ("both", "ios"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(apple_fetch, terms))
        for t, rs in results:
            if rs is None:
                print(f"  apple skip: {t}"); continue
            for r in rs:
                if r.get("primaryGenreName") != "Games": continue          # gate 1
                g = set(r.get("genres", []))
                if (g & BLOCK_APPLE) or not (g & OK_APPLE): continue       # gate 2
                if not title_gate(r["trackName"], fam, mech): continue     # gate 3
                pool[("a", r["trackId"])] = {
                    "name": r["trackName"], "studio": r["artistName"],
                    "days": days_from_iso(r.get("releaseDate", "")),
                    "ios": {"rating": r.get("averageUserRating", 0) or 0,
                            "ratings": r.get("userRatingCount", 0) or 0,
                            "url": r["trackViewUrl"], "icon": r.get("artworkUrl100"),
                            "shots": (r.get("screenshotUrls") or [])[:4]},
                    "android": None}
        print(f"  {label} apple done: {len(terms)} terms")
    # ---- Google Play: searches serial, detail fetches gently parallel (x3, jittered) ----
    if platforms in ("both", "android"):
        from google_play_scraper import app as gp_app, search as gp_search
        cand = {}
        for i, t in enumerate(terms):
            hits = cache_get("gp_search", t)
            if hits is None:
                try:
                    hits = gp_search(t, lang="en", country="us", n_hits=25)
                    cache_put("gp_search", t, hits)
                except Exception:
                    print(f"  gp skip: {t}"); continue
            for r in hits:
                if r["appId"] in cand or ("g", r["appId"]) in pool: continue
                if not title_gate(r["title"], fam, mech): continue
                cand[r["appId"]] = True
        ids = list(cand)
        if gp_detail_cap is not None:
            ids = ids[:gp_detail_cap]
        def fetch_detail(aid):
            d = cache_get("gp_app", aid)
            if d is None:
                try:
                    time.sleep(random.uniform(0.05, 0.3))
                    d = gp_app(aid, lang="en", country="us")
                    cache_put("gp_app", aid, d)
                except Exception:
                    return None
            return aid, d
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            results = list(ex.map(fetch_detail, ids))
        for res in results:
            if not res: continue
            aid, d = res
            genre = (d.get("genre") or "").lower()
            if any(b in genre for b in BLOCK_GP): continue
            if not any(g in genre for g in OK_GP): continue
            pool[("g", aid)] = {
                "name": d["title"], "studio": d["developer"],
                "days": days_from_gp(d.get("released") or ""),
                "ios": None,
                "android": {"installs": d.get("installs", "?"),
                            "num": installs_num(d.get("installs")),
                            "score": d.get("score") or 0,
                            "url": f"https://play.google.com/store/apps/details?id={aid}",
                            "icon": d.get("icon"),
                            "shots": (d.get("screenshots") or [])[:4]}}
        print(f"  {label} gp done: {len(ids)} details")

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    iw, syn, mech = cfg["input_words"], cfg["synonyms"], cfg["mechanics"]
    platforms = cfg.get("platforms", "both")             # both | ios | android
    pool = {}
    terms = gen_terms(iw, syn, mech, cfg.get("depth", "precise"))
    fam = [w.lower() for w in iw + syn]
    print(f"wave 1: {len(terms)} terms")
    run_sweep(pool, terms, fam, mech, platforms, "w1")
    out = list(pool.values())
    dst = f"{cfg['workdir']}/pool.json"
    json.dump(out, open(dst, "w"))
    print(f"pool: {len(out)} records -> {dst}")

if __name__ == "__main__":
    main(sys.argv[1])
