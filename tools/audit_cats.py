#!/usr/bin/env python3
"""Flag deals whose category comes from a short rule match inside a longer word (e.g. 'uno' in 'Mizuno')."""
import json, os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from classify import explain
D = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json"), encoding="utf-8"))["deals"]
n = 0
for d in D:
    if d.get("sub") and d.get("subsrc") == "manual": continue
    sub, m, a, b, src = explain(d["title"], d["url"])
    t = d["title"].lower()
    if src != "name": continue
    inner = (a > 0 and t[a-1].isalpha()) or (b < len(t) and t[b].isalpha())
    if inner and len(m) <= 6:
        n += 1; print(f"{d['shop'][:8]:8} {sub:11} [{m}] {d['title'][:70]}")
print(n, "flagged", file=sys.stderr)
