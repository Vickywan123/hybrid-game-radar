# skill/scripts/gen_page.py
"""Render games.json into the approved report page. Spec: design doc §5."""
import base64, html, json, os, ssl, subprocess, sys, tempfile, urllib.request

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
        for g in games:
            if g["name"] == pin:
                g["rel"] = 1000
        games = sorted(games, key=lambda g: 0 if g["name"] == pin else 1)
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
