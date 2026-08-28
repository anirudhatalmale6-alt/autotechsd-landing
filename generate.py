#!/usr/bin/env python3
"""Build the 10 service landing pages.

Two outputs per page, from the same markup:

  wp/pages/<slug>.html      content fragment to paste into a WordPress
                            Custom HTML block — no <head>, no header/footer,
                            because Astra supplies those.
  preview/<slug>.html       the same fragment inside a standalone shell so the
                            client can review it before anything is published.

Rule followed throughout: every number and claim on these pages comes from the
client's own drafts or from his live site. Nothing is invented. Where he only
states the 12-month/12,000-mile warranty on some services, it only appears on
those pages.
"""
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, 'data', 'content.json')
WP_OUT = os.path.join(ROOT, 'wp', 'pages')
PREVIEW_OUT = os.path.join(ROOT, 'preview')

PHONE_DISPLAY = '(858) 277-2850'
PHONE_HREF = 'tel:+18582772850'
ADDRESS = '7950 Clairemont Mesa Blvd, San Diego, CA 92111'
# /contact/ does not exist on his site — the booking form is /appointments/,
# which is where every BOOK APPOINTMENT button in his header and footer goes.
BOOK_URL = 'https://autotechsd.com/appointments/'

# Image base. Preview reads them out of the local img/ folder; the WordPress
# build reads them off his site.
#
# The uploads path is NOT ours to choose. The REST media endpoint drops files
# into wp-content/uploads/<year>/<month>/ and renames anything whose name is
# already taken, so a single fixed prefix is a guess that breaks on the first
# collision. wp-deploy.py records the source_url the API actually returned for
# each file in data/media-map.json; if that file exists we use those URLs and
# the prefix below is only the fallback for anything not yet uploaded.
IMG_WP = 'https://autotechsd.com/wp-content/uploads/atslp/'
IMG_PREVIEW = 'img/'
MEDIA_MAP = os.path.join(ROOT, 'data', 'media-map.json')


def img_url(base, rel):
    """Resolve one image reference. `base` is either a plain prefix (preview)
    or a {relative path: absolute URL} map read back from the media library."""
    if isinstance(base, dict):
        return base.get(rel, IMG_WP + rel)
    return base + rel

CERTS = [
    ('cert-ase.webp', 'ASE Certified', 95, 93),
    ('cert-hybrid.webp', 'Hybrid Certified', 95, 93),
    # RepairPal and the higher-resolution NAPA AutoCare mark are the two files
    # he sent on 27 Aug. They went onto the home page strip first; these pages
    # carry the same row, so they get the same two.
    ('cert-repairpal.webp', 'RepairPal Certified', 260, 278),
    ('cert-napa-autocare-hd.webp', 'NAPA AutoCare Center', 180, 48),
    ('cert-bbb.webp', 'BBB Accredited Business', 150, 66),
    ('cert-aaa.webp', 'AAA Approved Auto Repair', 125, 77),
    ('cert-carfax.webp', 'CARFAX Service Shop', 171, 32),
    ('cert-gwc.webp', 'GWC Warranty Premier Service Center', 270, 92),
    ('cert-angi.webp', 'Angi', 100, 88),
]

ICON_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M20 6 9 17l-5-5"/></svg>')
ICON_SHIELD = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
               '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>'
               '<path d="m9 12 2 2 4-4"/></svg>')
ICON_TICK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M20 6 9 17l-5-5"/></svg>')
ICON_BAYS = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M3 21V8.6L12 3l9 5.6V21"/><path d="M2 21h20"/>'
             '<path d="M7.5 21v-7h9v7"/><path d="M7.5 17.2h9"/></svg>')
ICON_EST = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<circle cx="12" cy="9" r="6.2"/>'
            '<path d="m8.3 14.4-1.6 7.1L12 18.4l5.3 3.1-1.6-7.1"/></svg>')
ICON_STAR = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
             '<path d="m12 2.4 2.95 5.98 6.6.96-4.78 4.65 1.13 6.57L12 17.46 '
             '6.1 20.56l1.13-6.57L2.45 9.34l6.6-.96Z"/></svg>')

# The strip he asked for on 28 Aug: the three phrases his team wants visible at
# the top of every page, laid out like the icon row on his home page. His words,
# hyphenated to match the wording already used further down these pages.
TRUST = [
    (ICON_BAYS, '19-Bay Facility'),
    (ICON_EST, 'Established Since 1999'),
    (ICON_STAR, '5-Star Customer Rated'),
]

# Cancelled 26 Aug 2026. His site already has /auto-body-and-collision-repair/,
# which he only spotted after the build — two pages targeting the same service
# compete with each other in Google, so this one is out of the deliverable.
# Its config below and its content in content.json stay put, so the FAQ and the
# Service schema can be lifted onto his existing live page if he wants them.
SKIP = {'auto-body-shop-san-diego'}

# --------------------------------------------------------------------------
# Per-page presentation data.
#   hero    background image
#   stats   four tiles — each one traceable to his copy for THAT page
#   checks  what the service covers — his words, broken into scannable items
#   band    heading + lead for the dark checklist band
# --------------------------------------------------------------------------
PAGES = {
    'car-battery-replacement-san-diego': {
        'name': 'Car Battery Replacement',
        'hero': 'engine-wide.webp',
        'h2': 'Tested properly before anything gets replaced',
        'stats': [('Under <em>30</em> min', 'Most replacements'),
                  ('<em>Free</em>', 'Battery &amp; charging test'),
                  ('12<em>/</em>12', 'Month / 12,000-mile warranty'),
                  ('<em>Same</em> day', 'Installation')],
    },
    'brake-repair-san-diego': {
        'name': 'Brake Repair & Replacement',
        'hero': 'bay-wide.webp',
        'h2': 'Brakes inspected, repaired and road-tested',
        'stats': [('<em>Same</em> day', 'Most pad &amp; rotor jobs'),
                  ('<em>Free</em>', 'Brake inspection'),
                  ('12<em>/</em>12', 'Month / 12,000-mile warranty'),
                  ('<em>OEM</em>-quality', 'Parts fitted')],
    },
    'oil-change-san-diego': {
        'name': 'Oil Change Service',
        'hero': 'hero-shop.webp',
        'h2': 'The right oil for your engine, not just any oil',
        'stats': [('<em>Free</em>', 'Multi-point inspection'),
                  ('5,000<em>-</em>7,500', 'Mile synthetic interval'),
                  ('<em>3</em> oil types', 'Synthetic, blend, high-mileage'),
                  ('<em>OEM</em> spec', 'Matched to your manufacturer')],
    },
    'ac-repair-san-diego': {
        'name': 'Auto A/C Repair',
        'hero': 'vehicles-row.webp',
        'h2': 'Diagnosed before it gets recharged',
        'stats': [('<em>Full</em> inspection', 'Before any recharge'),
                  ('<em>Exact</em> quote', 'Before work starts'),
                  ('<em>Hybrid</em> &amp; EV', 'Serviced too'),
                  ('<em>All</em> makes', 'Domestic, European, Asian')],
    },
    'transmission-repair-san-diego': {
        'name': 'Transmission Repair',
        'hero': 'engine-wide.webp',
        'h2': 'Catch it early and it stays a fluid service',
        'stats': [('30k<em>-</em>60k', 'Mile fluid interval'),
                  ('<em>3</em> types', 'Automatic, manual, CVT'),
                  ('<em>Full</em> diagnostics', 'Before major repairs'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
    },
    'traction-control-abs-repair': {
        'name': 'Traction Control & ABS Repair',
        'hero': 'european-bmw.webp',
        'h2': 'A warning light is a fault code, not a mystery',
        'stats': [('<em>Exact</em> fault code', 'Pulled before repair'),
                  ('<em>Targeted</em>', 'No guesswork repairs'),
                  ('<em>3</em> systems', 'ABS, traction, stability'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
    },
    'cooling-system-repair-san-diego': {
        'name': 'Cooling System Repair',
        'hero': 'bay-wide.webp',
        'h2': 'Overheating damage happens in minutes',
        'stats': [('30k<em>-</em>60k', 'Mile flush interval'),
                  ('<em>Minutes</em>', 'Is all overheating needs'),
                  ('<em>4</em> common causes', 'Diagnosed properly'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
    },
    'tesla-ev-service-san-diego': {
        'name': 'Tesla & EV Service',
        'hero': 'vehicles-row.webp',
        'h2': 'Independent EV service without the dealership wait',
        'stats': [('<em>19</em> bays', 'No dealership queue'),
                  ('<em>Same</em> day', 'Service turnaround'),
                  ('<em>12V</em>', 'Auxiliary battery service'),
                  ('<em>Tesla</em> &amp; EV', 'Alongside gas and hybrid')],
    },
    'windshield-replacement-san-diego': {
        'name': 'Windshield Replacement',
        'hero': 'landrover.webp',
        'h2': 'Repair it early, replace it when it matters',
        'stats': [('Under <em>1</em> hr', 'Most chip repairs'),
                  ('<em>ADAS</em>', 'Camera recalibration'),
                  ('<em>Most</em> insurers', 'Billed directly'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
    },
    'auto-body-shop-san-diego': {
        'name': 'Auto Body & Collision Repair',
        'hero': 'collision.webp',
        'h2': 'Everyday bodywork, not just collision claims',
        'stats': [('<em>Upfront</em>', 'Estimate before work'),
                  ('<em>Factory</em> code', 'Paint mixed to match'),
                  ('<em>PDR</em>', 'Paintless dent repair'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
    },
    # --- added later, from his second batch of copy ---
    'commercial-fleet-service-repair-san-diego': {
        'name': 'Commercial Fleet Service',
        # Hero is still a stand-in. His own fleet photo goes in the body instead:
        # it is a 4:1 band, and the hero is object-fit:cover into a tall box on a
        # phone, which would zoom that band down to about one grille.
        'hero': 'hero-shop.webp',
        'h2': 'One shop for the whole fleet, mechanical through collision',
        'stats': [('<em>19</em> bays', 'Service and repair bays'),
                  ('<em>Since</em> 1999', 'Serving San Diego'),
                  ('<em>24</em> hour', 'Vehicle drop-off'),
                  ('<em>One</em> shop', 'Mechanical, glass &amp; collision')],
        'figures': [
            # His photo, cropped to the truck row. Everything above the crop line
            # was the building signage, and the lettering in the file he sent is
            # misspelt there ("AOTECHSD.COM"), so it does not go on his own page.
            {'after': 1, 'caption': 'Work trucks and service vans in for fleet maintenance.',
             'items': [('fleet-vehicles.webp', 'Fleet of white work trucks and service vans at Auto Tech Specialists in San Diego')]},
            {'after': 6, 'caption': 'Our 19-bay facility in Kearny Mesa.',
             'items': [('bay-wide.webp', 'Service bays at Auto Tech Specialists in Kearny Mesa, San Diego')]},
        ],
    },
    'auto-detailing-san-diego': {
        'name': 'Auto Detailing',
        # landrover.webp is a Range Rover wordmark, not a vehicle — fine as a dark
        # hero wash elsewhere, useless as a "before" detailing photo.
        'hero': 'hero-shop.webp',
        'h2': 'Two packages, priced up front',
        'stats': [('<em>$150</em>', 'Silver package'),
                  ('<em>$250</em>', 'Gold package'),
                  ('1.5<em>&ndash;</em>4 hrs', 'Typical turnaround'),
                  ('<em>3</em> add-ons', 'Engine bay, headlights, pet hair')],
        # He asked for room for pictures, and his own file marks two spots:
        # a before/after next to the packages and a finished-vehicle shot on Gold.
        'figures': [
            # His own two shots, 26 Aug. Same car, same bay, same light, so they
            # line up exactly side by side. Labelled "wash" and "finished" and
            # not "before/after": the left frame is a car under foam, not a dirty
            # one, and captioning a rinse as a "before" would oversell the work.
            {'after': 1, 'caption': 'Gold detailing in our wash bay — hand foam wash through to the finished car.',
             'items': [('detail-foam.webp', 'Car under a hand foam wash in the Gold Detailing bay at Auto Tech Specialists in San Diego', 'Wash'),
                       ('detail-finished.webp', 'Finished vehicle after Gold detailing at Auto Tech Specialists in Kearny Mesa, San Diego', 'Finished')]},
            {'after': 3, 'caption': 'Photo slot — a finished Gold package vehicle goes here.',
             'items': [('vehicles-row.webp', 'Gold auto detailing package at Auto Tech Specialists in Kearny Mesa')]},
        ],
    },
}

# Short hero tick lines. Kept identical across pages because they describe the
# shop, not the service — all four are on his live site.
HERO_TICKS = ['ASE-certified technicians', '19-bay facility in Kearny Mesa',
              'Walk-ins welcome', 'Free written estimates']


def esc(s):
    return html.escape(s, quote=False)


def short_service(page):
    """The label used in the eyebrow, the nav and the closing CTA heading."""
    return PAGES[page['slug']]['name']


def hero_size(name):
    """Intrinsic size of a hero file, read at build time rather than hardcoded."""
    from PIL import Image
    with Image.open(os.path.join(ROOT, 'src', 'img', name)) as im:
        return im.size


def split_sign(s):
    """'Slow Engine Crank: The engine turns over sluggishly...' -> label, rest.

    His signs are written as 'Label: explanation'. Bolding the label makes the
    list scannable, which is the whole point of a symptoms list.
    """
    m = re.match(r'^([^:]{2,48}):\s+(.*)$', s.strip(), re.S)
    return (m.group(1), m.group(2)) if m else (None, s.strip())


def minify_css(text):
    """Strip comments and collapse whitespace.

    Used for the preview shell and for the <style> block carried inside each
    WordPress fragment. wp/ats-lp.css stays the readable master.
    """
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s*([{};:,>])\s*', r'\1', text)
    return text.replace(';}', '}').strip()


def word_count(page):
    """Words a visitor actually sees in the copy — the client asked for 400-500."""
    parts = [page['heroSub'], page['bodyOpen'], page['warranty'],
             page.get('glanceH', ''), page.get('ctaLead', ''),
             page.get('finePrint', ''), page.get('asideNote', '')]
    for label, value in page.get('glance', []):
        parts += [label, value]
    for sec in page['sections']:
        parts += [sec['h']] + sec['paras'] + sec['list']
        if sec.get('table'):
            parts += sec['table']['head'] + [c for r in sec['table']['rows'] for c in r]
    parts += [page['signsH']] + page['signs']
    for f in page['faq']:
        parts += [f['q'], f['a']]
    return sum(len(x.split()) for x in parts if x)


def render_table(t, caption):
    """His comparison table, wrapped so it can scroll instead of forcing the page to.

    A three-column table with this much text in each cell cannot shrink to 320px.
    Letting the wrapper scroll keeps the table readable and stops it blowing out
    the width of every other section on the page.
    """
    head = '\n'.join('              <th scope="col">%s</th>' % esc(h) for h in t['head'])
    rows = []
    for r in t['rows']:
        cells = ['              <th scope="row">%s</th>' % esc(r[0])]
        cells += ['              <td>%s</td>' % esc(c) for c in r[1:]]
        rows.append('            <tr>\n%s\n            </tr>' % '\n'.join(cells))
    # On a phone only the first price column fits, and a cut-off table gives no
    # hint that a second one exists — on a page whose whole job is comparing the
    # two packages, that loses half the content. The hint shows below 700px only.
    return ('          <p class="ats-lp__table-hint">Swipe the table sideways to compare both packages.</p>\n'
            '          <div class="ats-lp__table-wrap" tabindex="0" role="region" '
            'aria-label="%s">\n'
            '            <table class="ats-lp__table">\n'
            '              <thead>\n            <tr>\n%s\n            </tr>\n              </thead>\n'
            '              <tbody>\n%s\n              </tbody>\n'
            '            </table>\n'
            '          </div>' % (esc(caption), head, '\n'.join(rows)))


def render_figure(group, img_base):
    """A photo slot inside the body column.

    The client asked for room for pictures. These carry stand-in shots from his
    current site now and are the exact spots his own photos drop into — same
    markup, same dimensions, only the filename changes.
    """
    imgs = []
    for item in group['items']:
        # (file, alt) or (file, alt, label). A two-up photo pair needs the label
        # on each shot — a single caption underneath cannot say which is which.
        name, alt = item[0], item[1]
        label = item[2] if len(item) > 2 else None
        w, h = hero_size(name)
        img = ('<img src="%s" alt="%s" width="%d" height="%d" '
               'loading="lazy" decoding="async">'
               % (img_url(img_base, name), esc(alt), w, h))
        if label:
            imgs.append('            <div class="ats-lp__shot">%s'
                        '<span class="ats-lp__shot-tag">%s</span></div>'
                        % (img, esc(label)))
        else:
            imgs.append('            %s' % img)
    cls = 'ats-lp__fig' + (' ats-lp__fig--pair' if len(imgs) > 1 else '')
    cap = ('\n            <figcaption>%s</figcaption>' % esc(group['caption'])
           if group.get('caption') else '')
    return ('          <figure class="%s" data-ats-photo-slot>\n%s%s\n          </figure>'
            % (cls, '\n'.join(imgs), cap))


def wp_safe(frag):
    """Strip the section comments and blank lines out of the WordPress copy.

    wpautop runs over page content on render. A blank line between two
    <section>s makes it emit an empty <p>, and my `<!-- hero -->` style comments
    give it something to wrap, so it emitted one before EVERY section. Each of
    those carries the theme's 27px paragraph margin, which showed up as a white
    band between every band of colour on the page — including between the dark
    hero and the dark stat strip. Invisible in the preview, which does not run
    wpautop; only the live pages had it.

    The readable version stays in the preview build; only the copy that goes
    into WordPress is flattened.
    """
    frag = re.sub(r'^\s*<!--.*?-->\s*$', '', frag, flags=re.M)
    return re.sub(r'\n\s*\n+', '\n', frag).strip() + '\n'


def build_fragment(page, cfg, img_base):
    service = short_service(page)

    stats = '\n'.join(
        '          <div class="ats-lp__stat"><b>%s</b><span>%s</span></div>' % (n, l)
        for n, l in cfg['stats'])

    certs = '\n'.join(
        '          <img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">'
        % (img_url(img_base, 'cert/' + f), esc(a), w, h) for f, a, w, h in CERTS)

    ticks = '\n'.join('          <li>%s%s</li>' % (ICON_TICK, esc(t)) for t in HERO_TICKS)

    trust = '\n'.join(
        '        <li><span class="ats-lp__trust-ico">%s</span>%s</li>' % (i, esc(t))
        for i, t in TRUST)

    # Body column: his opening paragraph, then a sub-heading per section with
    # its paragraphs and any bullet list underneath.
    body = ['          <p>%s</p>' % esc(page['bodyOpen'])] if page['bodyOpen'] else []
    figures = {f['after']: f for f in cfg.get('figures', [])}
    for i, sec in enumerate(page['sections']):
        body.append('          <h3 class="ats-lp__h3">%s</h3>' % esc(sec['h']))
        body.extend('          <p>%s</p>' % esc(p) for p in sec['paras'])
        if sec.get('table'):
            body.append(render_table(sec['table'], sec['h']))
        if sec['list']:
            body.append('          <ul>')
            # Same 'Label: explanation' shape as the signs list — bold the label
            # so the bullets scan instead of reading as more prose.
            for li in sec['list']:
                lab, rest = split_sign(li)
                body.append('            <li>%s</li>' % (
                    ('<b>%s:</b> %s' % (esc(lab), esc(rest))) if lab else esc(rest)))
            body.append('          </ul>')
        if i in figures:
            body.append(render_figure(figures[i], img_base))
    if page.get('finePrint'):
        body.append('          <p class="ats-lp__fineprint">%s</p>' % esc(page['finePrint']))
    body = '\n'.join(body)

    signs_html = ''
    if page['signs']:
        items = []
        for s in page['signs']:
            label, rest = split_sign(s)
            inner = ('<b>%s:</b> %s' % (esc(label), esc(rest))) if label else esc(rest)
            items.append('          <li>%s<span>%s</span></li>' % (ICON_CHECK, inner))
        signs_html = '''
  <!-- warning signs -->
  <section class="ats-lp__sec ats-lp__sec--alt">
    <div class="ats-lp__wrap">
      <div class="ats-lp__head">
        <p class="ats-lp__eyebrow">Warning signs</p>
        <h2 class="ats-lp__h2">{h}</h2>
        <p class="ats-lp__lead">Any of these means it is worth getting checked before it becomes a bigger repair.</p>
      </div>
      <ul class="ats-lp__checks ats-lp__checks--light">
{items}
      </ul>
    </div>
  </section>
'''.format(h=esc(page['signsH'] or 'Signs you need this service'), items='\n'.join(items))

    faq = '\n'.join(
        '          <details>\n'
        '            <summary>%s</summary>\n'
        '            <p class="ats-lp__faq-a">%s</p>\n'
        '          </details>' % (esc(f['q']), esc(f['a']))
        for f in page['faq'])

    # "At a glance" — his own summary list, on the two newer pages only. It is
    # six label/value pairs, which is too many for the four stat tiles, so it
    # gets its own panel rather than being trimmed to fit.
    glance_html = ''
    if page.get('glance'):
        items = '\n'.join(
            '          <div class="ats-lp__glance-row"><dt>%s</dt><dd>%s</dd></div>'
            % (esc(label), esc(value)) for label, value in page['glance'])
        glance_html = '''
  <!-- at a glance -->
  <section class="ats-lp__sec ats-lp__sec--alt">
    <div class="ats-lp__wrap ats-lp__wrap--narrow">
      <div class="ats-lp__head ats-lp__head--mid">
        <p class="ats-lp__eyebrow">Overview</p>
        <h2 class="ats-lp__h2">{h}</h2>
      </div>
      <dl class="ats-lp__glance">
{items}
      </dl>
    </div>
  </section>
'''.format(h=esc(page['glanceH']), items=items)

    # The warranty covers repairs. Detailing is not a repair, so that page has
    # no warranty text and the whole band is left off rather than softened.
    warranty_html = ''
    if page.get('warranty'):
        warranty_html = '''
  <!-- warranty -->
  <section class="ats-lp__warranty">
    <div class="ats-lp__warranty-inner">
      <span class="ats-lp__warranty-mark">{shield}</span>
      <div class="ats-lp__warranty-text">
        <b>Backed by a written warranty</b>
        <p>{warranty}</p>
      </div>
    </div>
  </section>
'''.format(shield=ICON_SHIELD, warranty=esc(page['warranty']))

    aside_note = ('\n          <p class="ats-lp__aside-note">%s</p>' % esc(page['asideNote'])
                  if page.get('asideNote') else '')
    cta_lead = ('\n        <p class="ats-lp__cta-lead">%s</p>' % esc(page['ctaLead'])
                if page.get('ctaLead') else '')

    return '''<div class="ats-lp">

  <!-- trust strip -->
  <section class="ats-lp__trust" aria-label="Why Auto Tech Specialists">
    <div class="ats-lp__wrap">
      <ul class="ats-lp__trust-row">
{trust}
      </ul>
    </div>
  </section>

  <!-- hero -->
  <section class="ats-lp__hero">
    <div class="ats-lp__hero-bg"><img src="{hero_url}" alt="" width="{hero_w}" height="{hero_h}" fetchpriority="high" decoding="async"></div>
    <div class="ats-lp__hero-inner">
      <p class="ats-lp__kicker">{kicker}</p>
      <h1>{h1}</h1>
      <p class="ats-lp__hero-sub">{lead}</p>
      <div class="ats-lp__hero-actions">
        <a class="ats-btn ats-btn--primary" href="{phone_href}">Call {phone}</a>
        <a class="ats-btn ats-btn--outline" href="{book}">Book an appointment</a>
      </div>
      <ul class="ats-lp__ticks">
{ticks}
      </ul>
    </div>
  </section>

  <!-- at a glance -->
  <section class="ats-lp__stats" aria-label="{service} at a glance">
    <div class="ats-lp__stats-grid">
{stats}
    </div>
  </section>

  <!-- certifications -->
  <section class="ats-lp__certs">
    <div class="ats-lp__wrap">
      <p class="ats-lp__certs-label">Certified, approved and accredited</p>
      <div class="ats-lp__certs-row">
{certs}
      </div>
    </div>
  </section>

  <!-- body copy + call card -->
  <section class="ats-lp__sec">
    <div class="ats-lp__wrap">
      <div class="ats-lp__copy">
        <div class="ats-lp__copy-main">
          <p class="ats-lp__eyebrow">{service}</p>
          <h2 class="ats-lp__h2">{h2}</h2>
{body}
        </div>
        <aside class="ats-lp__aside">
          <h3>Talk to a technician today</h3>
          <p>Tell us what the car is doing and we will tell you what it needs — with a written estimate before any work starts.</p>
          <a class="ats-btn ats-btn--primary" href="{phone_href}">Call {phone}</a>{aside_note}
          <p class="ats-lp__aside-meta">
            <strong>Auto Tech Specialists</strong>
            {address}<br>Walk-ins welcome
          </p>
        </aside>
      </div>
    </div>
  </section>
{glance}{signs}{warranty}
  <!-- FAQ -->
  <section class="ats-lp__sec">
    <div class="ats-lp__wrap">
      <div class="ats-lp__head ats-lp__head--mid">
        <p class="ats-lp__eyebrow">Questions</p>
        <h2 class="ats-lp__h2">Frequently asked questions</h2>
      </div>
      <div class="ats-lp__faq">
{faq}
      </div>
    </div>
  </section>

  <!-- closing CTA -->
  <section class="ats-lp__cta">
    <div class="ats-lp__cta-inner">
      <div>
        <h2>Need {service} in San Diego?</h2>
        <p>{address} &middot; Walk-ins welcome</p>{cta_lead}
      </div>
      <div class="ats-lp__cta-actions">
        <a class="ats-btn ats-btn--primary" href="{phone_href}">Call {phone}</a>
        <a class="ats-btn ats-btn--dark" href="{book}">Book online</a>
      </div>
    </div>
  </section>

</div>
'''.format(hero_url=img_url(img_base, cfg['hero']),
           hero_w=hero_size(cfg['hero'])[0], hero_h=hero_size(cfg['hero'])[1], kicker=esc(page['kicker']), h1=esc(page['h1']),
           lead=esc(page['heroSub']), phone_href=PHONE_HREF, phone=PHONE_DISPLAY, book=BOOK_URL,
           ticks=ticks, trust=trust, stats=stats, certs=certs, service=esc(service),
           h2=esc(cfg['h2']), body=body, address=ADDRESS, signs=signs_html,
           glance=glance_html, warranty=warranty_html, aside_note=aside_note,
           cta_lead=cta_lead, faq=faq)


PREVIEW_SHELL = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="img/mark.webp" type="image/webp">
<link rel="preload" as="font" type="font/woff2" href="fonts/montserrat-latin-var.woff2" crossorigin>
<style>{css}</style>
<script type="application/ld+json">
{schema}
</script>
</head>
<body>
<div class="pv-note">
  Preview only &mdash; this is the page content as it will sit inside autotechsd.com.
  The site header, footer and menu come from your WordPress theme.
</div>
<header class="pv-hdr">
  <a class="pv-hdr__brand" href="index.html"><img src="img/logo.webp" alt="Auto Tech Specialists" width="190" height="46"></a>
  <nav class="pv-hdr__nav" aria-label="Landing pages">
{navlinks}
  </nav>
</header>
<main>
{fragment}
</main>
<footer class="pv-ftr">
  <p><strong>Auto Tech Specialists</strong> &middot; {address} &middot; <a href="{phone_href}">{phone}</a></p>
  <p class="pv-ftr__small">Preview build for review. &copy; <span id="yr">2026</span> Auto Tech Specialists.</p>
</footer>
<script>document.getElementById('yr').textContent=new Date().getFullYear();</script>
</body>
</html>
'''


INDEX_SHELL = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auto Tech Specialists — landing page previews</title>
<meta name="robots" content="noindex">
<link rel="icon" href="img/mark.webp" type="image/webp">
<link rel="preload" as="font" type="font/woff2" href="fonts/montserrat-latin-var.woff2" crossorigin>
<style>{css}
  .pv-intro {{ max-width: 900px; margin: 0 auto; padding: clamp(28px,5vw,56px) clamp(16px,4vw,32px) 8px; }}
  .pv-intro h1 {{ font-size: clamp(1.6rem,3.4vw,2.3rem); margin: 0 0 12px; color: #191919; letter-spacing: -.02em; }}
  .pv-intro p {{ margin: 0 0 10px; color: #5a5a5a; line-height: 1.6; }}
  .pv-grid {{ max-width: 900px; margin: 0 auto; padding: 18px clamp(16px,4vw,32px) clamp(40px,6vw,72px);
             display: grid; gap: 12px; }}
  .pv-card {{ display: block; text-decoration: none; border: 1px solid #e4e4e4; border-radius: 10px;
             padding: 16px 18px; background: #fff; transition: border-color .15s ease, transform .15s ease; }}
  .pv-card:hover {{ border-color: #ce171f; transform: translateY(-1px); }}
  .pv-card b {{ display: block; color: #191919; font-size: 1.02rem; margin-bottom: 4px; }}
  .pv-card span {{ display: block; color: #ce171f; font-size: .82rem; font-weight: 600; }}
  .pv-card em {{ display: block; color: #8f8f8f; font-size: .76rem; font-style: normal; margin-top: 4px; }}
</style>
</head>
<body>
<div class="pv-note">Preview build — nothing here is published to autotechsd.com yet.</div>
<header class="pv-hdr">
  <a class="pv-hdr__brand" href="index.html"><img src="img/logo.webp" alt="Auto Tech Specialists" width="190" height="46"></a>
</header>
<main>
  <div class="pv-intro">
    <h1>12 service landing pages</h1>
    <p>Your copy, your FAQs, your URLs and your schema markup — rebuilt in the site's own
    branding instead of the plain HTML the drafts came in.</p>
    <p>Built on your expanded second draft. Every page carries sub-headings, bullet lists
    and the warranty statement — the word count for each one is on its card below.</p>
    <p><strong>Fleet and Detailing</strong> are the two newest and are longer than the rest,
    because your drafts for them were longer. Detailing also has the Silver/Gold comparison
    table, and it is the one page with no warranty band — a detail is not a repair, so the
    12-month/12,000-mile repair warranty does not apply to it.</p>
    <p>Each page is a self-contained block of content. On the live site your WordPress theme
    supplies the header, menu and footer around it, so nothing here changes your existing design.</p>
    <p><strong>Photos:</strong> every image here is a stand-in taken from your current site.
    Fleet and Detailing also have dedicated photo slots in the body copy, captioned for the
    shots that belong there — your own photos drop straight into them.</p>
  </div>
  <div class="pv-grid">
{cards}
  </div>
</main>
<footer class="pv-ftr">
  <p><strong>Auto Tech Specialists</strong> &middot; {address} &middot; <a href="{phone_href}">{phone}</a></p>
  <p class="pv-ftr__small">Preview build for review.</p>
</footer>
</body>
</html>
'''


def main():
    pages = [p for p in json.load(open(CONTENT, encoding='utf-8'))
             if p['slug'] not in SKIP]

    for d in (WP_OUT, PREVIEW_OUT):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)

    # preview needs the assets alongside it
    shutil.copytree(os.path.join(ROOT, 'src', 'img'), os.path.join(PREVIEW_OUT, 'img'))
    os.makedirs(os.path.join(PREVIEW_OUT, 'img', 'cert'), exist_ok=True)
    for f, _, _w, _h in CERTS:
        shutil.copy(os.path.join(ROOT, 'src', 'img', f),
                    os.path.join(PREVIEW_OUT, 'img', 'cert', f))
    shutil.copytree(os.path.join(ROOT, 'src', 'fonts'), os.path.join(PREVIEW_OUT, 'fonts'))
    os.makedirs(os.path.join(PREVIEW_OUT, 'css'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'wp', 'ats-lp.css'),
                os.path.join(PREVIEW_OUT, 'css', 'ats-lp.css'))
    shutil.copy(os.path.join(ROOT, 'preview-shell.css'),
                os.path.join(PREVIEW_OUT, 'css', 'preview-shell.css'))

    lp_css = open(os.path.join(ROOT, 'wp', 'ats-lp.css'), encoding='utf-8').read()

    css = minify_css(
        open(os.path.join(ROOT, 'preview-shell.css'), encoding='utf-8').read() + lp_css)

    # Each WP fragment carries its own stylesheet, so the pages style themselves
    # and nobody has to visit the Customizer. Goes in the same Custom HTML block
    # as the markup — no block delimiters, the fragment is pasted as one lump.
    # Everything is namespaced .ats-lp, so eleven copies cannot collide with each
    # other or with Astra.
    # NOTE: <style> survives only for a user with unfiltered_html, i.e. an
    # Administrator on a single-site install. Posted as an Editor, wp_kses_post
    # strips it and the pages render unstyled — that is why the job needs an
    # Administrator, not because of the Customizer.
    # One newline, not two: a blank line here is another empty <p> from wpautop.
    wp_style = '<style>%s</style>\n' % minify_css(lp_css)

    # Real media-library URLs if wp-deploy.py has uploaded anything yet,
    # otherwise the plain prefix.
    img_wp = IMG_WP
    if os.path.exists(MEDIA_MAP):
        img_wp = json.load(open(MEDIA_MAP, encoding='utf-8'))
        print('media map: %d image(s) resolve to real uploads' % len(img_wp))

    navlinks = '\n'.join(
        '    <a href="%s.html">%s</a>' % (p['slug'], esc(short_service(p)))
        for p in pages)

    for page in pages:
        cfg = PAGES[page['slug']]

        # WordPress fragment — images resolve to the media library folder.
        frag_wp = wp_safe(build_fragment(page, cfg, img_wp))
        open(os.path.join(WP_OUT, page['slug'] + '.html'), 'w', encoding='utf-8').write(
            wp_style + frag_wp)

        # Preview — images resolve locally.
        frag_pv = build_fragment(page, cfg, IMG_PREVIEW)
        out = PREVIEW_SHELL.format(
            title=esc(page['title']), desc=esc(page['metaDesc']),
            canonical=page['canonical'], schema=json.dumps(page['schema'], indent=2),
            navlinks=navlinks, fragment=frag_pv, address=ADDRESS, css=css,
            phone_href=PHONE_HREF, phone=PHONE_DISPLAY)
        open(os.path.join(PREVIEW_OUT, page['slug'] + '.html'), 'w', encoding='utf-8').write(out)

    # A contents page so the client has one link to open instead of ten.
    cards = '\n'.join(
        '    <a class="pv-card" href="{slug}.html">'
        '<b>{n}. {name}</b><span>/{slug}/</span><em>{faq} FAQ &middot; {words} words</em></a>'.format(
            slug=p['slug'], n=i + 1, name=esc(short_service(p)), faq=len(p['faq']),
            words=word_count(p))
        for i, p in enumerate(pages))
    open(os.path.join(PREVIEW_OUT, 'index.html'), 'w', encoding='utf-8').write(INDEX_SHELL.format(
        cards=cards, address=ADDRESS, phone_href=PHONE_HREF, phone=PHONE_DISPLAY,
        css=minify_css(open(os.path.join(ROOT, 'preview-shell.css'), encoding='utf-8').read())))

    print('built %d pages' % len(pages))
    print('  wp fragments -> %s' % WP_OUT)
    print('  preview      -> %s' % PREVIEW_OUT)


if __name__ == '__main__':
    main()
