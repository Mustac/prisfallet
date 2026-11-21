#!/usr/bin/env python3
"""Import a shop's whole sale listing, saved from the browser as JSON:
[{"u": path-or-url, "t": title, "p": price, "b": before, "img": https-url,
  "st": in-stock flag/count (optional), "sub": (optional), "brand": (optional), "specs": [..] (optional)}]

usage: import_listing.py <Shop> <https://base> <file.json> [--append] [--max N] [--only sub1,sub2]
Without --append the shop's list is replaced, so ended offers drop out (this is also the daily re-check).
Keeps 30-75 % off, https picture, in stock. Category comes from classify() unless "sub" is given."""
import sys, json, os, re, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from classify import classify

shop, base, src = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
args = sys.argv[4:]
append = "--append" in args
mx = int(args[args.index("--max") + 1]) if "--max" in args else 100000
minsave = float(args[args.index("--minsave") + 1]) if "--minsave" in args else 0
dropother = "--drop-other" in args
kids = "--kids" in args  # toy/baby shop: everything lands in a "Barn og leker" sub
KIDS = {"lego","toys","boardgames","dolls","rc","outdoorkids","crafts","baby","strollers","carseats"}
only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
path = os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json")
data = json.load(open(path, encoding="utf-8"))
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
old = {d["url"]: d for d in data["deals"]}
items = json.load(open(src, encoding="utf-8"))
new, seen, why = [], set(), {}
def _pct(x):
    try: return 1 - float(x.get("p") or 0) / float(x.get("b") or 1)
    except (ValueError, ZeroDivisionError): return 0
items.sort(key=lambda x: -_pct(x) if 0.30 <= _pct(x) <= 0.75 else 1)
def skip(k): why[k] = why.get(k, 0) + 1
for x in items:
    t = re.sub(r"\s+", " ", (x.get("t") or "")).strip()
    u = x.get("u") or ""
    url = u if u.startswith("http") else base + u
    try: p, b = float(x.get("p") or 0), float(x.get("b") or 0)
    except ValueError: skip("price"); continue
    img = x.get("img") or ""
    if len(t) < 6 or t.lower() in ("nyhet", "tilbud", "bestselger", "kampanje", "outlet"): skip("title"); continue
    if not t or not p or b <= p: skip("noprice"); continue
    pct = 1 - p / b
    if not 0.30 <= pct <= 0.75: skip("pct"); continue
    if not img.startswith("https://") or "placeholder" in img: skip("img"); continue
    if "st" in x and not x["st"]: skip("stock"); continue
    if b - p < minsave: skip("small"); continue
    if url in seen or (shop, t.lower()) in seen: continue
    sub = x.get("sub") or classify(t, url)
    if kids and sub not in KIDS: sub = x.get("kdef") or "toys"
    if only and sub not in only: skip("sub"); continue
    if dropother and sub == "other": skip("other"); continue
    seen.add(url); seen.add((shop, t.lower()))
    d = {"shop": shop, "title": t, "brand": x.get("brand", ""), "price": p, "before": b, "url": url, "img": img, "checked": now, "sub": sub}
    if x.get("specs"): d["specs"] = x["specs"][:4]
    if x.get("until"): d["until"] = x["until"]
    o = old.get(url, {})
    for k in ("rating", "reviews", "specs", "until"):
        if k in o and k not in d: d[k] = o[k]
    if x.get("r"): d["rating"] = float(x["r"])
    if x.get("n"): d["reviews"] = int(x["n"])
    new.append(d)
new.sort(key=lambda d: -(1 - d["price"] / d["before"]))
new = new[:mx]
urls = {d["url"] for d in new}
data["deals"] = [d for d in data["deals"] if d["shop"] != shop or (append and d["url"] not in urls)] + new
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(f"{shop}: kept {len(new)} of {len(items)} (skipped {why}); total {len(data['deals'])}")
print("  subs:", dict(Counter(d["sub"] for d in new).most_common(12)))
