import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from search_stores import gen_terms

def test_gen_terms():
    terms = gen_terms(["arrow", "drop"], ["marble"], ["sort", "pop"])
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
    print("test_gen_terms OK")

test_gen_terms()
