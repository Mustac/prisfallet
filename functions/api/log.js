// Anonymous usage log for Prisfallet.no (Cloudflare Pages Function + D1, free plan).
// Stores only coarse, non-identifying facts: day, timestamp, event type, search term /
// product name, shop, category, result count, country, region, device class
// (mobile/tablet/pc from screen width), referring site, and filter choices.
// No IP address, no user agent, no cookies, no visitor or session IDs.

const TYPES = new Set(["pv", "search", "view", "click", "cat", "visit", "filter"]);
const FILTERS = new Set(["sort", "min", "price", "brand", "shop"]);
const DEVICES = new Set(["mobil", "nettbrett", "pc"]);
const ALLOWED_HOSTS = new Set(["prisfallet.no", "www.prisfallet.no", "prisfallet.pages.dev"]);

const clean = (v, max) =>
  typeof v === "string" ? v.replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max) || null : null;

// Search words are free text: strip anything that looks like an email address or a
// phone/ID number so personal data never ends up in the log.
const scrubTerm = (q) => {
  const t = clean(q, 80);
  if (!t) return null;
  return t
    .toLowerCase()
    .replace(/[^\s@]+@[^\s@]+\.[^\s@]+/g, "[fjernet]")
    .replace(/(\+?\d[\d\s.-]{6,}\d)/g, "[fjernet]");
};

const refHost = (r) => {
  const t = clean(r, 80);
  if (!t) return null;
  return /^[a-z0-9.-]+$/i.test(t) ? t.toLowerCase() : null;
};

export async function onRequestPost({ request, env }) {
  try {
    const origin = request.headers.get("Origin") || request.headers.get("Referer") || "";
    let host = "";
    try { host = new URL(origin).hostname; } catch (e) { /* no origin */ }
    if (!ALLOWED_HOSTS.has(host) && !host.endsWith(".prisfallet.pages.dev")) {
      return new Response(null, { status: 204 });
    }
    const text = await request.text();
    if (text.length > 2000) return new Response(null, { status: 413 });
    const b = JSON.parse(text);
    if (!b || !TYPES.has(b.t)) return new Response(null, { status: 400 });
    if (b.t === "filter" && !FILTERS.has(b.f)) return new Response(null, { status: 400 });

    const now = new Date();
    const cf = request.cf || {};
    const n = Number.isFinite(b.n) ? Math.max(0, Math.min(100000, Math.round(b.n))) : null;
    await env.DB.prepare(
      "INSERT INTO events (day, ts, type, term, deal, shop, cat, country, n, region, device, ref, f, v) " +
      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ).bind(
      now.toISOString().slice(0, 10),
      now.getTime(),
      b.t,
      b.t === "search" ? scrubTerm(b.q) : null,
      clean(b.d, 120),
      clean(b.s, 60),
      clean(b.c, 40),
      cf.country || null,
      n,
      cf.country === "NO" ? clean(cf.region, 40) : null,
      DEVICES.has(b.dev) ? b.dev : null,
      b.t === "visit" ? refHost(b.r) : null,
      b.t === "filter" ? b.f : null,
      b.t === "filter" ? clean(b.v, 60) : null
    ).run();

    // Data is kept until the owner deletes it (anonymous, no personal data).
    return new Response(null, { status: 204 });
  } catch (e) {
    return new Response(null, { status: 204 });
  }
}

export async function onRequest() {
  return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
}
