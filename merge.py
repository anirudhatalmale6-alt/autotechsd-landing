#!/usr/bin/env python3
"""Fold the client's expanded copy (AUTOTECHSD.html) into content.json.

He sent the 10 pages twice. The first set was ~90 words each with the SEO
metadata; the second set is the same 10 pages rewritten at 370-510 words, but
with no <head> — it is a preview mock-up, not a page.

So: metadata and canonical URLs come from the first set, all the visible words
come from the second, and the FAQPage schema is REBUILT from the new questions
so the structured data still matches what a visitor actually sees on the page.
That last part matters — Google treats FAQ markup that doesn't appear in the
page body as a violation.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(ROOT, 'data', 'content.json')
EXPANDED = os.path.join(ROOT, 'data', 'expanded.json')
OUT = os.path.join(ROOT, 'data', 'content.json')

# His own preview flags this as an industry claim he could not verify. A hard
# percentage about crash safety is not something to publish on a repair shop's
# site without a source, so the sentence keeps the safety point and drops the
# number. Told him; he can put the figure back if he has a citation.
CLAIM_FIX = (
    "Your vehicle's windshield accounts for up to 45% of structural cabin "
    "strength during a rollover accident and provides critical backing support "
    "for airbag deployment.",
    "Your windshield is a structural part of the vehicle — it helps support the "
    "roof in a rollover and gives the passenger airbag something to push "
    "against as it deploys.",
)

NAPA_FAQ = {
    'q': 'What warranty comes with my repair at Auto Tech Specialists?',
    'a': 'We back our workmanship with a 12-month/12,000-mile local warranty. As a '
         'certified NAPA AutoCare Center, qualifying repairs are also covered FREE by '
         'the NAPA AutoCare Peace of Mind Nationwide Warranty for 24 months/24,000 miles.',
}


def split_intro(intro):
    """Hero sub-heading gets the opening sentence; the body gets the rest.

    Splitting rather than repeating — the intro is now a full paragraph, too
    long to sit under an <h1>, and showing it in both places would read as a
    duplicate.
    """
    parts = re.split(r'(?<=[.!?])\s+', intro.strip())
    return parts[0], ' '.join(parts[1:]).strip()


def main():
    orig = {p['slug']: p for p in json.load(open(ORIG, encoding='utf-8'))}
    exp = json.load(open(EXPANDED, encoding='utf-8'))

    out = []
    for e in exp['pages']:
        slug = e['slug']
        o = orig[slug]

        intro = e['intro'].replace(*CLAIM_FIX)
        hero_sub, body_open = split_intro(intro)

        faq = [{'q': q, 'a': a} for q, a in e['faqs']]
        if e.get('napaFaq'):
            faq.append(dict(NAPA_FAQ))

        sections = []
        for s in e.get('sections', []):
            sections.append({
                'h': s['h'],
                'paras': list(s['p']) if isinstance(s.get('p'), list) else ([s['p']] if s.get('p') else []),
                'list': list(s.get('list') or []),
            })

        # Keep the org + service blocks, refresh what the page now actually says.
        schema = json.loads(json.dumps(o['schema']))
        for node in schema['@graph']:
            if node.get('@type') == 'Service':
                node['name'] = e['h1']
                node['description'] = intro
            elif node.get('@type') == 'FAQPage':
                node['mainEntity'] = [
                    {'@type': 'Question', 'name': f['q'],
                     'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
                    for f in faq
                ]

        out.append({
            'slug': slug,
            'canonical': o['canonical'],
            'title': o['title'],
            'metaDesc': o['metaDesc'],
            'kicker': o['kicker'],
            'tab': e['tab'],
            'h1': e['h1'],
            'heroSub': hero_sub,
            'bodyOpen': body_open,
            'sections': sections,
            'signsH': e.get('signsH', ''),
            'signs': list(e.get('signs') or []),
            'faq': faq,
            'warranty': exp['WARRANTY_BANNER'],
            'schema': schema,
        })

    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    for p in out:
        n = len(p['heroSub'].split()) + len(p['bodyOpen'].split())
        for s in p['sections']:
            n += len(s['h'].split()) + sum(len(x.split()) for x in s['paras'])
            n += sum(len(x.split()) for x in s['list'])
        n += sum(len(x.split()) for x in p['signs'])
        n += sum(len(f['q'].split()) + len(f['a'].split()) for f in p['faq'])
        print('%4d words  %-38s sections:%d signs:%d faq:%d' % (
            n, p['slug'], len(p['sections']), len(p['signs']), len(p['faq'])))


if __name__ == '__main__':
    main()
