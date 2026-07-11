# skill/scripts/fetch_descriptions.py
"""Dump store descriptions for the judgment set (spec §3.3 gate 4).
Fast path: Google Play descriptions come from the gp_app cache (already
fetched during search); Apple descriptions via batched lookup (100 ids
per request). Per-game network fetches happen only as a fallback."""
import json, re, ssl, sys, time, urllib.request

CTX = ssl.create_default_context()

def batch_apple_descs(ids):
    out = {}
    for i in range(0, len(ids), 100):
        chunk = ",".join(ids[i:i + 100])
        for _ in range(3):
            try:
                with urllib.request.urlopen(
                        f"https://itunes.apple.com/lookup?id={chunk}&country=us",
                        timeout=25, context=CTX) as r:
                    d = json.loads(r.read().decode("utf-8", "replace"))
                for x in d.get("results", []):
                    out[str(x["trackId"])] = x.get("description") or ""
                break
            except Exception:
                time.sleep(2)
    return out

def main(cfg_path):
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from search_stores import cache_get
    cfg = json.load(open(cfg_path))
    games = json.load(open(f"{cfg['workdir']}/games.json"))
    big = [g for g in games if g.get("reach", 0) >= 1_000_000]
    rest = sorted((g for g in games if g not in big), key=lambda g: -g.get("rel", 0))[:40]
    picked = big + rest

    apple_ids = []
    for g in picked:
        if g.get("ios"):
            m = re.search(r"/id(\d+)", g["ios"]["url"] or "")
            if m: apple_ids.append(m.group(1))
    apple_descs = batch_apple_descs(apple_ids)

    out = []
    for g in picked:
        desc = ""
        if g.get("ios"):
            m = re.search(r"/id(\d+)", g["ios"]["url"] or "")
            if m: desc = apple_descs.get(m.group(1), "")
        if not desc and g.get("android"):
            m = re.search(r"id=([\w.]+)", g["android"]["url"] or "")
            if m:
                d = cache_get("gp_app", m.group(1))
                if d: desc = d.get("description") or ""
        out.append({"name": g["name"], "studio": g["studio"], "desc": desc[:600]})
    json.dump(out, open(f"{cfg['workdir']}/descriptions.json", "w"))
    print(f"descriptions: {len(out)} games -> descriptions.json (batched+cached)")

if __name__ == "__main__":
    main(sys.argv[1])
