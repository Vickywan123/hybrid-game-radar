import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from merge_score import merge, score

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "pool_fixture.json")

def test_merge_and_tiers():
    recs = json.load(open(FIX))
    out = merge(recs)
    names = [r["name"] for r in out]
    # subtitle-aware cross-store merge (failure mode #5)
    sand = [r for r in out if "Sand Balls" in r["name"] and "Gravity" not in r["name"]]
    assert len(sand) == 1 and sand[0]["ios"] and sand[0]["android"]
    # different-dev same-noun game NOT merged (safety lock §4.2.3)
    assert any("Gravity Sand Balls" in n for n in names)
    # tiered scoring anchored to input (failure mode #15)
    score(out, ["arrow", "drop"], ["marble"], ["sort", "pop"])
    by = {r["name"]: r["rel"] for r in out}
    assert by["Arrow Drop"] == 1000                      # tier 0
    assert 500 <= by["Drop Arrow Pop"] < 1000            # tier 1
    assert by["Marble Sort! - Color Puzzle"] < 500       # tier 2
    print("test_merge_and_tiers OK")

test_merge_and_tiers()
