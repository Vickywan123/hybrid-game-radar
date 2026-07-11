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
