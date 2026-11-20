// Admin authentication helpers for Prisfallet.no (Cloudflare Pages Functions, WebCrypto only).
// Password: PBKDF2-SHA256. Second factor: TOTP (RFC 6238, SHA-1, 30 s, 6 digits).
// Session: HMAC-SHA256 signed cookie, HttpOnly + Secure + SameSite=Strict.

const enc = new TextEncoder();
export const COOKIE = "pf_admin";
export const SESSION_DAYS = 30;
export const PBKDF2_ITER = 20000;
export const MAX_FAILS = 5;
export const LOCK_MINUTES = 15;

export const b64u = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const unb64u = (s) => {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
};

export function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

export function randomBytes(n) {
  const a = new Uint8Array(n);
  crypto.getRandomValues(a);
  return a;
}

// ---------- password ----------
export async function hashPassword(password, saltB64, iter = PBKDF2_ITER) {
  const salt = saltB64 ? unb64u(saltB64) : randomBytes(16);
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: iter }, key, 256);
  return { hash: b64u(bits), salt: b64u(salt), iter };
}

export async function verifyPassword(password, rec) {
  const { hash } = await hashPassword(password, rec.salt, rec.iter);
  return timingSafeEqual(hash, rec.pass_hash);
}

// ---------- TOTP ----------
const B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
export function base32Encode(bytes) {
  let bits = 0, value = 0, out = "";
  for (const b of bytes) {
    value = (value << 8) | b; bits += 8;
    while (bits >= 5) { out += B32[(value >>> (bits - 5)) & 31]; bits -= 5; }
  }
  if (bits > 0) out += B32[(value << (5 - bits)) & 31];
  return out;
}
export function base32Decode(s) {
  s = s.replace(/=+$/, "").toUpperCase().replace(/\s+/g, "");
  let bits = 0, value = 0; const out = [];
  for (const c of s) {
    const i = B32.indexOf(c); if (i < 0) continue;
    value = (value << 5) | i; bits += 5;
    if (bits >= 8) { out.push((value >>> (bits - 8)) & 255); bits -= 8; }
  }
  return new Uint8Array(out);
}

export async function totpAt(secretB32, counter) {
  const key = await crypto.subtle.importKey("raw", base32Decode(secretB32), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const msg = new ArrayBuffer(8);
  const view = new DataView(msg);
  view.setUint32(0, Math.floor(counter / 2 ** 32));
  view.setUint32(4, counter >>> 0);
  const h = new Uint8Array(await crypto.subtle.sign("HMAC", key, msg));
  const o = h[h.length - 1] & 15;
  const code = (((h[o] & 127) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3]) % 1e6;
  return String(code).padStart(6, "0");
}

// Returns the matching counter (to block replays) or -1.
export async function verifyTotp(secretB32, code, nowMs = Date.now(), lastCounter = -1) {
  if (!/^\d{6}$/.test(String(code || ""))) return -1;
  const c = Math.floor(nowMs / 30000);
  for (const d of [0, -1, 1]) {
    const ctr = c + d;
    if (ctr <= lastCounter) continue;
    if (timingSafeEqual(await totpAt(secretB32, ctr), String(code))) return ctr;
  }
  return -1;
}

// ---------- session cookie ----------
async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
}
export async function makeSession(secret, gen) {
  const payload = b64u(enc.encode(JSON.stringify({ exp: Date.now() + SESSION_DAYS * 864e5, gen })));
  const sig = b64u(await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(payload)));
  return `${payload}.${sig}`;
}
export async function readSession(secret, cookieHeader, gen) {
  if (!secret || !cookieHeader) return null;
  const m = cookieHeader.split(/;\s*/).find((c) => c.startsWith(COOKIE + "="));
  if (!m) return null;
  const [payload, sig] = m.slice(COOKIE.length + 1).split(".");
  if (!payload || !sig) return null;
  const expect = b64u(await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(payload)));
  if (!timingSafeEqual(expect, sig)) return null;
  try {
    const p = JSON.parse(new TextDecoder().decode(unb64u(payload)));
    if (!p.exp || p.exp < Date.now()) return null;
    if (gen !== undefined && p.gen !== gen) return null; // logged out everywhere / password changed
    return p;
  } catch (e) { return null; }
}
export const sessionCookie = (value, maxAgeSec) =>
  `${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAgeSec}`;
