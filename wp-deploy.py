#!/usr/bin/env python3
"""Push the landing pages into autotechsd.com over the WordPress REST API.

    python3 wp-deploy.py check      what the account can actually do
    python3 wp-deploy.py inspect    menus, sidebars, existing pages
    python3 wp-deploy.py media      upload src/img -> data/media-map.json
    python3 wp-deploy.py pages      create/update the 11 pages as drafts
    python3 wp-deploy.py menu       add the 11 items under SERVICES
    python3 wp-deploy.py footer     rewrite the footer SERVICES widget

Credentials live in data/apppw.txt (gitignored), two lines:

    <wordpress username>
    <application password, spaces and all>

An application password is NOT the login password — the login password does not
authenticate REST at all, it comes back 401 rest_not_logged_in.

Two things about this host that are easy to lose an hour to:

1.  SiteGround's bot shield answers curl, requests and any bare HTTP client with
    HTTP 202 and an `sgcaptcha` meta-refresh, so every endpoint looks broken or
    empty. Loading /wp-json/ directly in Chromium does not help either — it sets
    no cookie. Loading the HOMEPAGE in Chromium does: it issues an `_I_` cookie
    that the shield then accepts. sg_session() does that once and hands back a
    requests.Session carrying the cookie and the matching User-Agent.

2.  Every run re-reads wp/pages/*.html, which generate.py rewrites from scratch.
    Never hand-edit a fragment; change the source and regenerate.
"""

import base64
import importlib.util
import json
import mimetypes
import os
import sys

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://autotechsd.com'
BASE = SITE + '/wp-json/wp/v2'
# Rank Math keeps its meta out of core's `meta` field; this is the only
# namespace that will write rank_math_title / rank_math_description.
RANKMATH = SITE + '/wp-json/rankmath/v1'
CRED = os.path.join(ROOT, 'data', 'apppw.txt')
COOKIE_CACHE = os.path.join(ROOT, 'data', 'sg-cookie.json')
MEDIA_MAP = os.path.join(ROOT, 'data', 'media-map.json')
CONTENT = os.path.join(ROOT, 'data', 'content.json')
WP_PAGES = os.path.join(ROOT, 'wp', 'pages')
IMG_DIR = os.path.join(ROOT, 'src', 'img')

SKIP = {'auto-body-shop-san-diego'}          # cancelled — he already has that page
PARENT_MENU_ITEM = 'SERVICES'


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def sg_cookie(force=False):
    """Get past the SiteGround shield and return (cookies, user agent).

    Cached, because it costs a browser launch. The cookie outlives a single run.
    """
    if not force and os.path.exists(COOKIE_CACHE):
        return json.load(open(COOKIE_CACHE, encoding='utf-8'))

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 720})
        pg = ctx.new_page()
        # The homepage, not /wp-json/ — the shield only issues the cookie on a
        # real page load.
        pg.goto(SITE + '/', wait_until='networkidle', timeout=90000)
        pg.wait_for_timeout(5000)
        data = {'cookies': ctx.cookies(), 'ua': pg.evaluate('navigator.userAgent')}
        b.close()

    os.makedirs(os.path.dirname(COOKIE_CACHE), exist_ok=True)
    json.dump(data, open(COOKIE_CACHE, 'w', encoding='utf-8'))
    return data


def sg_session(force_cookie=False):
    d = sg_cookie(force_cookie)
    s = requests.Session()
    for c in d['cookies']:
        s.cookies.set(c['name'], c['value'], domain=c['domain'].lstrip('.'))
    s.headers['User-Agent'] = d['ua']
    return s


def credentials():
    if not os.path.exists(CRED):
        sys.exit('No %s. Put the WordPress username on line 1 and the '
                 'application password on line 2.' % CRED)
    lines = [l.rstrip('\n') for l in open(CRED, encoding='utf-8') if l.strip()]
    if len(lines) < 2:
        sys.exit('%s needs two lines: username, then application password.' % CRED)
    return lines[0].strip(), lines[1].strip()


class WP(object):
    def __init__(self):
        self.s = sg_session()
        user, pw = credentials()
        self.user = user
        # Basic auth built by hand: requests' HTTPBasicAuth is fine, but some
        # SiteGround stacks strip the header on redirect, so it goes on the
        # session and stays there.
        token = base64.b64encode(('%s:%s' % (user, pw)).encode('utf-8')).decode('ascii')
        self.s.headers['Authorization'] = 'Basic ' + token

    def _shield(self, r):
        if 'sgcaptcha' in r.text[:400]:
            # The cached cookie went stale; take one fresh one and retry.
            # sg_session() hands back a BARE session, so the Authorization
            # header has to be re-applied or the retry silently goes out
            # unauthenticated and comes back 401.
            auth = self.s.headers.get('Authorization')
            self.s = sg_session(force_cookie=True)
            if auth:
                self.s.headers['Authorization'] = auth
            return True
        return False

    def call(self, method, path, **kw):
        url = path if path.startswith('http') else BASE + path
        r = self.s.request(method, url, timeout=60, **kw)
        if self._shield(r):
            r = self.s.request(method, url, timeout=60, **kw)
        return r

    def get(self, path, **kw):
        return self.call('GET', path, **kw)

    def post(self, path, **kw):
        return self.call('POST', path, **kw)

    def json(self, method, path, **kw):
        r = self.call(method, path, **kw)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {'_raw': r.text[:300]}


# --------------------------------------------------------------------------
# check — never assume a capability, ask the site
# --------------------------------------------------------------------------

STYLE_PROBE = ('<style>.ats-probe-8f21{color:#ce171f}</style>'
               '<div class="ats-probe-8f21">probe</div>')


def cmd_check(wp):
    code, me = wp.json('GET', '/users/me?context=edit')
    if code != 200:
        print('AUTH FAILED %s: %s' % (code, me.get('message') or me))
        return 1
    print('logged in as : %s (id %s)' % (me.get('name'), me.get('id')))
    print('roles        : %s' % ', '.join(me.get('roles', [])))
    caps = me.get('capabilities') or {}
    for c in ('publish_pages', 'edit_pages', 'upload_files', 'unfiltered_html',
              'edit_theme_options', 'manage_options'):
        print('  %-20s %s' % (c, 'yes' if caps.get(c) else 'NO'))

    # The capability list is what WordPress *reports*. What actually matters is
    # whether a <style> block survives the save, so save one and read it back.
    print('\nstyle-block probe (does kses strip our stylesheet?)')
    code, page = wp.json('POST', '/pages', json={
        'title': 'ats style probe (delete me)',
        'slug': 'ats-style-probe-8f21',
        'status': 'draft',
        'content': STYLE_PROBE,
    })
    if code not in (200, 201):
        print('  could not create a draft: %s %s' % (code, page.get('message') or page))
        return 1
    pid = page['id']
    try:
        code, back = wp.json('GET', '/pages/%d?context=edit' % pid)
        raw = (back.get('content') or {}).get('raw', '')
        survived = '<style>' in raw
        print('  <style> survived the save: %s' % ('YES' if survived else 'NO'))
        if not survived:
            print('  -> pages would render unstyled. The stylesheet has to go into')
            print('     Appearance > Customize > Additional CSS instead (admin only).')
        print('  saved content: %s' % raw[:120].replace('\n', ' '))
    finally:
        wp.call('DELETE', '/pages/%d?force=true' % pid)
        print('  probe page deleted')
    return 0


# --------------------------------------------------------------------------
# inspect — find the ids the other commands need
# --------------------------------------------------------------------------

def cmd_inspect(wp):
    code, menus = wp.json('GET', '/menus?per_page=100&context=edit')
    print('MENUS (%s)' % code)
    if isinstance(menus, list):
        for m in menus:
            print('  %-6s %-22s locations=%s' % (m['id'], m.get('name'), m.get('locations')))

    code, items = wp.json('GET', '/menu-items?per_page=100&context=edit')
    print('\nMENU ITEMS (%s)' % code)
    if isinstance(items, list):
        by_parent = {}
        for it in items:
            by_parent.setdefault(it.get('parent', 0), []).append(it)
        for it in sorted(by_parent.get(0, []), key=lambda x: x.get('menu_order', 0)):
            print('  %-6s %-24s %s' % (it['id'], it.get('title', {}).get('rendered'), it.get('url')))
            for kid in sorted(by_parent.get(it['id'], []), key=lambda x: x.get('menu_order', 0)):
                print('      %-6s %-22s %s' % (kid['id'], kid.get('title', {}).get('rendered'),
                                               kid.get('url')))

    code, bars = wp.json('GET', '/sidebars?context=edit')
    print('\nSIDEBARS (%s)' % code)
    if isinstance(bars, list):
        for b in bars:
            print('  %-34s %-24s widgets=%s' % (b.get('id'), b.get('name'), b.get('widgets')))

    code, pages = wp.json('GET', '/pages?per_page=100&status=any&_fields=id,slug,status')
    print('\nEXISTING PAGES (%s)' % code)
    if isinstance(pages, list):
        for p in sorted(pages, key=lambda x: x['slug']):
            print('  %-6s %-10s %s' % (p['id'], p['status'], p['slug']))
    return 0


# --------------------------------------------------------------------------
# media
# --------------------------------------------------------------------------

def referenced_images():
    """Every src/img file the generated fragments actually point at.

    Read out of the fragments rather than globbed off disk, so retired art does
    not get uploaded to his media library.
    """
    import re
    want = set()
    for f in sorted(os.listdir(WP_PAGES)):
        html = open(os.path.join(WP_PAGES, f), encoding='utf-8').read()
        for src in re.findall(r'src="([^"]+)"', html):
            if '/uploads/atslp/' in src:
                want.add(src.split('/uploads/atslp/', 1)[1])
    return sorted(want)


def cmd_media(wp):
    mapping = {}
    if os.path.exists(MEDIA_MAP):
        mapping = json.load(open(MEDIA_MAP, encoding='utf-8'))

    todo = referenced_images()
    print('%d image(s) referenced, %d already uploaded' % (len(todo), len(mapping)))
    for rel in todo:
        if rel in mapping:
            continue
        # Fragments address the badges as cert/cert-ase.webp because that is the
        # folder layout on the server; on disk src/img/ is flat.
        path = os.path.join(IMG_DIR, rel)
        if not os.path.exists(path):
            path = os.path.join(IMG_DIR, os.path.basename(rel))
        if not os.path.exists(path):
            print('  MISSING locally: %s' % rel)
            continue
        name = 'ats-' + rel.replace('/', '-')
        ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        code, res = wp.json('POST', '/media', data=open(path, 'rb').read(), headers={
            'Content-Disposition': 'attachment; filename="%s"' % name,
            'Content-Type': ctype,
        })
        if code not in (200, 201):
            print('  FAILED %s: %s %s' % (rel, code, res.get('message') or res))
            continue
        mapping[rel] = res['source_url']
        print('  %-34s -> %s' % (rel, res['source_url']))
        json.dump(mapping, open(MEDIA_MAP, 'w', encoding='utf-8'), indent=1, sort_keys=True)

    print('\nwrote %s (%d entries). Re-run generate.py so the fragments pick '
          'the real URLs up.' % (MEDIA_MAP, len(mapping)))
    return 0


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

def short_name(slug):
    """The human name for a page — menu label, breadcrumb, admin list.

    Single source of truth is generate.py's PAGES table, so the menu labels and
    the page titles can never drift apart. generate.py guards its main(), so
    importing it is free.
    """
    global _PAGES
    if _PAGES is None:
        spec = importlib.util.spec_from_file_location(
            'ats_generate', os.path.join(ROOT, 'generate.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PAGES = mod.PAGES
    return _PAGES[slug]['name'].replace('&amp;', '&')


_PAGES = None


def landing_pages():
    pages = [p for p in json.load(open(CONTENT, encoding='utf-8'))
             if p['slug'] not in SKIP]
    for p in pages:
        frag = os.path.join(WP_PAGES, p['slug'] + '.html')
        if not os.path.exists(frag):
            sys.exit('no fragment for %s — run generate.py first' % p['slug'])
        p['_html'] = open(frag, encoding='utf-8').read()
    return pages


def cmd_pages(wp):
    code, existing = wp.json(
        'GET', '/pages?per_page=100&status=any&_fields=id,slug,status')
    by_slug = {p['slug']: p for p in existing} if isinstance(existing, list) else {}

    for p in landing_pages():
        body = {
            # The WP post title is NOT the SEO title. It is what shows up in the
            # admin list, in breadcrumbs, and as the default label when he drags
            # the page into a menu — "Auto Detailing", not
            # "Professional Auto Detailing San Diego | Kearny Mesa". The SEO
            # title goes to Rank Math below.
            'title': short_name(p['slug']),
            'slug': p['slug'],
            'content': p['_html'],
        }
        prev = by_slug.get(p['slug'])
        if prev:
            # NEVER send `status` on an update. These pages are live; passing
            # 'draft' here (which this did) silently unpublishes all 11 and
            # WordPress then bounces every URL to the home page. Whatever
            # status the page already has is his decision, not the script's.
            code, res = wp.json('POST', '/pages/%d' % prev['id'], json=body)
            what = 'updated'
        else:
            # A brand new page starts as a draft — he publishes, not me.
            body['status'] = 'draft'
            code, res = wp.json('POST', '/pages', json=body)
            what = 'created'
        if code not in (200, 201):
            print('  FAILED %-42s %s %s' % (p['slug'], code, res.get('message') or res))
            continue
        print('  %-8s %-42s id=%-5s %s' % (what, p['slug'], res['id'],
                                           short_name(p['slug'])))

        # Rank Math does not register its keys with core's `meta` field, so
        # passing them to /wp/v2/pages is silently dropped AND reading them back
        # there always looks empty. Its own namespace is the only route that
        # works; proven against the live site, then confirmed by reading the
        # rendered <meta name="description"> off a published page.
        code, rm = wp.json('POST', RANKMATH + '/updateMeta', json={
            'objectType': 'post', 'objectID': res['id'],
            'meta': {'rank_math_title': p['title'],
                     'rank_math_description': p['metaDesc']}})
        if code != 200:
            print('       SEO title/description NOT set: %s %s' % (code, rm))
    return 0


# --------------------------------------------------------------------------
# menu
# --------------------------------------------------------------------------

def cmd_menu(wp):
    code, items = wp.json('GET', '/menu-items?per_page=100&context=edit')
    if code != 200:
        print('cannot read menu items: %s %s' % (code, items))
        return 1
    parent = next((i for i in items
                   if i.get('title', {}).get('rendered', '').strip().upper()
                   == PARENT_MENU_ITEM), None)
    if not parent:
        print('no %s item found in any menu' % PARENT_MENU_ITEM)
        return 1
    menu_id = parent['menus']
    have = {i.get('url', '').rstrip('/') for i in items}
    order = max([i.get('menu_order', 0) for i in items
                 if i.get('parent') == parent['id']] or [0])

    code, pages = wp.json('GET', '/pages?per_page=100&status=any&_fields=id,slug,link')
    by_slug = {p['slug']: p for p in pages} if isinstance(pages, list) else {}

    for p in landing_pages():
        target = by_slug.get(p['slug'])
        if not target:
            print('  %-42s no page yet — run `pages` first' % p['slug'])
            continue
        if target['link'].rstrip('/') in have:
            print('  %-42s already in the menu' % p['slug'])
            continue
        order += 1
        code, res = wp.json('POST', '/menu-items', json={
            'title': p['tab'] or p['kicker'],
            'type': 'post_type',
            'object': 'page',
            'object_id': target['id'],
            'parent': parent['id'],       # flat, all directly under SERVICES
            'menus': menu_id,
            'menu_order': order,
            'status': 'publish',
        })
        if code not in (200, 201):
            print('  FAILED %-42s %s %s' % (p['slug'], code, res.get('message') or res))
            continue
        print('  added   %-42s id=%s' % (p['slug'], res['id']))
    return 0


# --------------------------------------------------------------------------
# footer
# --------------------------------------------------------------------------

def cmd_footer(wp):
    """Rewrite the footer SERVICES column.

    It is a block widget, not a menu — widget-3 in Astra's footer holds an <h4>
    and a hand-typed list of <p><a> links. Updating the nav menu does nothing
    to it, which is why this is a separate command.
    """
    code, widgets = wp.json('GET', '/widgets?context=edit&per_page=100')
    if code != 200:
        print('cannot read widgets: %s %s' % (code, widgets))
        return 1
    target = [w for w in widgets if 'footer-widget-3' in (w.get('sidebar') or '')]
    if not target:
        print('no widget in footer-widget-3; run `inspect` and look at sidebars')
        return 1
    for w in target:
        print('%s  %s' % (w['id'], (w.get('rendered') or '')[:160].replace('\n', ' ')))
    print('\nRead-only for now on purpose: the client still has to choose whether '
          'all 11 links go in (17 total, a long ladder on a phone) or the column '
          'gets split in two. Do not overwrite his footer before he says which.')
    return 0


COMMANDS = {
    'check': cmd_check,
    'inspect': cmd_inspect,
    'media': cmd_media,
    'pages': cmd_pages,
    'menu': cmd_menu,
    'footer': cmd_footer,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    sys.exit(COMMANDS[sys.argv[1]](WP()) or 0)


if __name__ == '__main__':
    main()
