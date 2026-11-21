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
sys.path.insert(0, os.path.dirname(__file__))
from shops import img_ok
import re as _re
from urllib.parse import urlparse
TOP = {}
for _c, _subs in _re.findall(r'\{id:"([a-z]+)".*?subs:\[(.*?)\]\}', open(os.path.join(os.path.dirname(__file__), "..", "index.html"), encoding="utf-8").read(), _re.S):
    for _k in _re.findall(r'\["([a-z]+)","', _subs): TOP[_k] = _c
# Shop category hint (x["g"]) -> top categories allowed. A product whose computed category does not
# fit the shop's own category is dropped, so one bad keyword rule can never put shoes among board games.
HINTS = [
    (r"tv-lyd|tv-og-lyd|/tv/|/lyd/|lydplank|hoeyttal|hodetelefon|mobil|smartklokk|nettbrett|foto", {"electronics", "photo", "computers", "gaming"}),
    (r"data|pc-og-mac|skjermer|datatilbeh|kontor", {"computers", "electronics", "gaming", "photo"}),
    (r"gaming", {"gaming", "computers", "electronics"}),
    (r"hvitevar", {"appliances", "kitchen", "home"}),
    (r"husholdning|stoevsug|kjoekken|kjokken", {"home", "kitchen", "appliances"}),
    (r"personlig-pleie|skjoennhet|helse", {"beauty"}),
    (r"sport|fritid", {"sports", "toys", "home", "electronics", "photo", "tools"}),
    (r"hjem-og-hage|hage", {"home", "tools", "kitchen"}),
    (r"lego", {"toys"}),
    (r"leker|leketoy|strollers|carseats|baby|bilstol|barnevogn", {"toys"}),
    (r"apple", {"electronics", "computers"}),
    (r"bil---mc|bil-og-garasje|biltilbeh|/bil/|verktoy|bygg|oppbevaring|maskiner", {"tools", "home"}),
]
def fits(g, sub):
    if not g: return True
    g = g.lower()
    allowed = set()
    for rx, ok in HINTS:
        if _re.search(rx, g): allowed |= ok
    if allowed & {"electronics", "computers", "gaming"}: allowed |= {"mobil", "laptop", "desktop"}
    return not allowed or TOP.get(sub) in allowed

shop, base, src = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
args = sys.argv[4:]
append = "--append" in args
mx = int(args[args.index("--max") + 1]) if "--max" in args else 100000
minsave = float(args[args.index("--minsave") + 1]) if "--minsave" in args else 0
dropother = "--drop-other" in args
minprice = float(args[args.index("--minprice") + 1]) if "--minprice" in args else 0
kids = "--kids" in args  # toy/baby shop: everything lands in a "Barn og leker" sub
KIDS = {"lego","toys","boardgames","dolls","rc","outdoorkids","crafts","baby","strollers","carseats"}
only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
path = os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json")
data = json.load(open(path, encoding="utf-8"))
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
old = {d["url"]: d for d in data["deals"]}
items = json.load(open(src, encoding="utf-8"))
OVR_P = os.path.join(os.path.dirname(__file__), "..", "data", "overrides.json")
IMGO = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "img-overrides.json"))) if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "img-overrides.json")) else {}  # url -> working image (checked by hand)
OVR = json.load(open(OVR_P, encoding="utf-8")) if os.path.exists(OVR_P) else {}  # url -> sub or "drop" (from manual review)
new, seen, why = [], set(), {}
def _pct(x):
    try: return 1 - float(x.get("p") or 0) / float(x.get("b") or 1)
    except (ValueError, ZeroDivisionError): return 0
items.sort(key=lambda x: -_pct(x) if 0.30 <= _pct(x) <= 0.75 else 1)
def skip(k): why[k] = why.get(k, 0) + 1
for x in items:
    t = re.sub(r"\s+", " ", (x.get("t") or "")).strip()
    for _ in range(3):
        t = re.sub(r"^(kun online|ny lavere pris!?|nyhet|bestselger|black week|-?\d[\d ]*,-)\s*", "", t, flags=re.I).strip()
    t = re.sub(r"(\s*\((?:KOMP|REUR|RDKK|RDEU|RNOR)\))+\s*$", "", t).strip()   # NetOnNet stock codes like (KOMP)(REUR)
    w = t.split()
    if len(w) > 2 and w[1].isupper() and w[1] != w[0] and w[1].lower() == w[0].lower():   # "Acer ACER Acer Swift" -> "Acer Swift"
        w.pop(1)
        if w[1] == w[0]: w.pop(1)
    t = " ".join(w)
    if "--desc" in args and x.get("specs") and len(t) < 30 and not re.search(r"[a-zæøå]{3}", " ".join(w[1:])):
        dsc = x["specs"][0].strip()
        tl = {z.lower() for z in t.split()}
        dw = dsc.split()
        while dw and dw[0].lower() in tl: dw.pop(0)
        if dw: t = t + " – " + " ".join(dw)
    u = x.get("u") or ""
    url = u if u.startswith("http") else base + u
    try: p, b = float(x.get("p") or 0), float(x.get("b") or 0)
    except ValueError: skip("price"); continue
    img = IMGO.get(u if u.startswith("http") else base + u) or x.get("img") or ""
    letters = [c for c in t if c.isalpha()]
    upper = sum(c.isupper() for c in letters) / max(1, len(letters))
    if (len(t) < 8 or (len(t) < 22 and re.match(r"\d", t)) or t.lower() in ("nyhet", "tilbud", "bestselger", "kampanje", "outlet") or "*" in t
            or (upper > 0.6 and len(letters) > 8 and not re.search(r"[A-Za-zÆØÅæøå]*[a-zæøå]{3}", t)) or re.match(r"(få|prøv|opptil|spar|inkl|gratis|samle|kjøp|bonus|cashback|\d+ ?mnd)\b", t, re.I)):
        skip("title"); continue
    if not t or not p or b <= p: skip("noprice"); continue
    pct = 1 - p / b
    if not 0.30 <= pct <= 0.75: skip("pct"); continue
    if not img.startswith("https://") or not img_ok(shop, img): skip("img"); continue
    if "st" in x and not x["st"]: skip("stock"); continue
    if b - p < minsave or p < minprice: skip("small"); continue
    if url in seen or (shop, t.lower()) in seen: continue
    sub = x.get("sub") or classify(t + (" | " + x["specs"][0] if "--desc" in args and x.get("specs") and len(t) < 40 else ""), url)
    if x.get("sub") in KIDS:  # shop listing group (e.g. Jollyroom car seats); a clear name rule wins
        c = classify(t, url)
        if c in KIDS and c != "toys": sub = c
    if kids and sub not in KIDS: sub = x.get("kdef") or "toys"
    if OVR.get(url) == "drop": skip("reviewed-drop"); continue
    if url in OVR: sub = OVR[url]
    if sub == "drop" or (kids and classify(t, "") == "drop"): skip("drop"); continue
    if only and sub not in only: skip("sub"); continue
    hint = "" if kids else (x.get("g") or urlparse(url).path.lower())
    if sub != "drop" and not fits(hint, sub):
        alt = classify("", url) if url else "other"   # the shop's own category path
        if alt not in ("other", "drop") and fits(hint, alt): sub = alt
    if not fits(hint, sub): skip("mismatch"); print("   mismatch:", (x.get("g") or urlparse(url).path)[:40], sub, t[:60]) if "-v" in args else None; continue
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
