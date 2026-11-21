#!/usr/bin/env python3
"""Print deals not yet reviewed, grouped by category, one short line each: <n> <title> | <price>
usage: review.py [sub ...]     -> list;   review.py --ok            -> mark everything currently listed as reviewed
Fix wrong ones with:  review.py --set <n>=<sub|drop> ...  (numbers from the last listing)"""
import json, os, sys
R = os.path.join(os.path.dirname(__file__), "..", "data")
D = json.load(open(os.path.join(R, "manual-deals.json"), encoding="utf-8"))["deals"]
RV = os.path.join(R, "reviewed.json"); OV = os.path.join(R, "overrides.json"); LAST = "/tmp/review_last.json"
rev = set(json.load(open(RV))) if os.path.exists(RV) else set()
ovr = json.load(open(OV)) if os.path.exists(OV) else {}
a = sys.argv[1:]
if a[:1] == ["--set"]:
    last = json.load(open(LAST))
    for kv in a[1:]:
        n, v = kv.split("="); ovr[last[int(n)]] = v
    json.dump(ovr, open(OV, "w"), ensure_ascii=False, indent=0)
    full = json.load(open(os.path.join(R, "manual-deals.json"), encoding="utf-8"))
    keep = []
    for d in full["deals"]:
        v = ovr.get(d["url"])
        if v == "drop": continue
        if v: d["sub"] = v
        keep.append(d)
    full["deals"] = keep
    json.dump(full, open(os.path.join(R, "manual-deals.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(ovr), "overrides,", len(keep), "deals"); sys.exit()
if a[:1] == ["--ok"]:
    last = json.load(open(LAST)); rev |= set(last)
    json.dump(sorted(rev), open(RV, "w"), ensure_ascii=False, indent=0); print(len(rev), "reviewed"); sys.exit()
SH = set(filter(None, os.environ.get("SHOPS", "").split(",")))
todo = [d for d in D if d["url"] not in rev and (not a or d.get("sub") in a) and (not SH or d["shop"] in SH)]
todo.sort(key=lambda d: (d.get("sub") or "", d["title"].lower()))
last, cur = [], None
for d in todo:
    if d.get("sub") != cur:
        cur = d.get("sub"); print(f"## {cur}")
    print(f"{len(last)} {d['title'][:70]}")
    last.append(d["url"])
json.dump(last, open(LAST, "w"))
print(len(last), "to review", file=sys.stderr)
