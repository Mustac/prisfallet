#!/usr/bin/env python3
"""Pre-deploy inspection of data/manual-deals.json and the built data/deals.json.
Exits 1 on any problem. Picture/link checks run in the browser (tools/browser-check.js)."""
import json, re, sys, os
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(__file__))
from shops import SHOPS, img_ok
ROOT = os.path.join(os.path.dirname(__file__), "..")
HOST = {"Elkjøp": "elkjop.no", "Power": "power.no", "Komplett": "komplett.no", "NetOnNet": "netonnet.no",
        "Proshop": "proshop.no", "Kjell & Company": "kjell.com", "XXL": "xxl.no", "Lekekassen": "lekekassen.no",
        "Jollyroom": "jollyroom.no", "Jula": "jula.no", "Biltema": "biltema.no", "Clas Ohlson": "clasohlson.com",
        "Babyshop": "babyshop.no", "Lekmer": "lekmer.no", "Extra Leker": "extraleker.no", "Proshop": "proshop.no"}
idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
cats = re.search(r"const CATS=\[(.*?)\n\];", idx, re.S).group(1)
SUBS = set(re.findall(r'\["([a-z]+)","', cats))
deals = json.load(open(os.path.join(ROOT, "data", "manual-deals.json"), encoding="utf-8"))["deals"]
bad, seen = [], {}
BADT = re.compile(r"^(nyhet|tilbud|bestselger|kampanje)$|undefined|null|\bNaN\b|&amp;|&#|\\u00|<", re.I)
for d in deals:
    def err(m): bad.append(f"{d['shop']} | {m} | {d.get('title','')[:50]} | {d.get('url','')}")
    u, img, t = d.get("url", ""), d.get("img", ""), d.get("title", "")
    h = urlparse(u).hostname or ""
    if not u.startswith("https://"): err("url not https")
    if d["shop"] not in SHOPS: err("unknown shop")
    elif not h.endswith(SHOPS[d["shop"]][0]): err("url host " + h)
    if not img.startswith("https://") or " " in img or not img_ok(d["shop"], img): err("img")
    if len(t) < 6 or BADT.search(t): err("title")
    p, b = d.get("price", 0), d.get("before", 0)
    if not (p > 0 and b > p): err("price")
    elif not 0.30 <= 1 - p / b <= 0.75: err(f"pct {round((1-p/b)*100)}")
    if p > 200000: err("price too high")
    if d.get("sub") and d["sub"] not in SUBS: err("unknown sub " + d["sub"])
    if u in seen: err("duplicate url")
    seen[u] = 1
built = json.load(open(os.path.join(ROOT, "data", "deals.json"), encoding="utf-8"))["deals"]
other = [x for x in built if x["category"] == "other"]
print(f"{len(deals)} manual deals, {len(built)} built, {len(other)} in 'Annet', {len(bad)} problems")
for m in bad[:60]: print("  ", m)
sys.exit(1 if bad else 0)
