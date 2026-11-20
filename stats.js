// Anonymous page statistics for Prisfallet.no: only after the visitor accepts statistics in the cookie notice.
(function () {
  var self = /(^|\.)prisfallet\.(no|pages\.dev)$/;
  if (!self.test(location.hostname)) return;
  var w = innerWidth, dev = w < 768 ? "mobil" : w < 1100 ? "nettbrett" : "pc", r = "direct";
  try { if (document.referrer) { var h = new URL(document.referrer).hostname.replace(/^www\./, ""); r = self.test(h) ? "" : h; } } catch (e) {}
  function send(o) { o.dev = dev; try { navigator.sendBeacon("/api/log", new Blob([JSON.stringify(o)], { type: "application/json" })); } catch (e) {} }
  function go() { send({ t: "pv", c: location.pathname }); if (r) send({ t: "visit", r: r, c: location.pathname }); }
  var ok = false; try { ok = localStorage.getItem("pf-consent") === "yes"; } catch (e) {}
  if (ok) go(); else document.addEventListener("pf-consent-yes", go, { once: true });
})();
