# Daily hand-picked deals (until affiliate networks approve)

Rules (from Marijan): up to 25 deals per shop, at least 30 % off, in stock online, priority laptops,
headphones, TV, phones, tablets, gaming, watches ("hit stuff"). Direct link to the product page.
No Prisjakt links or Prisjakt price history. Every deal must have a real picture (the shop's own
image, linked, never downloaded); deals without a picture are hidden automatically.
Small, hand-picked selection read from visible campaign pages only — no bulk catalogue pulls
from shop APIs (that was refused once as unauthorized access; don't try again).

Daily refresh = re-collect each shop and REPLACE its list (add_deals.py), so a product whose
discount is gone simply drops out. When a card/page says how long the offer lasts ("Tilbudet
gjelder 11.11 - 30.11", "gyldig t.o.m 30.11"), store it as "until" (YYYY-MM-DD, 6th field of
enrich.py): the build and the page both hide the deal after that day.

Files: data/manual-deals.json (source), tools/add_deals.py (replace one shop's deals),
tools/enrich.py (specs, rating, img), scripts/update_deals.py (build deals.json; drops deals
not re-checked within 48 h). Then commit + push; Cloudflare deploys in ~1 min.

## Per shop (all in his Chrome; output of javascript_tool is cut at ~1000 chars and lines with
## query strings are blocked, so store results in localStorage and print in chunks)
- Elkjøp: /kampanje/black-friday/{data-og-kontor,tv-lyd,mobil-og-nettbrett,gaming}. Card text has
  "Pris X kr" / "Før X kr" / "nettlager". Short link /product/<id>. Product page HTML has
  aggregateRating + first <ul> = 3 key specs. Image: /image/<dv_web code>/<id>/p.jpg (og:image).
- Power: /kampanje/blackfriday/{pc-og-mac,hodetelefoner,tv,mobiltelefoner,nettbrett,smartklokker}/.
  pwr-landscape-product-item: "Spar S,- P NOK" -> before = P+S; stock label "På nettlager".
  Product pages are SPA (no JSON-LD). Image from listing img (media.power-cdn.net). Skip RePOWER/renovert.
- Komplett: /kampanje/black-friday, decline cookies, click category tiles (main a[1..6]); cards are
  KOMPLETT-PRODUCT-CARD shadow DOM: "Førpris: B,-" and "SPAR S,-" -> P = B - S. Short link
  /product/<id>. Rating via regex on product HTML. Image: /product-media/b2c/en-us/1200/<id>.jpg
- NetOnNet: /art/black-friday + category filter links. "Pris å betale" / "Tidligere laveste pris".
  Product page JSON-LD has availability + rating; og:image.
- Proshop: /Black-Friday-{Datamaskin-Skriver-Tilbehoer,Mobil-Tablet,Tv-Lyd-Foto,Spill-Konsoller,Hardware-Gaming}.
  li.site-productlist-item: "Ord. pris" + price, "På lager". Image /Images/915x900/<file> (og:image).
- Kjell: /no/black-friday/{lyd--bilde,mobilt,videospill--gaming,smarte-hjem}. Two prices "X,-".
  Short link /no/p/<slug-pNNNNN>. JSON-LD availability + rating; og:image (cdn-cgi/image/...).
- XXL: /kampanje (scroll). "P,-", "Førpris", "B,-", "På lager online". og:image cdn.xxl.no/filespin/<id>.
- Jollyroom: /blackweek/blackweek-{leker,barnevogner,bilstoler,babyutstyr}. "X kr" + "Tidl. pris".
  Pages are client-rendered: image from listing img data-src (jollyroom.se/storage/...).
- Not done yet: Clas Ohlson, Maxkjøp, Lampegiganten, Kicks, Lyko, Lekekassen, Lekmer, Babyshop,
  Outnorth, Stormberg. Specs missing for Komplett, Power, Proshop, XXL, Jollyroom.

## Lekekassen (added 2026-11-20)
- Listing: /black-november (Magento). Fetch `/black-november?p=N&product_list_limit=48` in the browser and parse `li.product-item`.
- Price: `[data-price-type=finalPrice]` / `[data-price-type=oldPrice]` `data-price-amount` (the visible text has other numbers).
- Image: the img `data-src` (d189539ycils2q.cloudfront.net/media/catalog/product/cache/<hash>/…). In stock = has a `tocart` button.

## Power, more categories (2026-11-20)
- Also collect /kampanje/blackfriday/{hvitevarer,kjoekken,stoevsugere,kjoekkenmaskiner,skjoennhet-og-velvaere}/ and load with `tools/load_shop.py Power --append`.
- Bad listing titles like "MONTERING: DIREKTE PÅ DØR" → use the name from the spec lines or the URL slug.

## tools/load_shop.py
- Tab-separated: title, brand, price, before, url, img, until, sub, specs(;). Replaces a shop's list; `--append` keeps the shop's other deals.
- Barn category subs: lego, toys, strollers (vogner/triller/vognpose), carseats (bilstol/beltestol), baby (babyutstyr: matstol, babygym, babycall...).

## More shops' listing methods (20 Nov evening)
- Elkjøp campaign pages paginate as /kampanje/black-friday/<cat>/page-N (48 per page); `__es(g)` from localStorage.exsrc. Ratings appear as the first "spec" line (e.g. "4.5").
- Power: /kampanje/blackfriday/{pc-og-mac,skjermer,tv,hodetelefoner,mobiltelefoner,smartklokker,nettbrett,gaming,lydplanker-og-hoeyttalere,datatilbehoer}/
- Komplett: /kampanje/black-friday?query=+&list_view=grid&kom__collections=<PC og tilbehør|lyd og bilde|Mobil tablets og klokker|Datautstyr|Gaming>&categoryPages=<id>;
  cards render only when scrolled into view (scrollIntoView each card). Text has "P,- Spar S,- Førpris: B,-" and "Tilbudet gjelder fra .. til dd.mm.yy".
- NetOnNet: /art/black-friday?afc_categoryTree.lvl0=<Data og nettbrett|Lyd|Gaming|Mobil og smartklokker>[&afc_categoryTree.lvl1=<lvl0> > Laptoper]; <article> tiles, "Pris å betale"/"Tidligere laveste pris", buyable = "Legg i handlevogn". Paging param doesn't work: use subcategory filters.
- Proshop: fetch /<Black-Friday-...>?pn=N, parse li.site-productlist-item with a text-node walker (DOMParser docs have no innerText). HEAD gives false 404s: check links with GET.
- Kjell: /no/black-friday/{lyd--bilde,mobilt,videospill--gaming}; stock + rating from product page JSON-LD (InStock, ratingValue); og:image.
- Laptop specs matter for the RAM/CPU/GPU/storage filter: always fill specs (CPU; "16 GB RAM, 512 GB SSD"; GPU) for laptops.

## Full sale listings (since 21 Nov) — the daily routine
Collect each shop's whole sale listing in his Chrome, save it as Downloads/pf-<shop>.json
(one download per tab: Chrome blocks a second automatic download in the same tab, so save from a
fresh tab opened on the shop's /robots.txt, reading the data from that origin's localStorage),
move it to Downloads/prisfallet-data/, stage it, then `tools/reimport.sh`.
- Elkjøp: iframe over /kampanje/black-friday/<cat>/page-N for each category; `__es` from localStorage.exsrc (pfx key).
- Power: iframe per /kampanje/blackfriday/<cat>/ + "Vis flere" clicks; `__pw`/`__pm` (pall2).
- NetOnNet: iframe over /no/art/art-category/black-friday?p=N (0-based); name = first leaf element in the product link, description = h2/h3 (nnall).
- Proshop: fetch /Black-Friday?pn=N + DOMParser; image is img data-src (lazy) or src; ~4 req/s gets 429 — keep it slower (psall).
- Jollyroom: iframe /blackweek/blackweek-{leker,barnevogner,bilstoler,babyutstyr}?page=N, tiles .product-item__inner,
  picture = img with /storage/ in data-src (NOT the colour swatch) (jrall).
- Lekekassen: fetch /black-november?p=N&product_list_limit=48, Magento li.product-item, data-price-amount.
- Extra Leker: fetch /leker-pa-tilbud?p=N&product_list_limit=48 (Magento), picture in img data-amsrc.
- Jula: /tilbud/?pl-pageSize=300 + scroll; title = p.text-md.font-bold; skip JulaClub-only prices.
- Biltema: /pristilbud/nedsatt-pris/ + click "Neste"; li.productEntity.
- XXL: /kampanje + click "Neste" (183 items); "Førpris" value is on the next line.
Quality gates (tools/import_listing.py): 30–75 % off, real https picture matching the shop's image host
(tools/shops.py), in stock, minimum saving/price, junk/badge titles skipped, category from
scripts/classify.py must agree with the shop's own category path (HINTS) or falls back to it, else dropped;
toy shops: everything stays in "Barn og leker". data/overrides.json = manual fixes (url -> sub or "drop").
Before deploy: tools/inspect.py (0 problems), tools/review.py (eyeball new titles per category),
picture check (Image() load of every deal on the preview) and link check (data/verify.js in each shop tab:
200 + page title matches our name; stop at 403/429 and resume slower with the start index).
Preview = branch `preview` -> https://preview.prisfallet.pages.dev ; production = merge to main.

## Komplett full listing (since 21 Nov)
- Collections: /kampanje/black-friday?query=+&list_view=grid&kom__collections=<C>&categoryPages=<id> for
  "PC og tilbehør"/10723 (g pc), "Mobil tablets og klokker"/10444 (mobil), Datautstyr/10000 (data), Gaming/10431 (gaming), "lyd og bilde"/10719 (tv).
- Extractor source is in localStorage.kxsrc on komplett.no: `eval(localStorage.kxsrc); __kx('<g>')`, poll window.__kr.
  It scrolls (infinite scroll) until the card count stops growing, then scrollIntoView each KOMPLETT-PRODUCT-CARD (shadow DOM,
  walk with __deep/__dt). Title = H3, desc = P (kept as specs only if it looks like specs). Price from KOMPLETT-PRODUCT-CARD-PRICE:
  "P,- Spar S,- Førpris: B,-" (P+S must equal B). KLUBB (member-price) cards are skipped. Results in localStorage.kxall.
- Save from komplett.no/robots.txt as pf-komplett.json. reimport.sh maps g -> hint (pc-og-mac, mobil, data, gaming, tv-lyd).
- Komplett-PC collection tops out at 25 %: not collected.

## Checks added 21 Nov
- data/img-overrides.json: url -> hand-checked working image (used when the listing image is broken).
- data/verify-new.json + verify.js accepting a .json src: verify only new/changed deals:
  `__verify(shop, "https://preview.prisfallet.pages.dev/data/verify-new.json", 2, 500)`.
- NetOnNet code-only titles ("TCL 98T8D") get " – <description>"; (KOMP)(REUR) stock codes are stripped.
