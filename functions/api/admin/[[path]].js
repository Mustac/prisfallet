// Admin API for Prisfallet.no: setup, login (password + TOTP), logout and live stats.
// All responses are no-store. Everything except setup/login/status needs a valid session.
import {
  COOKIE, SESSION_DAYS, MAX_FAILS, LOCK_MINUTES, PBKDF2_ITER, hashPassword, verifyPassword, verifyTotp,
  base32Encode, randomBytes, makeSession, readSession, sessionCookie, timingSafeEqual,
} from "../../_lib/auth.js";

const json = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Robots-Tag": "noindex", ...headers },
  });

const SCHEMA = [
  "CREATE TABLE IF NOT EXISTS admin_auth (id INTEGER PRIMARY KEY CHECK (id = 1), pass_hash TEXT, salt TEXT, iter INTEGER, totp_secret TEXT, totp_last INTEGER DEFAULT -1, gen INTEGER DEFAULT 1, pending_totp TEXT, created INTEGER, reset_code TEXT, reset_at INTEGER, pending_pass TEXT, pending_salt TEXT)",
  "CREATE TABLE IF NOT EXISTS admin_attempts (ts INTEGER NOT NULL, ok INTEGER NOT NULL)",
];
async function ensureSchema(db) { for (const s of SCHEMA) await db.prepare(s).run(); }
const getAuth = (db) => db.prepare("SELECT * FROM admin_auth WHERE id = 1").first();

async function lockedOut(db) {
  const since = Date.now() - LOCK_MINUTES * 60000;
  const r = await db.prepare("SELECT COUNT(*) AS n FROM admin_attempts WHERE ok = 0 AND ts > ?").bind(since).first();
  return (r?.n || 0) >= MAX_FAILS;
}
const logAttempt = (db, ok) => db.prepare("INSERT INTO admin_attempts (ts, ok) VALUES (?, ?)").bind(Date.now(), ok ? 1 : 0).run();

async function body(request) {
  if (!(request.headers.get("Content-Type") || "").includes("application/json")) return null;
  const t = await request.text();
  if (t.length > 2000) return null;
  try { return JSON.parse(t); } catch (e) { return null; }
}

export async function onRequest(ctx) {
  const { request, env, params } = ctx;
  const db = env.DB;
  const route = (params.path || []).join("/");
  const method = request.method;
  if (!db) return json({ error: "Database not bound" }, 500);
  await ensureSchema(db);
  const auth = await getAuth(db);
  const configured = !!(auth && auth.pass_hash && auth.totp_secret);
  const secret = env.ADMIN_SESSION_KEY;

  // ----- status: is the admin set up, am I logged in? -----
  if (route === "status" && method === "GET") {
    const s = configured ? await readSession(secret, request.headers.get("Cookie"), auth.gen) : null;
    return json({ configured, loggedIn: !!s, setupPossible: !configured && !!env.ADMIN_SETUP_CODE });
  }

  // ----- one-time setup: setup code -> choose password -> confirm authenticator -----
  if (route === "setup/start" && method === "POST") {
    if (configured) return json({ error: "Already set up" }, 409);
    if (await lockedOut(db)) return json({ error: `Too many attempts. Try again in ${LOCK_MINUTES} minutes.` }, 429);
    const b = await body(request);
    if (!b || !env.ADMIN_SETUP_CODE || !timingSafeEqual(String(b.code || ""), env.ADMIN_SETUP_CODE)) {
      await logAttempt(db, false);
      return json({ error: "Wrong setup code" }, 403);
    }
    const pw = String(b.password || "");
    if (pw.length < 12) return json({ error: "Password must be at least 12 characters" }, 400);
    const { hash, salt, iter } = await hashPassword(pw);
    const totp = base32Encode(randomBytes(20));
    await db.prepare(
      "INSERT INTO admin_auth (id, pass_hash, salt, iter, pending_totp, created) VALUES (1, ?, ?, ?, ?, ?) " +
      "ON CONFLICT(id) DO UPDATE SET pass_hash = excluded.pass_hash, salt = excluded.salt, iter = excluded.iter, pending_totp = excluded.pending_totp, totp_secret = NULL"
    ).bind(hash, salt, iter, totp, Date.now()).run();
    const uri = `otpauth://totp/Prisfallet.no:admin?secret=${totp}&issuer=Prisfallet.no&algorithm=SHA1&digits=6&period=30`;
    return json({ secret: totp, uri });
  }

  if (route === "setup/confirm" && method === "POST") {
    if (configured) return json({ error: "Already set up" }, 409);
    const b = await body(request);
    if (!b || !env.ADMIN_SETUP_CODE || !timingSafeEqual(String(b.code || ""), env.ADMIN_SETUP_CODE)) {
      await logAttempt(db, false);
      return json({ error: "Wrong setup code" }, 403);
    }
    if (!auth || !auth.pending_totp) return json({ error: "Start the setup again" }, 400);
    const ctr = await verifyTotp(auth.pending_totp, b.totp);
    if (ctr < 0) return json({ error: "Code does not match. Check that the phone clock is correct." }, 400);
    await db.prepare("UPDATE admin_auth SET totp_secret = pending_totp, pending_totp = NULL, totp_last = ? WHERE id = 1").bind(ctr).run();
    const cookie = await makeSession(secret, auth.gen || 1);
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(cookie, SESSION_DAYS * 86400) });
  }

  // ----- password reset (hidden page /admin/reset/) -----
  // Only works after a reset code has been put in the database from the Cloudflare dashboard
  // (D1 console), and only for 60 minutes after that. Logs out every device when finished.
  if ((route === "reset/start" || route === "reset/confirm") && method === "POST") {
    if (!configured) return json({ error: "Not set up yet" }, 409);
    // No shared lockout here, so someone spamming the login page can't block a reset.
    // The reset code is long, random-ish, set by the owner and only valid for 60 minutes.
    const b = await body(request);
    const fresh = auth.reset_code && auth.reset_at && Date.now() - auth.reset_at < 60 * 60000;
    if (!b || !fresh || String(auth.reset_code).length < 12 || !timingSafeEqual(String(b.code || ""), String(auth.reset_code))) {
      await logAttempt(db, false);
      return json({ error: "Wrong or expired reset code" }, 403);
    }
    if (route === "reset/start") {
      const pw = String(b.password || "");
      if (pw.length < 12) return json({ error: "Password must be at least 12 characters" }, 400);
      const { hash, salt } = await hashPassword(pw);
      const totp = base32Encode(randomBytes(20));
      await db.prepare("UPDATE admin_auth SET pending_pass = ?, pending_salt = ?, pending_totp = ? WHERE id = 1").bind(hash, salt, totp).run();
      const uri = `otpauth://totp/Prisfallet.no:admin?secret=${totp}&issuer=Prisfallet.no&algorithm=SHA1&digits=6&period=30`;
      return json({ secret: totp, uri });
    }
    if (!auth.pending_totp || !auth.pending_pass) return json({ error: "Start the reset again" }, 400);
    const ctr = await verifyTotp(auth.pending_totp, b.totp);
    if (ctr < 0) return json({ error: "Code does not match. Check that the phone clock is correct." }, 400);
    await db.prepare(
      "UPDATE admin_auth SET pass_hash = pending_pass, salt = pending_salt, iter = ?, totp_secret = pending_totp, totp_last = ?, " +
      "pending_pass = NULL, pending_salt = NULL, pending_totp = NULL, reset_code = NULL, reset_at = NULL, gen = gen + 1 WHERE id = 1"
    ).bind(PBKDF2_ITER, ctr).run();
    await db.prepare("DELETE FROM admin_attempts").run();
    const cookie = await makeSession(secret, (auth.gen || 1) + 1);
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(cookie, SESSION_DAYS * 86400) });
  }

  // ----- login -----
  if (route === "login" && method === "POST") {
    if (!configured) return json({ error: "Not set up yet" }, 409);
    if (!secret) return json({ error: "Mangler ADMIN_SESSION_KEY" }, 500);
    if (await lockedOut(db)) return json({ error: `Too many attempts. Try again in ${LOCK_MINUTES} minutes.` }, 429);
    const b = await body(request);
    const pwOk = b ? await verifyPassword(String(b.password || ""), auth) : false;
    const ctr = pwOk ? await verifyTotp(auth.totp_secret, b.totp, Date.now(), auth.totp_last ?? -1) : -1;
    if (!pwOk || ctr < 0) {
      await logAttempt(db, false);
      return json({ error: "Wrong password or code" }, 401);
    }
    await logAttempt(db, true);
    await db.prepare("UPDATE admin_auth SET totp_last = ? WHERE id = 1").bind(ctr).run();
    const cookie = await makeSession(secret, auth.gen || 1);
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(cookie, SESSION_DAYS * 86400) });
  }

  // ----- everything below needs a session -----
  const session = configured ? await readSession(secret, request.headers.get("Cookie"), auth.gen) : null;
  if (!session) return json({ error: "Not logged in" }, 401);

  if (route === "logout" && method === "POST") {
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie("", 0) });
  }
  if (route === "logout-all" && method === "POST") {
    await db.prepare("UPDATE admin_auth SET gen = gen + 1 WHERE id = 1").run();
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie("", 0) });
  }

  if (route === "stats" && method === "GET") {
    const url = new URL(request.url);
    const days = Math.max(1, Math.min(395, parseInt(url.searchParams.get("days") || "30", 10) || 30));
    return json(await stats(db, days, url.origin));
  }

  return json({ error: "Unknown" }, 404);
}

// ---------- live statistics from the anonymous event log ----------
async function stats(db, days, origin) {
  const now = Date.now();
  const today = new Date(now).toISOString().slice(0, 10);
  const from = new Date(now - (days - 1) * 864e5).toISOString().slice(0, 10);
  const q = (sql, ...b) => db.prepare(sql).bind(...b).all().then((r) => r.results || []);

  const [daily, refs, devices, regions, countries, searches, zero, clicksDeal, clicksShop, clicksCat,
    viewsDeal, cats, filters, last] = await Promise.all([
    q("SELECT day, SUM(type='pv') pv, SUM(type='visit') visits, SUM(type='search') searches, SUM(type='view') views, SUM(type='click') clicks FROM events WHERE day >= ? GROUP BY day ORDER BY day", from),
    q("SELECT ref, COUNT(*) n FROM events WHERE type='visit' AND day >= ? GROUP BY ref ORDER BY n DESC LIMIT 15", from),
    q("SELECT device, COUNT(*) n FROM events WHERE type='pv' AND day >= ? AND device IS NOT NULL GROUP BY device ORDER BY n DESC", from),
    q("SELECT region, COUNT(*) n FROM events WHERE type='pv' AND day >= ? AND region IS NOT NULL GROUP BY region ORDER BY n DESC LIMIT 15", from),
    q("SELECT country, COUNT(*) n FROM events WHERE type='pv' AND day >= ? AND country IS NOT NULL GROUP BY country ORDER BY n DESC LIMIT 10", from),
    q("SELECT term, COUNT(*) n, MIN(n) results FROM events WHERE type='search' AND day >= ? AND term IS NOT NULL GROUP BY term ORDER BY n DESC LIMIT 40", from),
    q("SELECT term, COUNT(*) n FROM events WHERE type='search' AND day >= ? AND n = 0 AND term IS NOT NULL GROUP BY term ORDER BY n DESC LIMIT 25", from),
    q("SELECT deal, shop, COUNT(*) n FROM events WHERE type='click' AND day >= ? GROUP BY deal, shop ORDER BY n DESC LIMIT 20", from),
    q("SELECT shop, COUNT(*) n FROM events WHERE type='click' AND day >= ? GROUP BY shop ORDER BY n DESC LIMIT 20", from),
    q("SELECT cat, COUNT(*) n FROM events WHERE type='click' AND day >= ? GROUP BY cat ORDER BY n DESC", from),
    q("SELECT deal, shop, COUNT(*) n FROM events WHERE type='view' AND day >= ? GROUP BY deal, shop ORDER BY n DESC LIMIT 20", from),
    q("SELECT cat, COUNT(*) n FROM events WHERE type='cat' AND day >= ? GROUP BY cat ORDER BY n DESC", from),
    q("SELECT f, v, COUNT(*) n FROM events WHERE type='filter' AND day >= ? GROUP BY f, v ORDER BY n DESC LIMIT 30", from),
    q("SELECT MAX(ts) ts FROM events"),
  ]);

  // site health: deals file freshness
  let feed = null;
  try {
    const r = await fetch(origin + "/data/deals.json", { cf: { cacheTtl: 0 } });
    if (r.ok) {
      const d = await r.json();
      feed = { updated: d.updated, demo: !!d.demo, deals: (d.deals || []).length, shops: (d.shops || []).length, sources: d.sources };
    }
  } catch (e) { /* ignore */ }

  return { generated: now, today, from, days, daily, refs, devices, regions, countries, searches, zero,
    clicksDeal, clicksShop, clicksCat, viewsDeal, cats, filters, lastEvent: last[0]?.ts || null, feed };
}
