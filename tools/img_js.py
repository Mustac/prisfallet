#!/usr/bin/env python3
"""Browser snippet: read each product page's own og:image (and rating/specs if missing) for one shop."""
import json, sys, os
shop = sys.argv[1]
data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json"), encoding="utf-8"))
urls = ["/" + d["url"].split("://", 1)[1].split("/", 1)[1] for d in data["deals"] if d["shop"] == shop]
print(r"""const U=%s;const out=[];for(const u of U){try{const h=await (await fetch(u)).text();const d=new DOMParser().parseFromString(h,'text/html');let im=(d.querySelector('meta[property="og:image"]')||{}).content||'';if(!im){for(const s of d.querySelectorAll('script[type="application/ld+json"]')){try{for(const o of [].concat(JSON.parse(s.textContent))){if(o.image){im=[].concat(o.image)[0];im=im.url||im}}}catch(e){}}}if(im&&im.startsWith('//'))im='https:'+im;const r=h.match(/"ratingValue"\s*:\s*"?([\d.,]+)"?/);const c=h.match(/"(?:reviewCount|ratingCount)"\s*:\s*"?(\d+)"?/);out.push([u,r?r[1].replace(/[.,]$/,''):'',c?c[1]:'',im])}catch(e){out.push([u,'','',''])}}window.__im=out;localStorage.img=JSON.stringify(out);out.length+' done, '+out.filter(x=>x[3]).length+' images, '+out.filter(x=>x[3]&&x[3].includes('?')).length+' with query'""" % json.dumps(urls))
