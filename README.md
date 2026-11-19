# Kupp.no – feed version

This is the legal, affiliate-feed version of Kupp.no. It does **not** scrape shop websites. All products, prices and photos come from the official product feeds that shops publish through affiliate networks, and every shop link is an affiliate link (annonselenke).

The old scraped site (github.com/Mustac/kupp-no) is left untouched.

## Try it now (sample data)

Double-click **run-demo.bat**. It builds the site from the sample feeds in `tests/fixtures` and opens it at http://localhost:8000. A yellow bar says the deals are sample data.

Python 3.10 or newer is needed. Nothing else has to be installed.

## How it works

```
affiliate feeds ──> scripts/update_deals.py ──> data/deals.json ──> index.html
                         │
                         └─> data/price-history.json   (our own 30-day price log)
```

1. Each source in `scripts/adapters/networks.py` reads its key or feed link from an environment variable. **If the key is empty, the source is skipped.** You can switch sources on one at a time as accounts get approved.
2. Every feed (XML, CSV or JSON, also zipped or gzipped) is mapped onto one shape.
3. Each product's price is added to `data/price-history.json`. Entries older than about 35 days are removed.
4. A product is kept only if it is **in stock** and **at least 30% off**. Discounts over 90% are dropped as feed errors.
5. The discount is measured against:
   * `verified_30d_low` – the lowest price **we** recorded in the 30 days before today. It is used only once we have followed the product for 30 days. Label: "Laveste pris siste 30 dager".
   * otherwise `feed_before_price` – the before-price the shop puts in its feed. Label: "Førpris (butikkens oppgitte)". This is **never** called the 30-day low.
6. Affiliate links are saved exactly as the network gives them, tracking parameters included. Images are linked, never downloaded or re-hosted.

### Output format (`data/deals.json` → `deals[]`)

| field | meaning |
|---|---|
| id | stable id (network + shop + SKU) |
| shop, source_network | e.g. "Komplett", "adtraction" |
| title, brand, category | category is one of the site's subcategory ids |
| current_price | price now (NOK) |
| feed_before_price | the shop's own before-price from the feed, or null |
| verified_30d_low | our 30-day lowest price, or null until we have 30 days |
| discount_percent | whole number |
| price_basis | "verified_30d_low" or "feed_before_price" |
| image_url, affiliate_url | from the feed, unchanged |
| in_stock, last_seen | always true / today's date |

## Connecting the networks

Put the values in **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret**. For a list, put one entry per line in the format `Shop name|link`.

| Secret | Where you get it | Status |
|---|---|---|
| `ADTRACTION_FEED_URLS` | Adtraction dashboard → the programme (Komplett, NetOnNet, Kjell & Co …) → Product feeds → copy the feed link | Easiest route. Recommended. |
| `ADTRACTION_TOKEN`, `ADTRACTION_CHANNEL_ID`, `ADTRACTION_PROGRAMS` | Adtraction → Account → API. Programs as `Komplett\|programId` | Optional. Adtraction says product feeds are in **API v3**, but I could not read the exact v3 path without an account. Check it in their docs and set `ADTRACTION_API_BASE` if needed. |
| `AWIN_FEED_URL` | Awin → Toolbox → Create-a-Feed → choose Lekmer (and others), CSV, gzip → copy the download link | Standard Awin feature. |
| `DAISYCON_FEED_URLS` | Daisycon → Material → Product feeds → Coolshop NO / avXperten NO → copy the feed link | Standard Daisycon feature. |
| `KELKOO_TOKEN` | Kelkoo Group publisher account → API token | Endpoint checked: `api.kelkoogroup.net/publisher/shopping/v2/feeds/offers?country=no`. Which Norwegian shops it covers depends on your account. |
| `PRISJAKT_CLIENT_ID`, `PRISJAKT_CLIENT_SECRET`, `PRISJAKT_REF` | Apply to Prisjakt for a Partner Search API key and a RefID | The real API is `api.schibsted.com/prisjakt/partner-search` (the `api.pj.nu` address in the original spec is wrong). The licence requires you to show that data comes from Prisjakt and link to them. The exact deals path is unconfirmed: set `PRISJAKT_DEALS_PATH` from their docs. |

Then go to **Actions → Update deals → Run workflow** to test it. After that it runs by itself every day at 04:00 UTC and commits the new `data/deals.json`.

### Running live on this PC instead

Copy `.env.example` to `.env`, fill in the values (several feeds on one line, separated by commas) and double-click **run-live.bat**. Never commit `.env`.

## Legal checklist (Norway)

* **Advertising must be marked** (markedsføringsloven § 3): the bar at the top says "Annonse / Inneholder annonselenker", and every shop button says "Se tilbud (annonselenke)". The links have `rel="sponsored"`.
* **Before-prices** (prisopplysningsforskriften): a shop's announced discount must be measured against its lowest price in the last 30 days. We can only confirm that ourselves after 30 days of history, so until then we say "the shop's stated before-price".
* **Network terms**: most programmes forbid bidding on brand names and some forbid showing vouchers. Read each programme's terms when you join.
* **Images and texts** may only be used as the feed licence allows. We link the images; we don't copy them.

## Files

```
index.html                     the website (one file)
data/deals.json                built every day
data/price-history.json        our 30-day price log
scripts/update_deals.py        the daily job
scripts/adapters/networks.py   one function per network
scripts/adapters/feeds.py      reads XML / CSV / JSON feeds
scripts/adapters/common.py     download, unzip, price parsing
scripts/classify.py            puts products in the site's categories
tests/                         python -m unittest discover tests
.github/workflows/update-deals.yml   daily GitHub job
run-demo.bat / run-live.bat    for Windows
```

## Publishing

Make a new GitHub repo (for example `kupp-feeds`), push this folder, then turn on GitHub Pages (Settings → Pages → Branch `main`, folder `/`). Add the secrets above, then run the workflow.
