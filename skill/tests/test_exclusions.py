import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from apply_exclusions import apply

def test_apply()
test_punctuation_insensitive():
    games = [{"name": "Arrow Drop"}, {"name": "Marble Woka Woka: Jungle Blast"}]
    with tempfile.TemporaryDirectory() as d:
        json.dump(games, open(f"{d}/games.json", "w"))
        json.dump(["Marble Woka Woka: Jungle Blast"], open(f"{d}/exclusions.json", "w"))
        removed = apply(d)
        left = json.load(open(f"{d}/games.json"))
    assert removed == 1 and len(left) == 1 and left[0]["name"] == "Arrow Drop"
    print("test_apply OK")

def test_punctuation_insensitive():
    """Failure #27: 'Block Blast!' must be removed by an exclusion written
    with a full-width bang ('Block Blast！')."""
    import json, tempfile
    games = [{"name": "Block Blast!"}, {"name": "Colony Flow!"}]
    with tempfile.TemporaryDirectory() as d:
        json.dump(games, open(f"{d}/games.json", "w"))
        json.dump(["Block Blast！"], open(f"{d}/exclusions.json", "w"))
        removed = apply(d)
        left = json.load(open(f"{d}/games.json"))
    assert removed == 1 and left[0]["name"] == "Colony Flow!"
    print("test_punctuation_insensitive OK")

test_apply()
test_punctuation_insensitive()
