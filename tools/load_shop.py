#!/usr/bin/env python3
"""Replace one shop's hand-picked deals from a tab-separated list (one deal per line):
title, brand, price, before, url, img, until(YYYY-MM-DD or ''), sub, specs(';'-separated)
Ratings already stored for the same URL are kept."""
import sys, json, os, datetime as dt
shop = sys.argv[1]
append = "--append" in sys.argv[2:]  # keep this shop's other deals
path = os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json")
data = json.load(open(path, encoding="utf-8"))
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
old = {d["url"]: d for d in data["deals"] if d["shop"] == shop}
new = []
for line in sys.stdin:
    p = line.rstrip("\n").split("\t")
    if len(p) < 6 or not p[0].strip():
        continue
    p += [""] * (9 - len(p))
    title, brand, price, before, url, img, until, sub, specs = [x.strip() for x in p[:9]]
    price, before = float(price), float(before)
    if before <= 0 or not (0.30 <= 1 - price / before <= 0.75) or not img.startswith("https://"):
        print("skip", title); continue
    d = {"shop": shop, "title": title, "brand": brand, "price": price, "before": before, "url": url, "img": img, "checked": now}
    if until: d["until"] = until
    if sub: d["sub"] = sub
    sp = [s.strip() for s in specs.split(";") if s.strip()][:4]
    if sp: d["specs"] = sp
    o = old.get(url, {})
    for k in ("rating", "reviews"):
        if k in o: d[k] = o[k]
    if not sp and o.get("specs"): d["specs"] = o["specs"]
    new.append(d)
urls = {d["url"] for d in new}
data["deals"] = [d for d in data["deals"] if d["shop"] != shop or (append and d["url"] not in urls)] + new
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{shop}: {len(new)} deals, {len(data['deals'])} total")
