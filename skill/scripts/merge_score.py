# skill/scripts/merge_score.py
"""Cross-store merge + tiered relevance. Spec: design doc §3.4, §4."""
import json, re, sys

def na(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def base(name):
    return na(re.split(r"\s*[-:–—|·]\s*", name, maxsplit=1)[0])

def merge(records):
    by_studio = {}
    for r in records:
        by_studio.setdefault(na(r["studio"]), []).append(r)
    gone = set()
    for grp in by_studio.values():
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                if id(a) in gone or id(b) in gone: continue
                an, bn = na(a["name"]), na(b["name"])
                if not (an.startswith(bn) or bn.startswith(an)
                        or (base(a["name"]) and base(a["name"]) == base(b["name"]))):
                    continue
                if a["ios"] and not a["android"] and b["android"] and not b["ios"]:
                    keep, drop = a, b
                elif b["ios"] and not b["android"] and a["android"] and not a["ios"]:
                    keep, drop = b, a
                else:
                    continue                       # safety lock §4.2.3
                keep["android"] = drop["android"]
                if drop["days"] is not None and (keep["days"] is None or drop["days"] < keep["days"]):
                    keep["days"] = drop["days"]
                gone.add(id(drop))
    return [r for r in records if id(r) not in gone]

def reach(r):
    a = r["android"]["num"] if r["android"] else 0
    i = (r["ios"]["ratings"] * 30) if r["ios"] else 0    # reviews ~3% of installs
    return max(a, i)

def score(records, input_words, synonyms, mechanics):
    q = na(" ".join(input_words))
    fam = input_words + synonyms
    for r in records:
        n = r["name"].lower()
        r["reach"] = reach(r)
        if na(r["name"]) == q:
            r["rel"] = 1000                                            # tier 0
        elif all(w in n for w in input_words):
            r["rel"] = 500 + sum(1 for w in mechanics if w in n)       # tier 1
        else:                                                          # tier 2
            r["rel"] = (sum(1 for w in input_words if w in n) * 10
                        + sum(1 for w in fam if w in n) * 3
                        + min(sum(1 for w in mechanics if w in n), 3) * 2)

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    recs = json.load(open(f"{cfg['workdir']}/pool.json"))
    out = merge(recs)
    score(out, cfg["input_words"], cfg["synonyms"], cfg["mechanics"])
    json.dump(out, open(f"{cfg['workdir']}/games.json", "w"))
    print(f"merged: {len(recs)} -> {len(out)} games")

if __name__ == "__main__":
    main(sys.argv[1])
