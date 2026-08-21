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
BOOK_URL = 'https://autotechsd.com/contact/'

# Image base. Preview reads them out of the local img/ folder; once the media
# library IDs exist this flips to the WordPress uploads URL.
IMG_WP = 'https://autotechsd.com/wp-content/uploads/atslp/'
IMG_PREVIEW = 'img/'

CERTS = [
    ('cert-ase.webp', 'ASE Certified', 95, 93),
    ('cert-hybrid.webp', 'Hybrid Certified', 95, 93),
    ('cert-napa-autocare.webp', 'NAPA AutoCare Center', 150, 41),
    ('cert-bbb.webp', 'BBB Accredited Business', 150, 66),
    ('cert-aaa.webp', 'AAA Approved Auto Repair', 125, 77),
    ('cert-carfax.webp', 'CARFAX Service Shop', 171, 32),
    ('cert-gwc.webp', 'GWC Warranty Premier Service Center', 270, 92),
    ('cert-angi.webp', 'Angi', 100, 88),
]

ICON_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M20 6 9 17l-5-5"/></svg>')
ICON_TICK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M20 6 9 17l-5-5"/></svg>')

# --------------------------------------------------------------------------
# Per-page presentation data.
#   hero    background image
#   stats   four tiles — each one traceable to his copy for THAT page
#   checks  what the service covers — his words, broken into scannable items
#   band    heading + lead for the dark checklist band
# --------------------------------------------------------------------------
PAGES = {
    'car-battery-replacement-san-diego': {
        'hero': 'engine-wide.webp',
        'h2': 'Tested properly before anything gets replaced',
        'stats': [('Under <em>30</em> min', 'Most replacements'),
                  ('<em>Free</em>', 'Battery &amp; charging test'),
                  ('12<em>/</em>12', 'Month / 12,000-mile warranty'),
                  ('<em>Same</em> day', 'Installation')],
        'band': ('What the battery service covers',
                 'Our complimentary battery and charging-system test checks voltage, '
                 'cold-cranking amps (CCA), and alternator output.'),
        'checks': ['Voltage and cold-cranking amps (CCA) tested',
                   'Alternator output and charging system checked',
                   'Starter tested at the same time',
                   'AGM, standard flooded and GEL batteries in stock',
                   'Domestic, European, Japanese, hybrid and EV vehicles',
                   'Written quote before any work starts'],
    },
    'brake-repair-san-diego': {
        'hero': 'bay-wide.webp',
        'h2': 'Brakes inspected, repaired and road-tested',
        'stats': [('<em>Same</em> day', 'Most pad &amp; rotor jobs'),
                  ('<em>Free</em>', 'Brake inspection'),
                  ('12<em>/</em>12', 'Month / 12,000-mile warranty'),
                  ('<em>OEM</em>-quality', 'Parts fitted')],
        'band': ('What the brake service covers',
                 'Our brake service starts with a free inspection of pads, rotors, '
                 'calipers, and brake lines.'),
        'checks': ['Pads, rotors, calipers and brake lines inspected',
                   'Ceramic and semi-metallic pad options',
                   'Full hydraulic system repair',
                   'OEM-quality parts',
                   'Every vehicle test-driven after the repair',
                   'Squealing, grinding and soft-pedal diagnosis'],
    },
    'oil-change-san-diego': {
        'hero': 'hero-shop.webp',
        'h2': 'The right oil for your engine, not just any oil',
        'stats': [('<em>Free</em>', 'Multi-point inspection'),
                  ('5,000<em>-</em>7,500', 'Mile synthetic interval'),
                  ('<em>3</em> oil types', 'Synthetic, blend, high-mileage'),
                  ('<em>OEM</em> spec', 'Matched to your manufacturer')],
        'band': ('What every oil change includes',
                 'Every oil change includes a complimentary multi-point safety inspection.'),
        'checks': ['Full synthetic, synthetic blend and high-mileage oils',
                   'Oil matched to your manufacturer specification',
                   'Oil filter replaced',
                   'Essential fluids topped off',
                   'Tire inflation pressures checked',
                   'Complimentary multi-point safety inspection'],
    },
    'ac-repair-san-diego': {
        'hero': 'vehicles-row.webp',
        'h2': 'Diagnosed before it gets recharged',
        'stats': [('<em>Full</em> inspection', 'Before any recharge'),
                  ('<em>Exact</em> quote', 'Before work starts'),
                  ('<em>Hybrid</em> &amp; EV', 'Serviced too'),
                  ('<em>All</em> makes', 'Domestic, European, Asian')],
        'band': ('What the A/C service covers',
                 'Our A/C service includes a full inspection — refrigerant levels, '
                 'compressor function, and leak detection — before any recharge.'),
        'checks': ['Refrigerant levels checked',
                   'Compressor function tested',
                   'Leak detection before any recharge',
                   'Weak airflow and warm-air diagnosis',
                   'A/C clutch engagement checked',
                   'Domestic, European, Asian, hybrid and EV vehicles'],
    },
    'transmission-repair-san-diego': {
        'hero': 'engine-wide.webp',
        'h2': 'Catch it early and it stays a fluid service',
        'stats': [('30k<em>-</em>60k', 'Mile fluid interval'),
                  ('<em>3</em> types', 'Automatic, manual, CVT'),
                  ('<em>Full</em> diagnostics', 'Before major repairs'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
        'band': ('What the transmission service covers',
                 'We service automatic, manual, and CVT transmissions, offering fluid '
                 'flushes and diagnostic evaluation for larger repairs.'),
        'checks': ['Automatic, manual and CVT transmissions',
                   'Transmission fluid flush',
                   'Diagnostic evaluation before larger repairs',
                   'Gear slipping and delayed engagement diagnosed',
                   'Harsh shifting investigated',
                   'Fluid leaks traced and repaired'],
    },
    'traction-control-abs-repair': {
        'hero': 'european-bmw.webp',
        'h2': 'A warning light is a fault code, not a mystery',
        'stats': [('<em>Exact</em> fault code', 'Pulled before repair'),
                  ('<em>Targeted</em>', 'No guesswork repairs'),
                  ('<em>3</em> systems', 'ABS, traction, stability'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
        'band': ('How we diagnose the warning light',
                 'These systems rely on wheel-speed sensors, the ABS module, and wiring. '
                 'Our diagnostic process pulls the exact fault code so repairs are targeted.'),
        'checks': ['Exact fault code pulled from the vehicle',
                   'Wheel-speed sensors tested',
                   'ABS module checked',
                   'Wiring and connectors inspected',
                   'Traction control and stability light diagnosis',
                   'Repairs targeted at the actual fault'],
    },
    'cooling-system-repair-san-diego': {
        'hero': 'bay-wide.webp',
        'h2': 'Overheating damage happens in minutes',
        'stats': [('30k<em>-</em>60k', 'Mile flush interval'),
                  ('<em>Minutes</em>', 'Is all overheating needs'),
                  ('<em>4</em> common causes', 'Diagnosed properly'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
        'band': ('What the cooling system service covers',
                 'We perform coolant flushes, hose and belt inspections, and radiator repairs.'),
        'checks': ['Coolant flush',
                   'Radiator leak diagnosis and repair',
                   'Water pump inspection',
                   'Thermostat checked for sticking',
                   'Radiator fan tested',
                   'Hose and belt inspection'],
    },
    'tesla-ev-service-san-diego': {
        'hero': 'vehicles-row.webp',
        'h2': 'Independent EV service without the dealership wait',
        'stats': [('<em>19</em> bays', 'No dealership queue'),
                  ('<em>Same</em> day', 'Service turnaround'),
                  ('<em>12V</em>', 'Auxiliary battery service'),
                  ('<em>Tesla</em> &amp; EV', 'Alongside gas and hybrid')],
        'band': ('What we service on your EV',
                 'We handle the maintenance EV owners still need: tires, brakes, '
                 'suspension and alignment, and 12-volt auxiliary battery testing.'),
        'checks': ['Tire rotation and replacement',
                   'Brake pads, rotors and slide pins',
                   'Suspension work',
                   'Wheel alignment',
                   '12-volt auxiliary battery testing and replacement',
                   'Tesla serviced alongside gas and hybrid vehicles'],
    },
    'windshield-replacement-san-diego': {
        'hero': 'landrover.webp',
        'h2': 'Repair it early, replace it when it matters',
        'stats': [('Under <em>1</em> hr', 'Most chip repairs'),
                  ('<em>ADAS</em>', 'Camera recalibration'),
                  ('<em>Most</em> insurers', 'Billed directly'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
        'band': ('What the windshield service covers',
                 'Small chips and cracks can often be repaired in under an hour if caught '
                 'early, saving you the cost of a full replacement.'),
        'checks': ['Chip and small-crack repair',
                   'Full windshield replacement',
                   'Driver-assist camera recalibration',
                   'Lane-departure and collision-avoidance systems reset',
                   'We work directly with most insurers',
                   'Advice on repair versus replacement'],
    },
    'auto-body-shop-san-diego': {
        'hero': 'collision.webp',
        'h2': 'Everyday bodywork, not just collision claims',
        'stats': [('<em>Upfront</em>', 'Estimate before work'),
                  ('<em>Factory</em> code', 'Paint mixed to match'),
                  ('<em>PDR</em>', 'Paintless dent repair'),
                  ('<em>19</em> bays', 'Kearny Mesa facility')],
        'band': ('What the body shop handles',
                 "Our body shop team handles paintless dent repair for minor dings, full "
                 "panel repainting to match factory color, bumper scuff and scratch repair, "
                 "and rust spot treatment."),
        'checks': ['Paintless dent repair for minor dings',
                   'Full panel repainting to factory color',
                   'Bumper scuff and scratch repair',
                   'Rust spot treatment',
                   'Faded clear coat restored',
                   'Upfront estimate before any work begins'],
    },
}

# Short hero tick lines. Kept identical across pages because they describe the
# shop, not the service — all four are on his live site.
HERO_TICKS = ['ASE-certified technicians', '19-bay facility in Kearny Mesa',
              'Walk-ins welcome', 'Free written estimates']


def esc(s):
    return html.escape(s, quote=False)


def short_service(h1):
    """'Brake Repair & Replacement in San Diego, CA' -> 'Brake Repair & Replacement'."""
    return re.sub(r'\s+in San Diego.*$', '', h1).strip()


def build_fragment(page, cfg, img_base):
    slug = page['slug']
    service = short_service(page['h1'])
    lead = page['paras'][0]
    rest = page['paras'][1:]
    band_h2, band_lead = cfg['band']

    stats = '\n'.join(
        '          <div class="ats-lp__stat"><b>%s</b><span>%s</span></div>' % (n, l)
        for n, l in cfg['stats'])

    certs = '\n'.join(
        '          <img src="%scert/%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">'
        % (img_base, f, esc(a), w, h) for f, a, w, h in CERTS)

    ticks = '\n'.join('          <li>%s%s</li>' % (ICON_TICK, esc(t)) for t in HERO_TICKS)
    checks = '\n'.join('          <li>%s<span>%s</span></li>' % (ICON_CHECK, esc(c))
                       for c in cfg['checks'])
    copy = '\n'.join('          <p>%s</p>' % esc(p) for p in rest)

    faq = '\n'.join(
        '          <details>\n'
        '            <summary>%s</summary>\n'
        '            <p class="ats-lp__faq-a">%s</p>\n'
        '          </details>' % (esc(f['q']), esc(f['a']))
        for f in page['faq'])

    return '''<div class="ats-lp">

  <!-- hero -->
  <section class="ats-lp__hero">
    <div class="ats-lp__hero-bg" style="background-image:url('{img}{hero}')"></div>
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
{copy}
        </div>
        <aside class="ats-lp__aside">
          <h3>Talk to a technician today</h3>
          <p>Tell us what the car is doing and we will tell you what it needs — with a written estimate before any work starts.</p>
          <a class="ats-btn ats-btn--primary" href="{phone_href}">Call {phone}</a>
          <p class="ats-lp__aside-meta">
            <strong>Auto Tech Specialists</strong>
            {address}<br>Walk-ins welcome
          </p>
        </aside>
      </div>
    </div>
  </section>

  <!-- what's covered -->
  <section class="ats-lp__band">
    <div class="ats-lp__band-bg" style="background-image:url('{img}{hero}')"></div>
    <div class="ats-lp__wrap">
      <div class="ats-lp__head">
        <p class="ats-lp__eyebrow">What's included</p>
        <h2 class="ats-lp__h2">{band_h2}</h2>
        <p class="ats-lp__lead">Here is exactly what the service covers when you bring your vehicle to our Kearny Mesa shop.</p>
      </div>
      <ul class="ats-lp__checks">
{checks}
      </ul>
    </div>
  </section>

  <!-- FAQ -->
  <section class="ats-lp__sec ats-lp__sec--alt">
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
        <p>{address} &middot; Walk-ins welcome</p>
      </div>
      <div class="ats-lp__cta-actions">
        <a class="ats-btn ats-btn--primary" href="{phone_href}">Call {phone}</a>
        <a class="ats-btn ats-btn--dark" href="{book}">Book online</a>
      </div>
    </div>
  </section>

</div>
'''.format(img=img_base, hero=cfg['hero'], kicker=esc(page['kicker']), h1=esc(page['h1']),
           lead=esc(lead), phone_href=PHONE_HREF, phone=PHONE_DISPLAY, book=BOOK_URL,
           ticks=ticks, stats=stats, certs=certs, service=esc(service),
           h2=esc(cfg['h2']),
           copy=copy, address=ADDRESS, band_h2=esc(band_h2),
           checks=checks, faq=faq)


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
<link rel="stylesheet" href="css/preview-shell.css">
<link rel="stylesheet" href="css/ats-lp.css">
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
<link rel="stylesheet" href="css/preview-shell.css">
<style>
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
    <h1>10 service landing pages</h1>
    <p>Your copy, your FAQs, your URLs and your schema markup — rebuilt in the site's own
    branding instead of the plain HTML the drafts came in.</p>
    <p>Each page is a self-contained block of content. On the live site your WordPress theme
    supplies the header, menu and footer around it, so nothing here changes your existing design.</p>
    <p><strong>Photos:</strong> the shop images below are from your current site and are stand-ins —
    they get swapped for the shop and vehicle photos you're sending.</p>
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
    pages = json.load(open(CONTENT, encoding='utf-8'))

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

    navlinks = '\n'.join(
        '    <a href="%s.html">%s</a>' % (p['slug'], esc(short_service(p['h1'])))
        for p in pages)

    for page in pages:
        cfg = PAGES[page['slug']]

        # WordPress fragment — images resolve to the media library folder.
        frag_wp = build_fragment(page, cfg, IMG_WP)
        open(os.path.join(WP_OUT, page['slug'] + '.html'), 'w', encoding='utf-8').write(frag_wp)

        # Preview — images resolve locally.
        frag_pv = build_fragment(page, cfg, IMG_PREVIEW)
        out = PREVIEW_SHELL.format(
            title=esc(page['title']), desc=esc(page['metaDesc']),
            canonical=page['canonical'], schema=json.dumps(page['schema'], indent=2),
            navlinks=navlinks, fragment=frag_pv, address=ADDRESS,
            phone_href=PHONE_HREF, phone=PHONE_DISPLAY)
        open(os.path.join(PREVIEW_OUT, page['slug'] + '.html'), 'w', encoding='utf-8').write(out)

    # A contents page so the client has one link to open instead of ten.
    cards = '\n'.join(
        '    <a class="pv-card" href="{slug}.html">'
        '<b>{n}. {name}</b><span>/{slug}/</span><em>{faq} FAQ &middot; {words} words</em></a>'.format(
            slug=p['slug'], n=i + 1, name=esc(short_service(p['h1'])), faq=len(p['faq']),
            words=sum(len(x.split()) for x in p['paras']))
        for i, p in enumerate(pages))
    open(os.path.join(PREVIEW_OUT, 'index.html'), 'w', encoding='utf-8').write(INDEX_SHELL.format(
        cards=cards, address=ADDRESS, phone_href=PHONE_HREF, phone=PHONE_DISPLAY))

    print('built %d pages' % len(pages))
    print('  wp fragments -> %s' % WP_OUT)
    print('  preview      -> %s' % PREVIEW_OUT)


if __name__ == '__main__':
    main()
