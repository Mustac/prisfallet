"""Shared helpers for all feed adapters: downloading, unpacking and reading prices."""
import gzip
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile

USER_AGENT = "PrisfalletBot/1.0 (+https://prisfallet.no/)"


def http_get(url, headers=None, timeout=60, retries=3, data=None, method=None):
    """Download a URL and return bytes. Retries on network errors and 5xx/429."""
    hdrs = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    hdrs.update(headers or {})
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs, data=data, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return unpack(body)
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        time.sleep(2 ** attempt * 2)
    raise last


def unpack(body: bytes) -> bytes:
    """Feeds may arrive gzipped or zipped. Return the plain content."""
    if body[:2] == b"\x1f\x8b":
        return gzip.decompress(body)
    if body[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            name = next(n for n in z.namelist() if not n.endswith("/"))
            return z.read(name)
    return body


def to_price(value):
    """'1 299,00 NOK' / '1299.00' / 1299 -> 1299.0 (None if not a price)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    s = str(value).replace(" ", " ").replace(" ", " ").strip()
    s = re.sub(r"[^\d,.\s-]", "", s).strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:            # 1.299,00 or 1,299.00
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = head.replace(",", "") + ("." + tail if len(tail) in (1, 2) else tail)
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def to_bool_stock(value, default=True):
    """Read in-stock flags such as 'yes', 'in stock', '1', 'true', 'på lager', '0'."""
    if value is None or value == "":
        return default
    s = str(value).strip().lower()
    if s in ("0", "false", "no", "nei", "out of stock", "out_of_stock", "utsolgt", "ikke på lager", "soldout", "sold out"):
        return False
    if re.fullmatch(r"\d+", s):
        return int(s) > 0
    return True


def pick(record: dict, *names, default=None):
    """First non-empty value among several possible field names (case-insensitive)."""
    low = {k.lower(): v for k, v in record.items()}
    for n in names:
        v = low.get(n.lower())
        if v not in (None, "", [], {}):
            return v
    return default


def parse_entries(raw: str):
    """'Shop name|https://feed-url' entries, one per line or comma separated."""
    out = []
    for part in re.split(r"[\n,]+", raw or ""):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            shop, url = part.split("|", 1)
            out.append((shop.strip(), url.strip()))
        else:
            out.append(("", part))
    return out


def load_json(body: bytes):
    return json.loads(body.decode("utf-8-sig"))
