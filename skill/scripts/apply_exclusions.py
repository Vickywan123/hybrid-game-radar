# skill/scripts/apply_exclusions.py
"""Remove Claude-judged wrong-mechanic games from games.json.
Matching is PUNCTUATION-INSENSITIVE (failure #27: "Block Blast!" survived an
exclusion written as "Block Blast！" — full-width vs ASCII bang)."""
import json, re, sys

def na(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def apply(workdir):
    games = json.load(open(f"{workdir}/games.json"))
    excl = set(json.load(open(f"{workdir}/exclusions.json")))
    excl_na = {na(x) for x in excl}
    keep = [g for g in games if na(g["name"]) not in excl_na]
    removed = len(games) - len(keep)
    json.dump(keep, open(f"{workdir}/games.json", "w"))
    for n in sorted(excl):
        print(f"  excluded: {n}")
    print(f"removed {removed}; {len(keep)} remain")
    return removed

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    apply(cfg["workdir"])
