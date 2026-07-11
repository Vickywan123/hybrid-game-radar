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
