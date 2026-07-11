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
