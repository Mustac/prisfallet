"""Run with:  python -m unittest discover tests"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import update_deals as U                          # noqa: E402
from adapters import networks                    # noqa: E402
from adapters.common import to_price             # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


def offer(sku="1", now=500.0, before=1000.0, stock=True, shop="Testbutikk"):
    return {"shop": shop, "source_network": "adtraction", "sku": sku, "title": f"Produkt {sku}", "brand": "X",
            "category_text": "", "current_price": now, "before_price": before, "image_url": "",
            "affiliate_url": f"https://example.com/t?sku={sku}&aff=1", "in_stock": stock}


class Prices(unittest.TestCase):
    def test_norwegian_formats(self):
        self.assertEqual(to_price("1 299,00 NOK"), 1299.0)
        self.assertEqual(to_price("1.299,00"), 1299.0)
        self.assertEqual(to_price("12 490"), 12490.0)
        self.assertIsNone(to_price("0"))


class Sources(unittest.TestCase):
    def test_sources_without_keys_are_skipped(self):
        saved = dict(os.environ)
        try:
            for k in list(os.environ):
                if k.startswith(("ADTRACTION", "AWIN", "DAISYCON", "KELKOO", "PRISJAKT")):
                    del os.environ[k]
            for name, fn in networks.ALL.items():
                self.assertIsNone(fn(lambda m: None), name)
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_every_sample_feed_parses(self):
        offers, status = U.collect(FIX)
        nets = {o["source_network"] for o in offers}
        self.assertEqual(nets, {"adtraction", "awin", "daisycon", "kelkoo"})
        for o in offers:
            self.assertTrue(o["affiliate_url"].startswith("https://"))
            self.assertGreater(o["current_price"], 0)


class Rules(unittest.TestCase):
    today = "2026-11-17"

    def run_build(self, offers, history=None):
        for o in offers:
            o["id"] = U.offer_id(o)
        return U.build(offers, history or {}, self.today)

    def test_out_of_stock_dropped(self):
        self.assertEqual(self.run_build([offer(stock=False)]), [])

    def test_under_30_percent_dropped(self):
        self.assertEqual(self.run_build([offer(now=800, before=1000)]), [])

    def test_absurd_discount_dropped(self):
        self.assertEqual(self.run_build([offer(now=9, before=999)]), [])

    def test_no_before_price_and_no_history_dropped(self):
        self.assertEqual(self.run_build([offer(before=None)]), [])

    def test_feed_price_is_never_called_30_day_low(self):
        d = self.run_build([offer()])[0]
        self.assertEqual(d["price_basis"], "feed_before_price")
        self.assertIsNone(d["verified_30d_low"])
        self.assertEqual(d["feed_before_price"], 1000)

    def test_affiliate_link_kept_exactly(self):
        d = self.run_build([offer()])[0]
        self.assertEqual(d["affiliate_url"], "https://example.com/t?sku=1&aff=1")

    def test_schema(self):
        d = self.run_build([offer()])[0]
        self.assertEqual(set(d), {"id", "shop", "source_network", "title", "brand", "category", "current_price",
                                  "feed_before_price", "verified_30d_low", "discount_percent", "price_basis",
                                  "image_url", "affiliate_url", "in_stock", "last_seen"})


class History(unittest.TestCase):
    def test_30_day_low_only_after_30_days(self):
        o = offer(now=1000, before=None)
        o["id"] = U.offer_id(o)
        start = dt.date(2026, 10, 1)
        hist = {}
        for i in range(29):                       # 29 days at 1000 kr
            day = (start + dt.timedelta(days=i)).isoformat()
            U.update_history(hist, [dict(o)], day)
        day29 = (start + dt.timedelta(days=29)).isoformat()
        self.assertIsNone(U.verified_30d_low(hist[o["id"]], day29))
        day30 = (start + dt.timedelta(days=30)).isoformat()
        self.assertEqual(U.verified_30d_low(hist[o["id"]], day30), 1000)
        # on day 30 the price drops to 600 -> a verified 40% deal
        cheap = dict(o, current_price=600.0)
        U.update_history(hist, [cheap], day30)
        d = U.build([cheap], hist, day30)[0]
        self.assertEqual(d["price_basis"], "verified_30d_low")
        self.assertEqual(d["verified_30d_low"], 1000)
        self.assertEqual(d["discount_percent"], 40)

    def test_old_history_trimmed(self):
        o = offer()
        o["id"] = U.offer_id(o)
        hist = {}
        U.update_history(hist, [o], "2026-01-01")
        U.update_history(hist, [o], "2026-11-17")
        self.assertEqual(list(hist[o["id"]]["p"]), ["2026-11-17"])


class EndToEnd(unittest.TestCase):
    def test_demo_run_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = U.main(["--fixtures", FIX, "--out", tmp, "--today", "2026-11-17"])
            self.assertTrue(out["demo"])
            self.assertGreater(len(out["deals"]), 0)
            with open(os.path.join(tmp, "deals.json"), encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)["deals"]), len(out["deals"]))
            self.assertTrue(os.path.exists(os.path.join(tmp, "price-history.json")))


if __name__ == "__main__":
    unittest.main()
