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
    # future-dated game: "upcoming" badge, sorts as day 0 (never negative)
    fut = [{"name": "Future Game", "studio": "S", "days": -52, "reach": 0, "rel": 0,
            "ios": {"rating": 0, "ratings": 0, "url": "https://apps.apple.com/f", "icon": None},
            "android": None, "iconData": ""}]
    h3 = render(fut, TPL, "q", "s", "x")
    assert "upcoming" in h3 and 'data-days="0"' in h3 and "-52" not in h3
    # hover screenshots: panel present only when shots exist
    sh = [dict(games[0])]; sh[0]["shotsData"] = ["data:image/jpeg;base64,AAA", "data:image/jpeg;base64,BBB"]
    h4 = render(sh, TPL, "q", "s", "x")
    assert 'class="shots"' in h4 and h4.count('class="shot"') == 2
    h5 = render([games[1]], TPL, "q", "s", "x")
    assert 'class="shots"' not in h5
    # hovered card must rise above siblings or the shots panel is covered
    assert "z-index:30" in TPL.split(".card:hover{")[1][:120]
    print("test_render OK")

test_render()
