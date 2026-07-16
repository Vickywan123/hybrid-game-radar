import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from search_stores import mine_new_words, snowball_terms

def test_universal_fillers_not_mined():
    """Failure #28: 'block'/'escape' mined from arrow-out titles dragged in
    grid-fill puzzles and room-escape adventures (240 of 450 additions)."""
    verified = ["Arrow Out 3D: Tap Away", "Block Away - Tap Out Puzzle",
                "Arrow Escape: Logic Puzzle", "Block Escape: Tap Away Puzzle",
                "Wooden Slide: Block Escape", "Arrows - Puzzle Escape"]
    mined = mine_new_words(verified, ["arrow", "sand", "drop", "out", "tap"])
    for bad in ["block", "escape", "wood", "wooden", "slide", "away"]:
        assert bad not in mined, f"filler leaked: {mined}"
    print(f"test_universal_fillers_not_mined OK (mined={mined})")

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
    # pixel appears in only 2 verified titles -> no single term (failure #24),
    # but combos must still exist (verified live: 'pixel blast' finds Pixel Flow!)
    assert "pixel" not in terms, f"weak single leaked: {terms}"
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

def test_theme_dominates_mechanic():
    """Failure #22: 'conveyor jam' (mechanic word only) outranked yarn games.
    With theme_words=['yarn'], every yarn/wool/knit game must beat it."""
    from merge_score import score
    def g(name):
        return {"name": name, "studio": "S", "days": 10, "ios": None,
                "android": {"installs": "10+", "num": 10, "score": 4, "url": "u", "icon": None}}
    games = [g("conveyor jam"), g("Color Sort Conveyor"), g("Yarn Maze"),
             g("Wool Frenzy"), g("Thread Jam - Untangle 3D Ropes")]
    score(games, ["yarn", "conveyor"], ["wool", "thread", "knit", "string"],
          ["sort", "knit", "wind", "weave", "loop", "tangle", "jam"], theme_words=["yarn"])
    by = {x["name"]: x["rel"] for x in games}
    assert by["Yarn Maze"] > by["conveyor jam"], by
    assert by["Wool Frenzy"] > by["conveyor jam"], by
    assert by["Thread Jam - Untangle 3D Ropes"] > by["Color Sort Conveyor"], by
    print("test_theme_dominates_mechanic OK")

def test_single_needs_strong_evidence():
    """Failure #24: 'find'/'logic'/'frenzy' singles flooded the Seat Away run
    with hidden-object and logic-grid genres. Singles need >=3 verified titles."""
    verified = ["Find Seat", "Find My Seat",                       # find x2 -> no single
                "Spool Sort", "Spool Jam", "Spool Away"]           # spool x3 -> single ok
    known = ["seat", "sort", "jam", "away"]
    mined, terms = snowball_terms(verified, ["seat"], known)
    assert "find" in mined and "spool" in mined
    assert "find" not in terms, f"weak single leaked: {terms}"
    assert "spool" in terms, f"strong single missing: {terms}"
    assert "find seat" in terms                                    # combos always allowed
    print("test_single_needs_strong_evidence OK")

test_pixel_flow_class()
test_single_needs_strong_evidence()
test_theme_dominates_mechanic()
test_mine_ignores_stopwords()
test_yarn_generic_leak()
test_snowball_scoring_not_polluted()
test_universal_fillers_not_mined()
