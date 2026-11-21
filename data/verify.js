window.__verify = async (shop, src, conc = 3, delay = 250, start = 0) => {
  const all = (await (await fetch(src + "/data/manual-deals.json", {cache: "no-store"})).json()).deals.filter(d => d.shop === shop);
  const tok = s => (s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]{3,}/g) || []);
  const res = {ok: 0, notitle: 0, bad: []}; window.__vr = {done: 0, total: all.length, res};
  let i = start, stop = false; window.__vr.done = start;
  const one = async d => {
    const u = d.url.replace(/^https:\/\/[^/]+/, location.origin);
    let r;
    try { r = await fetch(u, {redirect: "follow", credentials: "omit"}); } catch (e) { res.bad.push([d.url, "fetch-error"]); return; }
    if (r.status === 403 || r.status === 429) { stop = true; res.bad.push([d.url, "blocked " + r.status]); return; }
    if (r.status !== 200) { res.bad.push([d.url, "status " + r.status]); return; }
    if (new URL(r.url).pathname === "/") { res.bad.push([d.url, "redirect-home"]); return; }
    const rd = r.body.getReader(); let h = "", n = 0; const dec = new TextDecoder();
    while (n < 400000) { const {value, done} = await rd.read(); if (done) break; h += dec.decode(value, {stream: true}); n += value.length;
      if (/<\/head>/i.test(h) && /og:title|<title/i.test(h)) break; }
    try { rd.cancel(); } catch (e) {}
    const cands = [];
    for (const rx of [/property=["']og:title["'][^>]*content=["']([^"']+)/i, /content=["']([^"']+)["'][^>]*property=["']og:title/i, /<title[^>]*>([^<]+)/i, /<h1[^>]*>([\s\S]{0,300}?)<\/h1>/i])
      { const m = h.match(rx); if (m) cands.push(m[1].replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#\d+;/g, " ")); }
    const a = tok(d.title);
    let best = 0, pt = cands[0] || "";
    for (const c of cands) { const b = new Set(tok(c)); const hit = a.filter(x => b.has(x)).length / Math.max(1, a.length); if (hit > best) { best = hit; pt = c; } }
    const hit = best;
    if (!cands.length || tok(cands.join(" ")).length < 2) { res.notitle++; res.ok++; }
    else if (hit < 0.5) res.bad.push([d.url, "title " + Math.round(hit * 100) + "% | " + pt.slice(0, 80)]);
    else res.ok++;
  };
  const work = async () => { while (i < all.length && !stop) { const d = all[i++]; await one(d); window.__vr.done++; await new Promise(r => setTimeout(r, delay)); } };
  await Promise.all(Array.from({length: conc}, work));
  window.__vr.finished = true; window.__vr.stopped = stop;
  localStorage.pfverify = JSON.stringify(res);
};
