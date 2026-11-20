// Anonymous usage log for Prisfallet.no (Cloudflare Pages Function + D1, free plan).
// Stores only: day, timestamp, event type, search term / product name, shop, category,
// result count and visitor country. No IP address, no user agent, no cookies, no IDs.

const TYPES = new Set(["search", "view", "click", "cat"]);
const ALLOWED_HOSTS = new Set(["prisfallet.no", "www.prisfallet.no", "prisfallet.pages.dev"]);

const clean = (v, max) =>
  typeof v === "string" ? v.replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max) || null : null;

export async function onRequestPost({ request, env, waitUntil }) {
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

    const now = new Date();
    const n = Number.isFinite(b.n) ? Math.max(0, Math.min(100000, Math.round(b.n))) : null;
    await env.DB.prepare(
      "INSERT INTO events (day, ts, type, term, deal, shop, cat, country, n) VALUES (?,?,?,?,?,?,?,?,?)"
    ).bind(
      now.toISOString().slice(0, 10),
      now.getTime(),
      b.t,
      b.t === "search" ? clean(b.q, 80)?.toLowerCase() ?? null : null,
      clean(b.d, 120),
      clean(b.s, 60),
      clean(b.c, 40),
      (request.cf && request.cf.country) || null,
      n
    ).run();
    // Retention: occasionally delete events older than 13 months (stated on /personvern).
    if (Math.random() < 0.002) {
      const cutoff = now.getTime() - 396 * 24 * 3600 * 1000;
      const del = env.DB.prepare("DELETE FROM events WHERE ts < ?").bind(cutoff).run();
      if (waitUntil) waitUntil(del); else await del;
    }
    return new Response(null, { status: 204 });
  } catch (e) {
    return new Response(null, { status: 204 });
  }
}

export async function onRequest() {
  return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
}
