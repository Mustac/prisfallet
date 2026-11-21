// Run in a tab on the shop's own site. Checks every deal link of that shop: page answers 200,
// stays on the shop, and the page title matches our product name. Reads only the page head.
// usage: __verify("Elkjøp", "https://preview.prisfallet.pages.dev")  -> progress in window.__vr
window.__verify = async (shop, src, conc = 3, delay = 250) => {
  const all = (await (await fetch(src + "/data/manual-deals.json", {cache: "no-store"})).json()).deals.filter(d => d.shop === shop);
  const tok = s => (s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]{3,}/g) || []);
  const res = {ok: 0, bad: []}; window.__vr = {done: 0, total: all.length, res};
  let i = 0, stop = false;
  const one = async d => {
    const u = d.url.replace(/^https:\/\/[^/]+/, location.origin);
    let r;
    try { r = await fetch(u, {redirect: "follow", credentials: "omit"}); } catch (e) { res.bad.push([d.url, "fetch-error"]); return; }
    if (r.status === 403 || r.status === 429) { stop = true; res.bad.push([d.url, "blocked " + r.status]); return; }
    if (r.status !== 200) { res.bad.push([d.url, "status " + r.status]); return; }
    if (new URL(r.url).pathname === "/" ) { res.bad.push([d.url, "redirect-home"]); return; }
    const rd = r.body.getReader(); let h = "", n = 0;
    while (n < 400000) { const {value, done} = await rd.read(); if (done) break; h += new TextDecoder().decode(value); n += value.length;
      if (/<\/head>/i.test(h) && /og:title|<title/i.test(h)) break; }
    try { rd.cancel(); } catch (e) {}
    const m = h.match(/property=["']og:title["'][^>]*content=["']([^"']+)/i) || h.match(/content=["']([^"']+)["'][^>]*property=["']og:title/i) || h.match(/<title[^>]*>([^<]+)/i);
    const pt = m ? m[1].replace(/&amp;/g, "&").replace(/&#\d+;/g, " ") : "";
    const a = tok(d.title), b = new Set(tok(pt));
    const hit = a.filter(x => b.has(x)).length / Math.max(1, a.length);
    if (!pt) res.bad.push([d.url, "no-title"]);
    else if (hit < 0.5) res.bad.push([d.url, "title " + Math.round(hit * 100) + "% | " + pt.slice(0, 80)]);
    else res.ok++;
  };
  const work = async () => { while (i < all.length && !stop) { const d = all[i++]; await one(d); window.__vr.done++; await new Promise(r => setTimeout(r, delay)); } };
  await Promise.all(Array.from({length: conc}, work));
  window.__vr.finished = true; window.__vr.stopped = stop;
  localStorage.pfverify = JSON.stringify(res);
};
"ok";
