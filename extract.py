#!/usr/bin/env python3
"""Pull the copy out of the client's plain HTML drafts into one JSON file.

His drafts are all the same shape: kicker line, h1, three intro paragraphs,
an FAQ section, a call CTA, plus a JSON-LD @graph in the head. We keep his
words and his slugs verbatim — only the presentation gets rebuilt.
"""
import glob
import html
import json
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'client-pages')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'content.json')


def one(pattern, text, flags=re.S):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ''


def clean(s):
    """Drop inline tags, collapse whitespace, keep the text as he wrote it."""
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


pages = []
for path in sorted(glob.glob(os.path.join(SRC, '*.html'))):
    raw = open(path, encoding='utf-8').read()
    head, body = raw.split('</head>', 1)
    main = one(r'<main>(.*)</main>', body)

    canonical = one(r'rel="canonical"\s+href="([^"]+)"', head)
    slug = canonical.rstrip('/').rsplit('/', 1)[-1]

    faq = []
    for q, a in re.findall(r'<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', main, re.S):
        faq.append({'q': clean(q), 'a': clean(a)})

    # The three lead paragraphs sit above the FAQ section.
    above = main.split('<section', 1)[0]
    paras = [clean(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', above, re.S)]

    schema = one(r'<script type="application/ld\+json">(.*?)</script>', head)

    pages.append({
        'file': os.path.basename(path),
        'slug': slug,
        'canonical': canonical,
        'title': html.unescape(one(r'<title>(.*?)</title>', head)),
        'metaDesc': one(r'name="description"\s+content="([^"]+)"', head),
        'kicker': html.unescape(clean(one(r'letter-spacing:\.05em[^"]*">(.*?)</div>', main))),
        'h1': html.unescape(clean(one(r'<h1[^>]*>(.*?)</h1>', main))),
        'paras': [html.unescape(p) for p in paras],
        'faq': [{'q': html.unescape(f['q']), 'a': html.unescape(f['a'])} for f in faq],
        'schema': json.loads(schema) if schema else None,
    })

# Order the way he numbered them: "Page 1", "page 2", ... not lexically.
pages.sort(key=lambda p: int(re.search(r'(\d+)', p['file']).group(1)))

json.dump(pages, open(OUT, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print('wrote %s (%d pages)' % (OUT, len(pages)))
for p in pages:
    print('  %-2s %-38s %d paras, %d faq' %
          (re.search(r'(\d+)', p['file']).group(1), p['slug'], len(p['paras']), len(p['faq'])))
