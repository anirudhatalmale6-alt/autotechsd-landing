#!/bin/sh
set -e
export CHROME_PATH=/home/freelancer6/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome
cd "$(dirname "$0")"
LH=./node_modules/.bin/lighthouse
python3 -m http.server 8797 --directory preview --bind 127.0.0.1 > lh-fleet-server.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8797/index.html)" = "200" ]; do sleep 1; done
slug=commercial-fleet-service-repair-san-diego
for form in mobile desktop; do
  if [ "$form" = desktop ]; then PRESET=desktop; else PRESET=perf; fi
  $LH "http://127.0.0.1:8797/$slug.html" --preset=$PRESET \
    --only-categories=performance,accessibility,best-practices,seo \
    --chrome-flags="--headless=new --no-sandbox" --output=json \
    --output-path="lhf-$form.json" --quiet > /dev/null 2>&1
  node -e "
    const c=require('./lhf-$form.json').categories;
    const s=['performance','accessibility','best-practices','seo'].map(k=>Math.round(c[k].score*100));
    console.log('$form'.padEnd(8), s.join(' / '), s.every(x=>x===100)?'':'  <-- CHECK');
  "
done
echo FLEET-LH-DONE
