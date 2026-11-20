#!/usr/bin/env python3
"""Daily update: fetch every connected affiliate feed, keep the real deals, write data/deals.json.

Run locally:   python scripts/update_deals.py
Run offline:   python scripts/update_deals.py --fixtures tests/fixtures   (uses sample feeds, no keys needed)

Rules (from the project spec):
  * a source whose key/link is not set is skipped, never an error
  * keep only products that are in stock and at least MIN_DISCOUNT off
  * "feed_before_price" is the shop's own stated before-price; it is NEVER called the 30-day low
  * "verified_30d_low" is only set once we have 30 days of our own price history for that product
  * affiliate links are kept exactly as the network gives them (tracking parameters intact)
  * images are linked from the network/shop, never downloaded or re-hosted
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from adapters import networks                    # noqa: E402
from adapters.feeds import records, to_offer     # noqa: E402
from classify import classify                    # noqa: E402

MIN_DISCOUNT = float(os.environ.get("MIN_DISCOUNT", "0.30"))
MAX_DISCOUNT = 0.90          # bigger "discounts" are almost always feed errors
# When one shop's product comes through several networks at the same price, use the network
# listed first (set to the network that pays more / tracks longer for that shop).
NETWORK_PRIORITY = [n.strip() for n in os.environ.get(
    "NETWORK_PRIORITY", "adtraction,awin,daisycon,kelkoo,prisjakt").split(",") if n.strip()]


def _net_rank(network):
    return NETWORK_PRIORITY.index(network) if network in NETWORK_PRIORITY else len(NETWORK_PRIORITY)
HISTORY_DAYS = 30
DATA = os.path.join(ROOT, "data")
# Hand-picked deals (direct shop links, no affiliate network) live in data/manual-deals.json.
# Each one carries the time its price was checked on the shop's own page; a deal that has not
# been re-checked within MANUAL_MAX_AGE_H hours is dropped, so stale prices never stay up.
MANUAL_FILE = "manual-deals.json"
MANUAL_MAX_AGE_H = float(os.environ.get("MANUAL_MAX_AGE_H", "48"))


def log(msg):
    print(msg, flush=True)


def offer_id(o):
    key = f"{o['source_network']}|{o['shop']}|{o['sku']}".lower()
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def collect(fixtures_dir=None):
    """Return (offers, status) where status says per source: ok / skipped / failed."""
    offers, status = [], {}
    if fixtures_dir:
        for fn in sorted(os.listdir(fixtures_dir)):
            m = re.match(r"(adtraction|awin|daisycon|kelkoo|prisjakt)[-_]?(.*)\.(xml|csv|json)$", fn)
            if not m:
                continue
            net, shop = m.group(1), m.group(2).replace("_", " ").title()
            with open(os.path.join(fixtures_dir, fn), "rb") as f:
                got = [o for o in (to_offer(r, net, shop if net in ("adtraction", "awin", "daisycon") else "")
                                   for r in records(f.read())) if o]
            log(f"  fixture {fn}: {len(got)} products")
            offers += got
            status[net] = "sample"
        return offers, status
    for name, fn in networks.ALL.items():
        got = fn(log)
        if got is None:
            log(f"  {name}: skipped (no key/link set)")
            status[name] = "skipped"
        else:
            status[name] = "ok" if got else "empty"
            offers += got
    return offers, status


def manual_offers(path, now=None):
    """Read hand-picked deals. Returns offers in the same shape as feed offers."""
    now = now or dt.datetime.now(dt.timezone.utc)
    data = load_json(path, {})
    out = []
    for m in data.get("deals", []):
        try:
            checked = dt.datetime.fromisoformat(m["checked"].replace("Z", "+00:00"))
            if (now - checked).total_seconds() > MANUAL_MAX_AGE_H * 3600:
                continue
            url = m["url"].strip()
            if not url.startswith("https://") or "prisjakt" in url:
                continue
            if not str(m.get("img", "")).startswith("https://"):
                continue   # his rule: every product shown has a real picture
            out.append({
                "source_network": "direct", "shop": m["shop"].strip(), "sku": url,
                "title": m["title"].strip(), "brand": (m.get("brand") or "").strip(),
                "current_price": float(m["price"]), "before_price": float(m["before"]) if m.get("before") else None,
                "image_url": m["img"] if str(m.get("img", "")).startswith("https://") else "", "affiliate_url": url, "in_stock": m.get("in_stock", True),
                "category_text": m.get("cat", ""), "checked": checked.astimezone(dt.timezone.utc).isoformat(timespec="minutes"),
                "specs": [str(x)[:80] for x in (m.get("specs") or [])][:4],
                "rating": float(m["rating"]) if m.get("rating") else None,
                "reviews": int(m["reviews"]) if m.get("reviews") else None,
            })
        except (KeyError, ValueError, TypeError):
            continue
    return out


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def update_history(history, offers, today):
    """history = {id: {"first": "YYYY-MM-DD", "p": {"YYYY-MM-DD": lowest price that day}}}"""
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=HISTORY_DAYS + 5)).isoformat()
    for o in offers:
        h = history.setdefault(o["id"], {"first": today, "p": {}})
        prev = h["p"].get(today)
        h["p"][today] = min(prev, o["current_price"]) if prev else o["current_price"]
    for pid in list(history):
        h = history[pid]
        h["p"] = {d: v for d, v in h["p"].items() if d >= cutoff}
        if not h["p"]:
            del history[pid]
    return history


def verified_30d_low(h, today):
    """Lowest price in the 30 days BEFORE today, only if our history really covers 30 days."""
    if not h:
        return None
    t = dt.date.fromisoformat(today)
    if (t - dt.date.fromisoformat(h["first"])).days < HISTORY_DAYS:
        return None
    start = (t - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    prior = [v for d, v in h["p"].items() if start <= d < today]
    return min(prior) if prior else None


def build(offers, history, today):
    """Pick the price basis, compute discount, keep only real deals."""
    deals, seen = [], {}
    for o in offers:
        if not o["in_stock"]:
            continue
        o["id"] = offer_id(o)
        low30 = verified_30d_low(history.get(o["id"]), today)
        if low30:
            basis, ref = "verified_30d_low", low30
        elif o["before_price"]:
            basis, ref = "feed_before_price", o["before_price"]
        else:
            continue
        pct = 1 - o["current_price"] / ref
        if pct < MIN_DISCOUNT or pct > MAX_DISCOUNT:
            continue
        sub = classify(o["title"] + " " + o.get("category_text", ""), o["affiliate_url"])
        deal = {
            "id": o["id"],
            "shop": o["shop"],
            "source_network": o["source_network"],
            "title": o["title"],
            "brand": o["brand"],
            "category": sub,
            "current_price": round(o["current_price"], 2),
            "feed_before_price": round(o["before_price"], 2) if o["before_price"] else None,
            "verified_30d_low": round(low30, 2) if low30 else None,
            "discount_percent": round(pct * 100),
            "price_basis": basis,
            "image_url": o["image_url"],
            "affiliate_url": o["affiliate_url"],
            "in_stock": True,
            "last_seen": today,
        }
        if o.get("checked"):
            deal["checked"] = o["checked"]
        for k in ("specs", "rating", "reviews"):
            if o.get(k):
                deal[k] = o[k]
        # The same product from the same shop via two networks is one deal: keep the cheaper
        # offer; at equal price keep the network that comes first in NETWORK_PRIORITY.
        # (The same product in different shops stays as separate deals - the visitor chooses.)
        key = (deal["shop"].lower(), re.sub(r"\W+", "", deal["title"].lower()))
        if key in seen:
            old = seen[key]
            if (old["current_price"], _net_rank(old["source_network"])) <= (deal["current_price"], _net_rank(deal["source_network"])):
                continue
        seen[key] = deal
    deals = sorted(seen.values(), key=lambda d: (-d["discount_percent"], d["current_price"]))
    return deals


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", help="read sample feeds from this folder instead of the networks")
    ap.add_argument("--today", help="pretend today is YYYY-MM-DD (tests)")
    ap.add_argument("--out", default=DATA)
    a = ap.parse_args(argv)
    today = a.today or dt.date.today().isoformat()
    os.makedirs(a.out, exist_ok=True)

    log(f"Prisfallet feed update {today}")
    offers, status = collect(a.fixtures)
    if not a.fixtures:
        manual = manual_offers(os.path.join(a.out, MANUAL_FILE))
        if manual:
            status["direct"] = "ok"
            offers += manual
            log(f"  hand-picked deals: {len(manual)} still fresh")
    has_manual_file = os.path.exists(os.path.join(a.out, MANUAL_FILE))
    if not a.fixtures and not offers and not has_manual_file:
        # No network connected yet (or all feeds failed): keep the current site data
        # instead of replacing it with an empty list.
        log("No offers from any source - keeping the existing data/deals.json unchanged.")
        return None
    for o in offers:
        o["id"] = offer_id(o)
    hist_path = os.path.join(a.out, "price-history.json")
    history = update_history(load_json(hist_path, {}), [o for o in offers if o["in_stock"]], today)
    deals = build(offers, history, today)

    shops = {}
    for d in deals:
        s = shops.setdefault(d["shop"], {"name": d["shop"], "network": d["source_network"], "deals": 0})
        s["deals"] += 1
    out = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "date": today,
        "demo": bool(a.fixtures),
        "min_discount": MIN_DISCOUNT,
        "sources": status,
        "shops": sorted(shops.values(), key=lambda s: -s["deals"]),
        "deals": deals,
    }
    with open(os.path.join(a.out, "deals.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, separators=(",", ":"))
    log(f"Read {len(offers)} products, kept {len(deals)} deals from {len(shops)} shops.")
    return out


if __name__ == "__main__":
    main()
