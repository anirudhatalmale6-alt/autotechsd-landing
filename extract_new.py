#!/usr/bin/env python3
"""Add the Fleet and Detailing pages to content.json.

These two arrived in a different shape from the first ten: full standalone HTML
documents with their own <head> and schema, and a much longer body — ten <h2>
sections on Fleet, a three-column pricing table on Detailing.

The body is flattened into a numbered list of blocks and RECIPE below says which
block goes where. That is deliberately explicit rather than clever: with only two
documents, a hand-checked index map is easier to audit than a parser guessing at
his heading hierarchy, and every string still comes out of his file verbatim —
nothing on these pages is retyped.

Run `python3 extract_new.py --blocks` to re-print the numbered list if his files
are ever resent, since the indices below refer to it.
"""
import json
import os
import re
import sys

from bs4 import BeautifulSoup, NavigableString

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'data', 'client-pages')
CONTENT = os.path.join(ROOT, 'data', 'content.json')

# Identical wording to the other ten. It is his own warranty text, and a warranty
# that is phrased three different ways across a site reads like three warranties.
WARRANTY = (
    'All repairs are backed by our 12-month/12,000-mile local warranty. As a '
    'certified NAPA AutoCare Center, qualifying repairs and services are also '
    'covered FREE by the NAPA AutoCare Peace of Mind Nationwide Warranty — '
    '24 months/24,000 miles, honored at more than 14,000 locations across the U.S.'
)

KICKER = 'KEARNY MESA, SAN DIEGO · EST. 1999 · ASE CERTIFIED'


def text_of(el):
    """Visible text, whitespace collapsed. bs4 has already decoded entities."""
    return re.sub(r'\s+', ' ', el.get_text()).strip()


def blocks(soup):
    """Flatten the body to ('h2'|'h3'|'p'|'ul'|'table', payload) in document order.

    <section> wrappers are transparent — he uses them on some blocks and not
    others, so they are not a reliable grouping level.
    """
    out = []

    def walk(node):
        for child in node.children:
            if isinstance(child, NavigableString):
                continue
            tag = child.name
            if tag == 'section':
                walk(child)
            elif tag in ('h1', 'nav', 'hr'):
                continue
            elif tag in ('h2', 'h3'):
                out.append((tag, text_of(child)))
            elif tag == 'p':
                # His inline "Call ... | Request ..." bars. The template already
                # puts call buttons in the hero and in the closing CTA.
                if 'hero-cta' in ' '.join(child.get('class') or []):
                    continue
                out.append(('p', text_of(child)))
            elif tag == 'ul':
                out.append(('ul', [text_of(li)
                                   for li in child.find_all('li', recursive=False)]))
            elif tag == 'table':
                out.append(('table', {
                    'head': [text_of(th) for th in child.select('thead th')],
                    'rows': [[text_of(td) for td in tr.find_all(['td', 'th'], recursive=False)]
                             for tr in child.select('tbody tr')],
                }))

    walk(soup.body)
    return out


# ---------------------------------------------------------------------------
# Which block goes where. Indices refer to the --blocks dump.
#
# 'drop' is not listed explicitly: anything not referenced here is left out, and
# in both files the leftovers are all the same thing — inline "call us / book
# now" blocks he wrote two or three times over. The template ends every page
# with exactly that CTA, so keeping his would print it three times on one page.
# ---------------------------------------------------------------------------
RECIPE = {
    'commercial-fleet-service-repair-san-diego': {
        'file': 'fleet-src.html',
        'glance': (0, 1),
        'intro': [5, 6],
        'sections': [
            {'h': 2, 'paras': [3, 4]},
            {'h': 7, 'paras': [8], 'list': 9},
            {'h': 10, 'paras': [11], 'list': 12},
            {'h': 13, 'paras': [14], 'list': 15},
            {'h': 16, 'paras': [17], 'list': 18},
            {'h': 19, 'list': 20},
            {'h': 21, 'paras': [22, 24], 'list': 23},
            {'h': 25, 'paras': [26], 'list': 27},
            {'h': 28, 'paras': [29]},
            {'h': 41, 'paras': [42, 43]},
        ],
        'faq': [(31, 32), (33, 34), (35, 36), (37, 38), (39, 40)],
        'ctaLead': 49,
        # Buried at the bottom of a CTA block he wrote, but it is the one line
        # that tells a fleet manager what to actually put in the enquiry. Moved
        # into the call card where it will be read.
        'asideNote': 47,
        'warranty': WARRANTY,
    },
    'auto-detailing-san-diego': {
        'file': 'detailing-src.html',
        'glance': (0, 1),
        'intro': [5],
        'sections': [
            {'h': 2, 'paras': [3, 4]},
            {'h': 6, 'table': 7},
            # His <h2>Package Descriptions</h2> is only a wrapper around two
            # <h3>s; the two packages carry the content, so they become the
            # sections and the empty wrapper is dropped.
            {'h': 9, 'paras': [10], 'list': 11},
            {'h': 12, 'paras': [13], 'list': 14},
            {'h': 15, 'list': 16},
        ],
        'faq': [(18, 19), (20, 21), (22, 23), (24, 25)],
        'ctaLead': None,
        # Detailing is not a repair, so the repair warranty does not belong on
        # this page — claiming a 12-month warranty on a wash would be wrong.
        'warranty': '',
        # The pricing caveat he wrote at the very bottom. It sits inside a CTA
        # block that gets dropped, and published prices must keep their caveat.
        'fineprint': 31,
    },
}


def glance_pairs(items):
    """'Facility: 19 service and repair bays' -> ('Facility', '19 service...')."""
    pairs = []
    for it in items:
        label, _, rest = it.partition(':')
        pairs.append([label.strip(), rest.strip()] if rest else ['', it])
    return pairs


def split_intro(intro):
    """First sentence goes under the <h1>; the rest opens the body column.

    Same treatment as the other ten. His intro is a full paragraph — too long to
    sit under a heading, and printing it in both places reads as a duplicate.
    """
    parts = re.split(r'(?<=[.!?])\s+', intro.strip())
    return parts[0], ' '.join(parts[1:]).strip()


def build(slug, cfg):
    soup = BeautifulSoup(open(os.path.join(SRC, cfg['file']), encoding='utf-8').read(),
                         'html.parser')
    bl = blocks(soup)

    def blk(i, kind):
        assert bl[i][0] == kind, 'block %d is %s, expected %s' % (i, bl[i][0], kind)
        return bl[i][1]

    gh, gl = cfg['glance']
    intro_paras = [blk(i, 'p') for i in cfg['intro']]
    hero_sub, first_rest = split_intro(intro_paras[0])

    sections = []
    for s in cfg['sections']:
        sec = {'h': blk(s['h'], 'h2') if bl[s['h']][0] == 'h2' else blk(s['h'], 'h3'),
               'paras': [blk(i, 'p') for i in s.get('paras', [])],
               'list': blk(s['list'], 'ul') if 'list' in s else [],
               'table': blk(s['table'], 'table') if 'table' in s else None}
        sections.append(sec)

    faq = [{'q': blk(q, 'h3'), 'a': blk(a, 'p')} for q, a in cfg['faq']]

    schema = json.loads(soup.find('script', type='application/ld+json').string)
    # The FAQ block in his schema is worded differently from the FAQ he actually
    # shows on the page — different questions on Detailing, different answers on
    # both. Google treats FAQ markup that does not match the visible page as a
    # violation, so the schema is rebuilt from what the visitor sees.
    for node in schema['@graph']:
        if node.get('@type') == 'FAQPage':
            node['mainEntity'] = [
                {'@type': 'Question', 'name': f['q'],
                 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
                for f in faq
            ]

    return {
        'slug': slug,
        'tab': slug,
        'title': soup.title.string.strip(),
        'metaDesc': soup.find('meta', attrs={'name': 'description'})['content'].strip(),
        'canonical': soup.find('link', rel='canonical')['href'].strip(),
        'kicker': KICKER,
        'h1': text_of(soup.find('h1')),
        'heroSub': hero_sub,
        'bodyOpen': ' '.join(x for x in [first_rest] + intro_paras[1:] if x),
        'glanceH': blk(gh, 'h2'),
        'glance': glance_pairs(blk(gl, 'ul')),
        'sections': sections,
        'signsH': '',
        'signs': [],
        'warranty': cfg['warranty'],
        'faq': faq,
        'ctaLead': blk(cfg['ctaLead'], 'p') if cfg['ctaLead'] is not None else '',
        'finePrint': blk(cfg['fineprint'], 'p') if 'fineprint' in cfg else '',
        'asideNote': blk(cfg['asideNote'], 'p') if 'asideNote' in cfg else '',
        'schema': schema,
    }


def main():
    if '--blocks' in sys.argv:
        for slug, cfg in RECIPE.items():
            soup = BeautifulSoup(open(os.path.join(SRC, cfg['file']), encoding='utf-8').read(),
                                 'html.parser')
            print('=== %s ===' % slug)
            for i, (k, p) in enumerate(blocks(soup)):
                if k == 'ul':
                    print('%2d ul    (%d) %s' % (i, len(p), p[0][:70]))
                elif k == 'table':
                    print('%2d table %dx%d' % (i, len(p['head']), len(p['rows'])))
                else:
                    print('%2d %-5s %s' % (i, k, p[:95]))
        return

    pages = json.load(open(CONTENT, encoding='utf-8'))
    pages = [p for p in pages if p['slug'] not in RECIPE]      # idempotent re-run
    for slug, cfg in RECIPE.items():
        pages.append(build(slug, cfg))

    # Every page carries the same keys, so the generator never has to guess.
    for p in pages:
        p.setdefault('glanceH', '')
        p.setdefault('glance', [])
        p.setdefault('ctaLead', '')
        p.setdefault('finePrint', '')
        p.setdefault('asideNote', '')
        for sec in p['sections']:
            sec.setdefault('table', None)

    json.dump(pages, open(CONTENT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('content.json now holds %d pages' % len(pages))
    for p in pages[-2:]:
        print('  %-45s %d sections, %d FAQ, warranty=%s'
              % (p['slug'], len(p['sections']), len(p['faq']), bool(p['warranty'])))


if __name__ == '__main__':
    main()
