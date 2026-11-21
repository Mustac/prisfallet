#!/bin/bash
# Rebuild manual-deals.json from the latest saved shop listings (after a rule change or a new collection).
set -e
cd "$(dirname "$0")/.."
D=/mnt/user-data/uploads/Downloads/prisfallet-data
I="python3 tools/import_listing.py"
[ -f $D/pf-jula.json ] && $I Jula https://www.jula.no $D/pf-jula.json --minsave 40 --drop-other
[ -f $D/pf-biltema.json ] && $I Biltema https://www.biltema.no $D/pf-biltema.json --minsave 40 --drop-other
[ -f $D/pf-lekekassen.json ] && $I Lekekassen https://lekekassen.no $D/pf-lekekassen.json --kids --minsave 30 --minprice 49
[ -f $D/pf-extraleker2.json ] && $I "Extra Leker" https://www.extra-leker.no $D/pf-extraleker2.json --kids --minsave 30 --minprice 49
[ -f $D/pf-jollyroom2.json ] && python3 tools/convert.py jollyroom $D/pf-jollyroom2.json /tmp/in/jr.json && $I Jollyroom https://www.jollyroom.no /tmp/in/jr.json --kids --minsave 30 --minprice 49
[ -f $D/pf-elkjop.json ] && python3 tools/convert.py elkjop $D/pf-elkjop.json /tmp/in/ek.json && $I Elkjøp https://www.elkjop.no /tmp/in/ek.json --minsave 50 --minprice 99 --drop-other
[ -f $D/pf-power.json ] && python3 tools/convert.py power $D/pf-power.json /tmp/in/pw.json && $I Power https://www.power.no /tmp/in/pw.json --minsave 50 --minprice 99 --drop-other
[ -f $D/pf-xxl.json ] && $I XXL https://www.xxl.no $D/pf-xxl.json --minsave 50 --minprice 99 --drop-other
[ -f $D/pf-komplett.json ] && python3 -c "import json,sys;M={'pc':'pc-og-mac','mobil':'mobil','data':'data','gaming':'gaming','tv':'tv-lyd'};d=json.load(open(sys.argv[1]));[x.update(g=M.get(x.get('g'),x.get('g'))) for x in d];json.dump(d,open(sys.argv[2],'w'),ensure_ascii=False)" $D/pf-komplett.json /tmp/in/komplett.json && $I Komplett https://www.komplett.no /tmp/in/komplett.json --minsave 50 --minprice 99 --drop-other
for s in netonnet proshop; do
  [ -f $D/pf-$s.json ] && python3 -c "import json,sys;d=json.load(open(sys.argv[1]));json.dump(list(d.values()) if isinstance(d,dict) else d,open(sys.argv[2],'w'),ensure_ascii=False)" $D/pf-$s.json /tmp/in/$s.json
done
[ -f /tmp/in/netonnet.json ] && $I NetOnNet https://www.netonnet.no /tmp/in/netonnet.json --minsave 50 --minprice 99 --drop-other --desc
[ -f /tmp/in/proshop.json ] && $I Proshop https://www.proshop.no /tmp/in/proshop.json --minsave 50 --minprice 99 --drop-other
python3 tools/inspect.py | head -5
