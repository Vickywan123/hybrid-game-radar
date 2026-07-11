# skill/scripts/search_stores.py
"""Search Apple + Google Play for a concept. Spec: design doc §3.1-3.3, 3.5, 3.6."""
import urllib.request, urllib.parse, ssl, json, re, sys, time
import concurrent.futures, hashlib, os
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
    terms = gen_terms(iw, syn, mech, cfg.get("depth", "precise"))
    print(f"{len(terms)} search terms")

    pool = {}
    platforms = cfg.get("platforms", "both")   # both | ios | android

    # ---- Apple: cached + parallel (Apple tolerates concurrency; Play does not) ----
    def apple_fetch(t):
        cached = cache_get("apple_search", t)
        if cached is not None:
            return t, cached
        limit = 200 if " " not in t else 50
        d = get_json("https://itunes.apple.com/search?term="
                     f"{urllib.parse.quote(t)}&entity=software&limit={limit}&country=us")
        results = d.get("results", []) if d else None
        if results is not None:
            cache_put("apple_search", t, results)
        return t, results

    apple_results = []
    if platforms in ("both", "ios"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            apple_results = list(ex.map(apple_fetch, terms))
    for t, results in apple_results:
        if results is None:
            print(f"  apple skip: {t}"); continue
        for r in results:
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
    if apple_results:
        print(f"  apple done: {len(terms)} terms")

    # ---- Google Play: cached, serial (parallel gets IP-blocked) ----
    from google_play_scraper import app as gp_app, search as gp_search
    seen_gp = set()
    gp_terms = terms if platforms in ("both", "android") else []
    for i, t in enumerate(gp_terms):
        hits = cache_get("gp_search", t)
        if hits is None:
            try:
                hits = gp_search(t, lang="en", country="us", n_hits=25)
                cache_put("gp_search", t, hits)
            except Exception:
                print(f"  gp skip: {t}"); continue
        for r in hits:
            if r["appId"] in seen_gp: continue
            if not title_gate(r["title"], iw, syn, mech): continue
            seen_gp.add(r["appId"])
            d = cache_get("gp_app", r["appId"])
            if d is None:
                try:
                    d = gp_app(r["appId"], lang="en", country="us")
                    cache_put("gp_app", r["appId"], d)
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
        if i % 10 == 0: print(f"  gp {i}/{len(gp_terms)}")

    out = list(pool.values())
    dst = f"{cfg['workdir']}/pool.json"
    json.dump(out, open(dst, "w"))
    print(f"pool: {len(out)} records -> {dst}")

if __name__ == "__main__":
    main(sys.argv[1])
