import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from search_stores import gen_terms

def test_gen_terms_full():
    terms = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"], depth="full")
    # full phrase
    assert "arrow drop" in terms
    # BOTH word orders of every pair (failure mode #8)
    assert "drop arrow" in terms
    assert "arrow sort" in terms and "sort arrow" in terms
    assert "marble sort" in terms and "sort marble" in terms
    # singles for every input + synonym word (failure mode #16)
    for w in ["arrow", "drop", "marble"]:
        assert w in terms
    # no duplicates
    assert len(terms) == len(set(terms))
    print("test_gen_terms_full OK")

def test_depth_tiers():
    p = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"], depth="precise")
    st = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"], depth="standard")
    fu = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"], depth="full")
    # precise: only the user's words — no mechanics, no synonyms
    assert "arrow drop" in p and "drop arrow" in p and "arrow" in p
    assert "arrow sort" not in p and "marble" not in p
    # standard adds mechanic combos, still no synonyms
    assert "arrow sort" in st and "sort arrow" in st and "marble" not in st
    # full adds the synonym family
    assert "marble sort" in fu and "sort marble" in fu and "marble" in fu
    # tiers strictly grow
    assert len(p) < len(st) < len(fu)
    print(f"test_depth_tiers OK (precise={len(p)} standard={len(st)} full={len(fu)} terms)")

test_gen_terms_full()
test_depth_tiers()
