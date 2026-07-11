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

test_pixel_flow_class()
test_mine_ignores_stopwords()
