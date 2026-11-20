#!/usr/bin/env python3
"""Add key specs and the shop's customer rating to hand-picked deals.
Usage: enrich.py < lines   (each line: url-part|rating|reviews|spec1;spec2;spec3)
url-part is any unique piece of the deal's URL (e.g. the product id). Empty fields are skipped."""
import sys, json, os
path = os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json")
data = json.load(open(path, encoding="utf-8"))
n = 0
for line in sys.stdin:
    p = line.rstrip("\n").split("|")
    if len(p) < 4 or not p[0].strip():
        continue
    key, rating, reviews, specs = p[0].strip(), p[1].strip().rstrip("."), p[2].strip(), p[3]
    hits = [d for d in data["deals"] if key in d["url"]]
    if len(hits) != 1:
        print("skip (matches %d): %s" % (len(hits), key)); continue
    d = hits[0]
    if rating and reviews and float(rating) > 0 and int(float(reviews)) > 0:
        d["rating"] = round(float(rating), 1); d["reviews"] = int(float(reviews))
    sp = [s.strip() for s in specs.split(";") if s.strip()][:4]
    if sp:
        d["specs"] = sp
    n += 1
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"enriched {n} deals")
