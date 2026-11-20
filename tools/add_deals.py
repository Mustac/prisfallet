#!/usr/bin/env python3
"""Add or replace one shop's hand-picked deals in data/manual-deals.json.
Usage: add_deals.py "<Shop>" "<url prefix>" < lines   (each line: title|brand|price|before|path)
All deals of that shop are replaced, and get the current time as 'checked'."""
import sys, json, datetime as dt, os
shop, prefix = sys.argv[1], sys.argv[2]
path = os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json")
try:
    data = json.load(open(path, encoding="utf-8"))
except FileNotFoundError:
    data = {"note": "Hand-picked deals with direct links to the shop. Prices checked on the shop's own product page.", "deals": []}
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
new = []
for line in sys.stdin:
    p = line.rstrip("\n").split("|")
    if len(p) < 5:
        continue
    title, brand, price, before, link = p[:5]
    price, before = float(price), float(before)
    if before <= 0 or 1 - price / before < 0.30:
        continue
    new.append({"shop": shop, "title": title.strip(), "brand": brand.strip(), "price": price, "before": before,
                "url": link if link.startswith("https://") else prefix + link, "checked": now})
old = {d["url"]: d for d in data["deals"] if d["shop"] == shop}
for d in new:   # keep specs/ratings already collected for the same product
    for k in ("specs", "rating", "reviews", "img"):
        if k in old.get(d["url"], {}):
            d[k] = old[d["url"]][k]
data["deals"] = [d for d in data["deals"] if d["shop"] != shop] + new
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{shop}: {len(new)} deals saved, {len(data['deals'])} total")
