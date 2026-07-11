import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from search_stores import mine_new_words, snowball_terms

def test_pixel_flow_class():
    """Spec failure #17: 'Pixel Flow!' shares zero words with 'This is Blast!'.
    Mining MECHANIC-VERIFIED titles must surface the family's real vocabulary
    (pixel), not the loud impostor genres (bubble/marble)."""
    verified = [
        "This is Blast!",
        "Color Blast: Block Shooter",
        "Color Blast Shooter",
        "Block Loop Shooter",
        "Pixel Blast - Color Shooter",
        "Pixel Blast: Color Shooter",
        "Bounce Blast",
        "HexaBlast Puzzle - Sort Colors",
    ]
    known = ["blast", "block", "cube", "toy", "brick",
             "pop", "shoot", "match", "color", "jam", "crush", "puzzle"]
    mined, terms = snowball_terms(verified, ["blast"], known)
    assert "pixel" in mined, f"mined={mined}"
    assert "pixel" in terms                      # mined single term
    assert "pixel blast" in terms or "blast pixel" in terms
    assert not any(w in mined for w in ["bubble", "marble", "ball"])
    print(f"test_pixel_flow_class OK (mined={mined})")

def test_mine_ignores_stopwords():
    out = mine_new_words(["Best Fun Game 3D", "Super Puzzle World"], ["blast"])
    assert out == [], f"stopwords leaked: {out}"
    print("test_mine_ignores_stopwords OK")

def test_yarn_generic_leak():
    """Yarn run leaked generic words (color/away/sorting). Variants of known
    words and hyper-casual filler must not be mined."""
    verified = ["Yarn Sort 3D: Jam Puzzle", "Wool Color Sort: Yarn Stitch",
                "Knit Away - Yarn 3D", "Wool Craze 2 - Yarn Sort Games",
                "Yarn Spool: Knit Color Sort", "Wool Sorting: Unravel Yarn 3D",
                "Yarn Roll: Unravel Knit Sort"]
    known = ["yarn", "conveyor", "wool", "thread", "knit", "string",
             "sort", "wind", "weave", "loop", "tangle", "jam"]
    mined, _ = snowball_terms(verified, ["yarn", "conveyor"], known)
    for bad in ["color", "colors", "away", "craze", "sorting"]:
        assert bad not in mined, f"generic leak: {mined}"
    assert "unravel" in mined or "spool" in mined or "roll" in mined, f"real vocab lost: {mined}"
    print(f"test_yarn_generic_leak OK (mined={mined})")

def test_snowball_scoring_not_polluted():
    """Failure #20: snowball additions were scored with mined words as
    synonyms — 'Coffee Craze - Sorting Game' outranked 'Thread Jam'.
    Ranking must anchor to the user's words only."""
    from merge_score import score
    games = [
        {"name": "Thread Jam - Untangle 3D Ropes", "studio": "S", "days": 100,
         "ios": None, "android": {"installs": "1,000,000+", "num": 1000000, "score": 4, "url": "u", "icon": None}},
        {"name": "Coffee Craze - Sorting Game", "studio": "S2", "days": 100,
         "ios": None, "android": {"installs": "1,000,000+", "num": 1000000, "score": 4, "url": "u2", "icon": None}},
    ]
    score(games, ["yarn", "conveyor"], ["wool", "thread", "knit", "string"],
          ["sort", "knit", "wind", "weave", "loop", "tangle", "jam"])
    by = {g["name"]: g["rel"] for g in games}
    assert by["Thread Jam - Untangle 3D Ropes"] > by["Coffee Craze - Sorting Game"], by
    print("test_snowball_scoring_not_polluted OK")

test_pixel_flow_class()
test_mine_ignores_stopwords()
test_yarn_generic_leak()
test_snowball_scoring_not_polluted()
