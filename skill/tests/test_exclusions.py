import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from apply_exclusions import apply

def test_apply():
    games = [{"name": "Arrow Drop"}, {"name": "Marble Woka Woka: Jungle Blast"}]
    with tempfile.TemporaryDirectory() as d:
        json.dump(games, open(f"{d}/games.json", "w"))
        json.dump(["Marble Woka Woka: Jungle Blast"], open(f"{d}/exclusions.json", "w"))
        removed = apply(d)
        left = json.load(open(f"{d}/games.json"))
    assert removed == 1 and len(left) == 1 and left[0]["name"] == "Arrow Drop"
    print("test_apply OK")

test_apply()
