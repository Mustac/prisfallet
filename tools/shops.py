"""Per-shop expectations used by the importer and the inspection: link host and picture URL pattern."""
import re
SHOPS = {
    "Elkjøp": ("elkjop.no", r"^https://www\.elkjop\.no/image/dv_web_[^/]+/[^/]+/p\.jpg$"),
    "Power": ("power.no", r"^https://media\.power-cdn\.net/images/.+/products/\d+/"),
    "Komplett": ("komplett.no", r"^https://www\.komplett\.no/product-media/"),
    "NetOnNet": ("netonnet.no", r"^https://(imagecontent|images)\.netonnet\.com/|^https://www\.netonnet\.no/GetFile/"),
    "Proshop": ("proshop.no", r"^https://www\.proshop\.no/Images/"),
    "Kjell & Company": ("kjell.com", r"^https://www\.kjell\.com/cdn-cgi/image/.+/productimages/"),
    "XXL": ("xxl.no", r"^https://cdn\.xxl\.no/filespin/[0-9a-f]{20,}"),
    "Lekekassen": ("lekekassen.no", r"^https://d189539ycils2q\.cloudfront\.net/media/catalog/product/"),
    "Jollyroom": ("jollyroom.no", r"^https://www\.jollyroom\.se/storage/.+\.(jpe?g|png|webp)$"),
    "Jula": ("jula.no", r"^https://assets\.cdn\.jula\.com/"),
    "Biltema": ("biltema.no", r"^https://productimages\.biltema\.com/v1/image/product/"),
    "Extra Leker": ("extra-leker.no", r"^https://www\.extra-leker\.no/media/catalog/product/"),
}
def img_ok(shop, img):
    s = SHOPS.get(shop)
    return bool(img) and (not s or re.search(s[1], img, re.I) is not None) and not re.search(r"placeholder|no[-_]?image|/colors/|swatch|logo", img, re.I)
