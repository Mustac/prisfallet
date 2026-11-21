#!/usr/bin/env python3
"""Turn a shop-specific browser dump into the import_listing.py format.
usage: convert.py <shop> <in.json> <out.json>"""
import sys, json, re
shop, src, dst = sys.argv[1:4]
raw = json.load(open(src, encoding="utf-8"))
vals = list(raw.values()) if isinstance(raw, dict) else raw
out = []
for x in vals:
    if shop == "jollyroom":
        y = {"u": x["u"], "t": x["t"], "p": x["p"], "b": x["b"], "img": x["img"], "st": x.get("st"), "n": x.get("rv") or 0}
        if x.get("g") in ("strollers", "carseats"): y["sub"] = x["g"]
        if x.get("g") == "baby": y["kdef"] = "baby"
    elif shop == "elkjop":
        if not x.get("img"): continue
        sp = [s for s in x.get("sp", []) if not re.fullmatch(r"[\d.,]+", s)]
        y = {"u": "/product/" + x["id"], "t": x["t"], "p": x["p"], "b": x["b"], "st": x.get("st"),
             "img": f"https://www.elkjop.no/image/{x['img']}/{x['id']}/p.jpg", "specs": sp[:3], "until": x.get("until") or ""}
    elif shop == "power":
        if "bedrift" in (x.get("g") or "") or re.search(r"repower|renovert|demo", x["t"], re.I): continue
        y = {"u": x["u"], "t": x["t"], "p": x["p"], "b": x["b"], "st": x.get("st"), "img": x.get("img", ""), "specs": x.get("sp", [])[:3]}
    else:
        y = x
    out.append(y)
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
print(shop, len(out), "items")
