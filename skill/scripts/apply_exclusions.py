# skill/scripts/apply_exclusions.py
"""Remove Claude-judged wrong-mechanic games from games.json."""
import json, sys

def apply(workdir):
    games = json.load(open(f"{workdir}/games.json"))
    excl = set(json.load(open(f"{workdir}/exclusions.json")))
    keep = [g for g in games if g["name"] not in excl]
    removed = len(games) - len(keep)
    json.dump(keep, open(f"{workdir}/games.json", "w"))
    for n in sorted(excl):
        print(f"  excluded: {n}")
    print(f"removed {removed}; {len(keep)} remain")
    return removed

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    apply(cfg["workdir"])
