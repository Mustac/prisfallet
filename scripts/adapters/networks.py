"""One small adapter per data source. Each reads its settings from environment variables
(GitHub Actions secrets) and is skipped when they are empty, so sources can be switched on
one by one as accounts get approved.

Settings (all optional):
  ADTRACTION_FEED_URLS   "Komplett|https://...feed-url..." one per line (links from the Adtraction dashboard)
  ADTRACTION_TOKEN       API v3 token  } alternative to feed links, see README (endpoint
  ADTRACTION_CHANNEL_ID  your channel  }  must be checked against Adtraction's v3 docs)
  ADTRACTION_PROGRAMS    "Komplett|programId" one per line
  AWIN_FEED_URL          one or more "Lekmer|https://productdata.awin.com/..." entries
  DAISYCON_FEED_URLS     "Coolshop|https://..." entries (Daisycon or Partner-ads feed links)
  KELKOO_TOKEN           Kelkoo Group publisher token (Bearer), country via KELKOO_COUNTRY (default "no")
  PRISJAKT_CLIENT_ID / PRISJAKT_CLIENT_SECRET / PRISJAKT_REF   Prisjakt Partner Search API (needs a RefID)
"""
import json
import os
import urllib.parse

from .common import http_get, load_json, parse_entries, pick, to_price
from .feeds import records, to_offer


def env(name):
    return (os.environ.get(name) or "").strip()


def _from_feed_links(var, network, log):
    offers = []
    for shop, url in parse_entries(env(var)):
        try:
            body = http_get(url, timeout=120)
            got = [o for o in (to_offer(r, network, shop) for r in records(body)) if o]
            log(f"  {network}: {shop or url[:40]} -> {len(got)} products")
            offers += got
        except Exception as e:                       # one broken feed must not stop the others
            log(f"  {network}: {shop or url[:40]} FAILED: {e}")
    return offers


def adtraction(log):
    if env("ADTRACTION_FEED_URLS"):
        return _from_feed_links("ADTRACTION_FEED_URLS", "adtraction", log)
    token, channel, programs = env("ADTRACTION_TOKEN"), env("ADTRACTION_CHANNEL_ID"), env("ADTRACTION_PROGRAMS")
    if not (token and channel and programs):
        return None
    base = env("ADTRACTION_API_BASE") or "https://api.adtraction.net/v3"
    offers = []
    for shop, program_id in parse_entries(programs):
        try:
            # Ask the API for this program's feed link, then download the feed itself.
            info = load_json(http_get(f"{base}/partner/products/feedinfo/{program_id}/{channel}",
                                      headers={"X-Token": token, "Accept": "application/json"}))
            feed_url = pick(info if isinstance(info, dict) else (info[0] if info else {}),
                            "feedUrl", "feedurl", "url", "downloadUrl")
            if not feed_url:
                log(f"  adtraction: {shop}: no feed link in API answer: {str(info)[:120]}")
                continue
            body = http_get(feed_url, headers={"X-Token": token}, timeout=180)
            got = [o for o in (to_offer(r, "adtraction", shop) for r in records(body)) if o]
            log(f"  adtraction: {shop} -> {len(got)} products")
            offers += got
        except Exception as e:
            log(f"  adtraction: {shop} FAILED: {e}")
    return offers


def awin(log):
    if not env("AWIN_FEED_URL"):
        return None
    return _from_feed_links("AWIN_FEED_URL", "awin", log)


def daisycon(log):
    if not env("DAISYCON_FEED_URLS"):
        return None
    return _from_feed_links("DAISYCON_FEED_URLS", "daisycon", log)


def kelkoo(log):
    token = env("KELKOO_TOKEN")
    if not token:
        return None
    country = env("KELKOO_COUNTRY") or "no"
    url = ("https://api.kelkoogroup.net/publisher/shopping/v2/feeds/offers?"
           + urllib.parse.urlencode({"country": country, "format": "json"}))
    try:
        body = http_get(url, headers={"Authorization": f"Bearer {token}"}, timeout=300)
    except Exception as e:
        log(f"  kelkoo: FAILED: {e}")
        return []
    offers = []
    for r in records(body):
        o = to_offer(r, "kelkoo")
        if not o:
            continue
        # Kelkoo gives the price before its rebate in priceWithoutRebate (handled in to_offer)
        offers.append(o)
    log(f"  kelkoo: {len(offers)} offers")
    return offers


def prisjakt(log):
    cid, secret, ref = env("PRISJAKT_CLIENT_ID"), env("PRISJAKT_CLIENT_SECRET"), env("PRISJAKT_REF")
    if not (cid and secret and ref):
        return None
    base = env("PRISJAKT_API_BASE") or "https://api.schibsted.com/prisjakt/partner-search"
    try:
        tok = load_json(http_get(f"{base}/token", method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 data=urllib.parse.urlencode({"grant_type": "client_credentials",
                                                              "client_id": cid, "client_secret": secret}).encode()))
        access = tok.get("access_token")
        path = env("PRISJAKT_DEALS_PATH") or "/suggestions"       # check against the API docs you get access to
        url = f"{base}{path}?" + urllib.parse.urlencode({"market": "no", "ref": ref, "limit": 500})
        body = http_get(url, headers={"Authorization": f"Bearer {access}", "Accept": "application/json"})
    except Exception as e:
        log(f"  prisjakt: FAILED: {e}")
        return []
    offers = []
    for r in records(body):
        price = r.get("price") if isinstance(r.get("price"), dict) else {}
        shop = r.get("shop") if isinstance(r.get("shop"), dict) else {}
        flat = dict(r)
        flat.setdefault("current_price", price.get("current") or r.get("currentPrice") or r.get("salesPrice"))
        flat.setdefault("original_price", price.get("regular") or r.get("originalPrice"))
        flat.setdefault("merchant", shop.get("name") or r.get("shopName"))
        o = to_offer(flat, "prisjakt")
        if o:
            offers.append(o)
    log(f"  prisjakt: {len(offers)} offers")
    return offers


ALL = {"adtraction": adtraction, "awin": awin, "daisycon": daisycon, "kelkoo": kelkoo, "prisjakt": prisjakt}
