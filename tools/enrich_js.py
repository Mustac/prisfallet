#!/usr/bin/env python3
"""Print a browser snippet that reads key specs + rating from each product page of one shop.
Run the snippet on that shop's site; it stores lines 'key|rating|reviews|spec;spec;spec' in localStorage.enr."""
import json, sys, os
shop = sys.argv[1]
data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "manual-deals.json"), encoding="utf-8"))
urls = [d["url"] for d in data["deals"] if d["shop"] == shop]
js = r"""const U=%s;const out=[];for(const u of U){try{const h=await (await fetch(u)).text();const r=h.match(/"ratingValue"\s*:\s*"?([\d.,]+)"?/);const c=h.match(/"(?:reviewCount|ratingCount)"\s*:\s*"?(\d+)"?/);const d=new DOMParser().parseFromString(h,'text/html');let sp=[];for(const ul of d.querySelectorAll('ul')){const li=[...ul.querySelectorAll(':scope>li')].map(l=>l.textContent.replace(/\s+/g,' ').trim()).filter(t=>t&&t.length<=80);if(li.length>=3&&li.length<=8&&!li.some(t=>/Finn butikk|Kundeservice|Levering|Logg inn|Gavekort|Retur/i.test(t))){sp=li.slice(0,4);break}}const key=u.replace(/\/$/,'').split('/').pop();out.push([key,r?r[1].replace(',','.'):'',c?c[1]:'',sp.join(';')].join('|'))}catch(e){out.push(u+'|||')}}localStorage.enr=out.join('\n');out.length+' done, '+out.filter(l=>l.split('|')[1]).length+' rated, '+out.filter(l=>l.split('|')[3]).length+' with specs'""" % json.dumps([u.split("://",1)[1].split("/",1)[1] and "/"+u.split("://",1)[1].split("/",1)[1] for u in urls])
print(js)
