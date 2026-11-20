// Anonymous page statistics for Prisfallet.no: no cookies, no IDs, nothing stored in the browser.
(function () {
  var self = /(^|\.)prisfallet\.(no|pages\.dev)$/;
  if (!self.test(location.hostname)) return;
  var w = innerWidth, dev = w < 768 ? "mobil" : w < 1100 ? "nettbrett" : "pc", r = "direct";
  try { if (document.referrer) { var h = new URL(document.referrer).hostname.replace(/^www\./, ""); r = self.test(h) ? "" : h; } } catch (e) {}
  function send(o) { o.dev = dev; try { navigator.sendBeacon("/api/log", new Blob([JSON.stringify(o)], { type: "application/json" })); } catch (e) {} }
  send({ t: "pv", c: location.pathname });
  if (r) send({ t: "visit", r: r, c: location.pathname });
})();
