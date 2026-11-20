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
