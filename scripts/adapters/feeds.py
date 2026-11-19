"""Readers for plain product feed files (XML, CSV, JSON) as delivered by affiliate networks.

Every network names its fields a little differently, so each reader turns a feed into
plain dicts, and `to_offer` maps the many possible field names onto one shape.
"""
import csv
import io
import json
import xml.etree.ElementTree as ET

from .common import pick, to_bool_stock, to_price


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else tag


def records_from_xml(body: bytes):
    """Yield one dict per product element (any element whose children are simple fields)."""
    root = ET.fromstring(body)
    # find the repeating element: the child tag that occurs most often somewhere in the tree
    best, best_n = None, 0
    for parent in root.iter():
        counts = {}
        for ch in parent:
            counts[_local(ch.tag)] = counts.get(_local(ch.tag), 0) + 1
        for tag, n in counts.items():
            if n > best_n and len(list(parent)) and any(len(list(c)) for c in parent):
                best, best_n = tag, n
    items = [el for el in root.iter() if _local(el.tag) == best] if best else [root]
    for el in items:
        rec = {}
        for ch in el.iter():
            if ch is el:
                continue
            key = _local(ch.tag)
            text = (ch.text or "").strip()
            if text and key not in rec:
                rec[key] = text
            for ak, av in ch.attrib.items():          # e.g. <image url="..."/>
                rec.setdefault(f"{key}_{_local(ak)}", av)
        if rec:
            yield rec


def records_from_csv(body: bytes):
    text = body.decode("utf-8-sig", errors="replace")
    sample = text[:5000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    yield from csv.DictReader(io.StringIO(text), dialect=dialect)


def records_from_json(body: bytes):
    data = json.loads(body.decode("utf-8-sig"))
    if isinstance(data, dict):
        for key in ("offers", "products", "items", "data", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if isinstance(data, list):
        yield from (d for d in data if isinstance(d, dict))


def records(body: bytes):
    head = body.lstrip()[:1]
    if head == b"<":
        return records_from_xml(body)
    if head in (b"{", b"["):
        return records_from_json(body)
    return records_from_csv(body)


def _first_url(v):
    if isinstance(v, list) and v:
        v = v[0]
    if isinstance(v, dict):
        v = pick(v, "url", "href", "src", "large", "default")
    return v if isinstance(v, str) and v.startswith("http") else None


def _name(v):
    if isinstance(v, dict):
        return pick(v, "name", "title", "label")
    return v


def to_offer(rec: dict, network: str, shop: str = ""):
    """Map a raw feed record onto the shared offer shape. Returns None if unusable."""
    title = pick(rec, "title", "name", "product_name", "productname", "producttitle")
    current = to_price(pick(rec, "search_price", "salesprice", "sale_price", "price", "currentprice",
                            "current_price", "price_inc_vat", "store_price"))
    before = to_price(pick(rec, "oldprice", "old_price", "price_old", "product_price_old", "originalprice",
                           "original_price", "regularprice", "regular_price", "pricewithoutrebate",
                           "rrp_price", "listprice", "list_price", "beforeprice", "normalprice"))
    url = pick(rec, "trackingurl", "tracking_url", "aw_deep_link", "deeplink", "deep_link", "affiliate_url",
               "affiliatelink", "gourl", "go_url", "link", "url", "producturl", "product_url")
    if isinstance(url, dict):
        url = pick(url, "url", "href")
    image = (_first_url(pick(rec, "imageurl", "image_url", "merchant_image_url", "aw_image_url", "image_large",
                              "image_default", "large_image", "image", "images", "image_link", "imageurls",
                              "image_url_large", "picture", "location")))
    if not title or not current or not url:
        return None
    merchant = _name(pick(rec, "merchant_name", "merchant", "shop", "shopname", "store", "retailer", "program"))
    return {
        "shop": shop or (merchant or "").strip() or network.title(),
        "source_network": network,
        "sku": str(pick(rec, "sku", "aw_product_id", "merchant_product_id", "productid", "product_id", "offerid",
                        "offer_id", "id", "ean", default=title))[:80],
        "title": str(title).strip()[:160],
        "brand": str(_name(pick(rec, "brand", "brand_name", "manufacturer", "make", default="")) or "").strip()[:60],
        "category_text": str(_name(pick(rec, "category", "merchant_category", "category_name", "categorypath",
                                        "producttype", "product_type", default="")) or "")[:200],
        "current_price": current,
        "before_price": before if before and before > current else None,
        "image_url": image or "",
        "affiliate_url": str(url),
        "in_stock": to_bool_stock(pick(rec, "instock", "in_stock", "stock", "stock_status", "availability",
                                       "is_in_stock", "stockstatus")),
    }
