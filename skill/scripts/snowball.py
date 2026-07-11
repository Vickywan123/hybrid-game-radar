# skill/scripts/snowball.py
"""Post-judgment snowball wave (spec failure #17).

Runs AFTER apply_exclusions: mines new vocabulary from mechanic-VERIFIED
titles (judgment set minus exclusions), sweeps the stores with it, and
appends gate-passing new games to games.json (scored). New games that
need judgment are written to snowball_descriptions.json.

Why post-judgment: mining the raw pool surfaces the loudest impostor
genres (measured on 'blast': bubble/ball/marble); mining verified keeps
surfaces the family's real vocabulary (pixel, flow, ...).
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_stores import snowball_terms, run_sweep
from merge_score import merge, score, na

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    wd = cfg["workdir"]
    iw, syn, mech = cfg["input_words"], cfg["synonyms"], cfg["mechanics"]

    games = json.load(open(f"{wd}/games.json"))
    judged = {g["name"] for g in json.load(open(f"{wd}/descriptions.json"))}
    excluded = set(json.load(open(f"{wd}/exclusions.json")))
    verified = sorted(judged - excluded)
    if not verified:
        print("no verified titles to mine; skipping snowball")
        return
    known = iw + syn + mech
    mined, terms = snowball_terms(verified, iw, known)
    if not terms:
        print("nothing mined; skipping snowball")
        return
    print(f"snowball: mined {mined} from {len(verified)} verified titles -> {len(terms)} terms")

    pool = {}
    fam = [w.lower() for w in iw + syn] + mined
    run_sweep(pool, terms, fam, mech, cfg.get("platforms", "both"), "snowball")

    have = {(na(g["name"])[:16], na(g["studio"])) for g in games}
    new = [r for r in pool.values()
           if (na(r["name"])[:16], na(r["studio"])) not in have
           and r["name"] not in excluded]
    if not new:
        print("snowball found no new games"); return

    merged_new = merge(new)
    # score with the USER'S synonyms only — mined words widen the net (gate),
    # never the ranking (§3.4: anchor to the user's words, not Claude's)
    score(merged_new, iw, syn, mech)
    games += merged_new
    json.dump(games, open(f"{wd}/games.json", "w"))
    top = sorted(merged_new, key=lambda g: -(g.get("reach", 0)))[:10]
    print(f"snowball added {len(merged_new)} new games (now {len(games)} total). biggest:")
    for g in top:
        print(f"  + {g['name']} — {g['studio']} (reach {g.get('reach', 0):,})")
    # hand the new candidates to Claude for a second, small judgment round
    json.dump([{"name": g["name"], "studio": g["studio"]} for g in merged_new],
              open(f"{wd}/snowball_new.json", "w"))

if __name__ == "__main__":
    main(sys.argv[1])
