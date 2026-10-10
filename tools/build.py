#!/usr/bin/env python3
"""One-time migration tool: turns the crawled Joomla site into the static site.

The published site does NOT need this (no build step on GitHub Pages). It is kept
so the conversion can be re-run from a fresh crawl.

    python3 -I tools/build.py <crawl-dir> <images-dir> <downloads.json>

<crawl-dir>     wget mirror of https://stmarydamshiria.com/ (stmarydamshiria.com/)
<images-dir>    the /images/... tree downloaded from the live site
<downloads.json> id -> {title,size,file,local} for the Phoca Download files
"""
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True  # a few originals are truncated on the live server too

ROOT = Path(__file__).resolve().parent.parent
CRAWL = Path(sys.argv[1])
IMAGES = Path(sys.argv[2])
DOWNLOADS = json.load(open(sys.argv[3], encoding='utf-8'))
HOSTS = ('https://stmarydamshiria.com', 'http://stmarydamshiria.com',
         'https://www.stmarydamshiria.com', 'http://www.stmarydamshiria.com')
SPAM = ('xxxhub', 'farmakosha')
LOG = {'unknown_links': {}, 'dead_embeds': [], 'images': set(), 'webp': []}

# Downloads kept inside the repo (small, valid files). Everything else is served
# from MEDIA_BASE (assets/js/config.js), see README "Audio and large files".
CORRUPT_ON_LIVE = {'3', '7', '8', '13', '16'}   # served garbled by the live server
NEVER_IN_REPO_EXT = ('.exe',)
IN_REPO_MAX = 3_000_000


# ---------------------------------------------------------------- url mapping
def seg_clean(s):
    return re.sub(r'\s+', '-', s.strip())


def key_from_file(rel):
    """crawl file path -> canonical page key ('' = home)."""
    k = rel[:-5] if rel.endswith('.html') else rel
    k = k.replace('?start=20', '/page-2')
    if k == 'index':
        return ''
    return '/'.join(seg_clean(s) for s in k.split('/'))


def out_path(key):
    return ROOT / key / 'index.html' if key else ROOT / 'index.html'


def rel_url(from_key, to_key):
    """relative URL from page from_key to page to_key (directory style)."""
    depth = len(from_key.split('/')) if from_key else 0
    r = '../' * depth + (to_key + '/' if to_key else '')
    return r or './'


def rel_asset(from_key, asset):
    depth = len(from_key.split('/')) if from_key else 0
    return '../' * depth + asset


PAGES = {}
for p in sorted(CRAWL.rglob('*.html')):
    rel = str(p.relative_to(CRAWL))
    k = key_from_file(rel)
    if k in PAGES:            # duplicate variant (trailing-space slug)
        continue
    PAGES[k] = p

# the live menu links to three pages that already answer 404 on the live site;
# they get small stand-in pages (see inventory)
STUBS = {
    'spirituals/seneksar': 'السنكسار',
    'spirituals/katamaras': 'القطمارس',
    'spirituals/bible/bible-read': 'قراءة الكتاب المقدس',
}


def map_href(href, from_key):
    """Return (new_href or None to unwrap, kind)."""
    if href is None:
        return None, 'none'
    h = html.unescape(href).strip()
    if any(s in h for s in SPAM):
        return None, 'spam'
    if h.startswith(('mailto:', 'tel:', 'javascript:')):
        return h, 'other'
    if h.startswith('#'):
        return h, 'anchor'
    if not h.startswith(('/', 'http', 'index.php')):
        return h, 'local'      # already rewritten by a section builder
    for host in HOSTS:
        if h.startswith(host):
            h = h[len(host):] or '/'
            break
    else:
        if re.match(r'^https?://', h):
            if 'damshiria.com' in h or 'damshiria.net' in h:
                return h, 'old-host'
            return h, 'external'
    if not h.startswith('/'):
        h = '/' + h
    h = urllib.parse.unquote(h)
    path, _, query = h.partition('?')
    path, _, frag = path.partition('#')
    q = urllib.parse.parse_qs(query)
    if 'download' in q:
        i = q['download'][0].split(':')[0]
        return ('download', i), 'download'
    if '/detail/' in path and 'icons' in path:
        return ('icon', path.rsplit('/', 1)[-1]), 'icon'
    path = path.strip('/')
    if path.endswith('.html'):
        path = path[:-5]
    if path in ('index.php', ''):
        if query and 'option=' in query:
            LOG['unknown_links'].setdefault(href, set()).add(from_key)
            return None, 'unknown'
        path = ''
    if q.get('start') == ['20']:
        path += '/page-2'
    key = '/'.join(seg_clean(s) for s in path.split('/')) if path else ''
    if key.startswith(('images/', 'components/', 'media/')):
        return ('file', key), 'file'
    if key in PAGES or key in STUBS:
        return rel_url(from_key, key) + (('#' + frag) if frag else ''), 'page'
    LOG['unknown_links'].setdefault(href, set()).add(from_key)
    return None, 'unknown'


# ---------------------------------------------------------------- images
def asset_image(src_path):
    """copy /images/... into assets/img/content/..., webp for large ones. returns repo path."""
    src_path = urllib.parse.unquote(src_path).lstrip('/')
    src = IMAGES / src_path
    if not src.exists():
        return None
    sub = src_path[len('images/'):] if src_path.startswith('images/') else src_path
    sub = '/'.join(re.sub(r'\s+', '-', s) for s in sub.split('/'))
    dst = ROOT / 'assets/img/content' / sub
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.stat().st_size > 120_000 and src.suffix.lower() in ('.jpg', '.jpeg', '.png'):
        dst = dst.with_suffix('.webp')
        if not dst.exists():
            im = Image.open(src)
            im.save(dst, 'WEBP', quality=86, method=6)
            LOG['webp'].append((src_path, src.stat().st_size, dst.stat().st_size))
    elif not dst.exists():
        shutil.copy2(src, dst)
    rel = str(dst.relative_to(ROOT))
    LOG['images'].add(rel)
    return rel


# ---------------------------------------------------------------- downloads
def download_entry(i):
    d = DOWNLOADS.get(i)
    if not d:
        return None
    fname = d['file'] or f'file-{i}'
    in_repo = (d['local'] and i not in CORRUPT_ON_LIVE and not fname.lower().endswith(NEVER_IN_REPO_EXT)
               and (CRAWL / d['local']).stat().st_size <= IN_REPO_MAX)
    safe = re.sub(r'[^A-Za-z0-9._-]+', '-', fname)
    if in_repo:
        dst = ROOT / 'assets/downloads' / safe
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(CRAWL / d['local'], dst)
        return {'repo': f'assets/downloads/{safe}', 'name': fname, **d}
    return {'media': fname, 'orig': d['href'], **d}


def download_link(soup, i, from_key, label=None):
    e = download_entry(i)
    if not e:
        return None
    a = soup.new_tag('a')
    a.string = label or e['title']
    if 'repo' in e:
        a['href'] = rel_asset(from_key, e['repo'])
        a['download'] = e['name']
    else:
        # resolved at runtime from MEDIA_BASE (assets/js/config.js)
        a['href'] = 'https://stmarydamshiria.com' + e['orig']
        a['data-media'] = e['media']
        a['data-orig'] = e['orig']
    return a


# ---------------------------------------------------------------- page cleanup
EMAIL_CLOAK = re.compile(
    r"<script[^>]*>\s*<!--\s*var prefix = '([^']*)';.*?var (addy\d+) = (.*?);\s*\2 = \2 \+ (.*?);\s*document\.write.*?"
    r"</script>.*?<script[^>]*>\s*<!--\s*document\.write\( '</' \);\s*document\.write\( 'span>' \);\s*//-->\s*</script>",
    re.S)


def decloak(raw):
    def rep(m):
        parts = re.findall(r"'([^']*)'", m.group(3) + '+' + m.group(4))
        addr = html.unescape(''.join(parts))
        return f'<a href="mailto:{addr}">{addr}</a>'
    return EMAIL_CLOAK.sub(rep, raw)


def youtube_iframe(soup, vid):
    wrap = soup.new_tag('div', attrs={'class': 'video-embed'})
    ifr = soup.new_tag('iframe', attrs={
        'src': f'https://www.youtube-nocookie.com/embed/{vid}', 'title': 'YouTube',
        'loading': 'lazy', 'allowfullscreen': '', 'frameborder': '0',
        'allow': 'accelerometer; encrypted-media; gyroscope; picture-in-picture'})
    wrap.append(ifr)
    return wrap


def convert_embeds(soup, key):
    for obj in list(soup.find_all(['object', 'embed'])):
        if obj.parent is None:
            continue
        txt = str(obj)
        m = re.search(r'youtube\.com/v/([A-Za-z0-9_-]{11})', txt)
        if m:
            obj.replace_with(youtube_iframe(soup, m.group(1)))
            continue
        m = re.search(r'vid=(\d+)', txt)
        if 'ustream' in txt:
            LOG['dead_embeds'].append((key, 'ustream', m.group(1) if m else ''))
            box = soup.new_tag('div', attrs={'class': 'dead-embed', 'data-ustream-vid': m.group(1) if m else ''})
            box.string = 'هذا التسجيل كان على Ustream ولم يعد متاحًا.'
            obj.replace_with(box)
            continue
        if 'plist.asx' in txt or 'mplayer' in txt:
            continue   # handled by the live-sound page builder
        LOG['dead_embeds'].append((key, 'object', txt[:80]))


def clean_fragment(soup, node, key):
    for c in node.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for e in node.select('.art-nostyle'):
        if e.find('a', class_='twitter-share-button'):
            e.replace_with(BeautifulSoup('<div class="art-nostyle"><p style="text-align: center;">'
                                         '<a class="share-x" href="https://twitter.com/intent/tweet" target="_blank" '
                                         'rel="noopener">شارك على تويتر</a></p></div>', 'html.parser'))
    for sel in ['a[name=fb_share]']:
        for e in node.select(sel):
            e.decompose()
    for ifr in node.find_all('iframe'):
        src = ifr.get('src', '')
        if 'facebook.com/plugins' in src:
            p = ifr.parent
            ifr.decompose()
            if p and p.name == 'p' and not p.get_text(strip=True) and not p.find(['img', 'iframe']):
                p.decompose()
    for a in node.find_all('a'):
        href = a.get('href')
        if href is None:
            continue
        new, kind = map_href(href, key)
        if kind == 'spam':
            a.decompose()
        elif kind == 'download':
            dl = download_link(soup, new[1], key, a.get_text())
            if dl:
                a.replace_with(dl)
            else:
                a.unwrap()
        elif kind == 'icon':
            a['href'] = '#'
        elif kind == 'file':
            r = asset_image(new[1])
            if r:
                a['href'] = rel_asset(key, r)
            else:
                a.unwrap()
        elif new is None:
            if a.get_text(strip=True) or a.find('img'):
                a.unwrap()
            else:
                a.decompose()
        else:
            a['href'] = new
        if a.parent is not None:
            for at in ('mce_href', 'onmouseover', 'onmouseout'):
                if at in a.attrs:
                    del a[at]
    for img in node.find_all('img'):
        src = img.get('src', '')
        for host in HOSTS:
            if src.startswith(host):
                src = src[len(host):]
        src = re.sub(r'^/+', '/', src)
        if src.startswith('/images/'):
            r = asset_image(src)
            if r:
                img['src'] = rel_asset(key, r)
                if r.endswith('.webp'):
                    try:
                        w, h = Image.open(ROOT / r).size
                        img.attrs.setdefault('width', str(w))
                    except Exception:
                        pass
            else:
                img.decompose()
                continue
        elif src.startswith('/components/') or src.startswith('/modules/'):
            img.decompose()
            continue
        elif src.startswith('http://'):
            img['src'] = 'https://' + src[7:]
        for at in ('mce_src', 'mce_style'):
            if at in img.attrs:
                del img[at]
        img['loading'] = 'lazy'
    for s in node.find_all('script'):
        s.decompose()
    for sel in node.find_all(['select']):
        p = sel.find_parent(['div', 'td', 'form']) or sel
        p.decompose()
    for e in node.find_all(string=re.compile(r'Powered by|Display Num')):
        par = e.parent
        if par is not None and par.name not in ('body', '[document]'):
            par.decompose()
    convert_embeds(soup, key)


# ---------------------------------------------------------------- special sections
def build_slider(soup, node, key):
    """DJ Image Slider -> static slider (assets/js/site.js)."""
    for loader in node.select('.djslider-loader'):
        slides = []
        for li in loader.select('li'):
            a = li.find('a')
            img = li.find('img')
            if not img or not img.get('src', '').lstrip('/').startswith('images/'):
                continue   # live slide points at a missing /blank.png
            slides.append((a.get('href') if a else None, img.get('src'), img.get('alt', '')))
        box = soup.new_tag('div', attrs={'class': 'slider', 'data-delay': '3600', 'aria-roledescription': 'carousel'})
        track = soup.new_tag('div', attrs={'class': 'slider-track'})
        for href, src, alt in slides:
            slide = soup.new_tag('div', attrs={'class': 'slide'})
            r = asset_image(src)
            im = soup.new_tag('img', attrs={'src': rel_asset(key, r) if r else src, 'alt': alt})
            if href:
                new, kind = map_href(href, key)
                a = soup.new_tag('a', attrs={'href': new or '#'})
                a.append(im)
                slide.append(a)
            else:
                slide.append(im)
            track.append(slide)
        box.append(track)
        for cls, label, sym in (('slider-prev', 'السابق', '‹'), ('slider-next', 'التالي', '›')):
            b = soup.new_tag('button', attrs={'class': cls, 'type': 'button', 'aria-label': label})
            b.string = sym
            box.append(b)
        pp = soup.new_tag('button', attrs={'class': 'slider-pause', 'type': 'button', 'aria-label': 'إيقاف/تشغيل'})
        pp.string = '❚❚'
        box.append(pp)
        loader.replace_with(box)
    for s in node.select('div[style*="clear: both"]'):
        pass


def build_gallery(soup, node, key, raw):
    """Phoca Gallery -> grid + lightbox."""
    pg = node.find(id='phocagallery')
    if not pg:
        return
    items = []
    for box in pg.select('.phocagallery-box-file'):
        a = box.find('a', class_='modal-button')
        img = box.find('img')
        if not img or 'phoca_thumb_m_' not in img.get('src', ''):
            continue
        fname = img['src'].split('phoca_thumb_m_')[-1]
        thumb = asset_image(img['src'])
        large = asset_image(f'/images/phocagallery/icons/{fname}') or asset_image(
            f'/images/phocagallery/icons/thumbs/phoca_thumb_l_{fname}')
        title = (a.get('title') if a else '') or img.get('alt', '')
        items.append((thumb, large, title))
    grid = soup.new_tag('div', attrs={'class': 'gallery'})
    for thumb, large, title in items:
        fig = soup.new_tag('figure', attrs={'class': 'gallery-item'})
        a = soup.new_tag('a', attrs={'href': rel_asset(key, large or thumb), 'class': 'lightbox', 'title': title})
        a.append(soup.new_tag('img', attrs={'src': rel_asset(key, thumb), 'alt': title, 'loading': 'lazy'}))
        fig.append(a)
        cap = soup.new_tag('figcaption')
        cap.string = title if len(title) <= 16 else title[:15] + '...'
        fig.append(cap)
        grid.append(fig)
    # pagination exactly like the live page (20 per page)
    nav = None
    for pag in node.select('.pagination, .pagenav, div.pgcenter, .phocagallery-pagination, .pg-center'):
        nav = pag
    pg.replace_with(grid)
    pager = soup.new_tag('div', attrs={'class': 'gallery-pager'})
    base = key.replace('/page-2', '')
    for label, k in (('1', base), ('2', base + '/page-2')):
        if k in PAGES:
            if k == key:
                s = soup.new_tag('span', attrs={'class': 'current'})
                s.string = label
                pager.append(s)
            else:
                a = soup.new_tag('a', attrs={'href': rel_url(key, k)})
                a.string = label
                pager.append(a)
    grid.insert_after(pager)
    for e in node.select('.pagination, .pgcenter, .pg-center, .pagenav, form[name=adminForm]'):
        if e.parent is not None and not e.find(class_='gallery'):
            e.decompose()


def build_downloads(soup, node, key):
    """Phoca Download tables -> file list with inline audio player."""
    for row in node.select('td.pdfile'):
        pass
    for a in node.select('.pdplay a, a[href*="/downloads/play/"]'):
        m = re.search(r'/play/(\d+)', a.get('href', ''))
        if m:
            e = download_entry(m.group(1))
            b = soup.new_tag('button', attrs={'type': 'button', 'class': 'play-btn',
                                              'data-media': e.get('media', '') if e else '',
                                              'data-src': rel_asset(key, e['repo']) if e and 'repo' in e else ''})
            b.string = 'Play'
            a.replace_with(b)
    for a in node.select('.pddetails a'):
        a.unwrap()
    for f in node.select('form[name=adminForm]'):
        f.unwrap()


def prayer_form(soup, key):
    html_ = '''
<form class="prayer-form" action="https://formspree.io/f/FORM_ID" method="post" data-mailto="PRAYER_EMAIL">
 <fieldset class="mod"><legend>ارسل طلبة</legend>
  <p><label for="newrequester">اسمك: (لابد من كتابة الاسم)</label><br />
  <input type="text" name="newrequester" id="newrequester" class="inputbox" required /></p>
  <p><label for="newemail">البريد الاكترونى الخاص بك: (اختيارى)</label><br />
  <input type="email" name="newemail" id="newemail" class="inputbox" /></p>
  <p><label for="newrequest">طلبة الصلاة:</label><br />
  <textarea name="newrequest" id="newrequest" rows="12" required></textarea></p>
  <p><input type="checkbox" name="private" id="psend" value="1" /> <label for="psend">لا تعرضها على الموقع</label></p>
  <input type="text" name="_gotcha" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
  <p><button type="submit" class="button art-button">ارسل</button></p>
  <p class="form-status" role="status"></p>
 </fieldset>
</form>'''
    return BeautifulSoup(html_, 'html.parser')


# ---------------------------------------------------------------- chrome
HOME_RAW = (CRAWL / 'index.html').read_text(encoding='utf-8')
HOME = BeautifulSoup(HOME_RAW, 'lxml')
MENU = HOME.select_one('ul.art-menu')


def nav_html(key):
    m = BeautifulSoup(str(MENU), 'html.parser').ul
    for li in m.find_all('li'):
        li.attrs.pop('id', None)
        li['class'] = [c for c in li.get('class', []) if c == 'parent']
    for a in m.find_all('a'):
        a.attrs.pop('onclick', None)
        cls = [c for c in a.get('class', []) if c == 'separator']
        href = a.get('href')
        if href == '#':
            a['href'] = '#'
            a['role'] = 'button'
        else:
            new, kind = map_href(href, key)
            a['href'] = new or '#'
            target = href.replace('https://stmarydamshiria.com', '').strip('/')
            if target == key or (target and key.startswith(target + '/')) or (target == '' and key == ''):
                cls.append('active')
        a['class'] = cls
        if not a['class']:
            del a['class']
    return str(m)


SIDEBAR = '''<div class="art-sidebar2"><div class="art-Block">
  <div class="art-Block-tl"></div><div class="art-Block-tr"></div><div class="art-Block-bl"></div><div class="art-Block-br"></div>
  <div class="art-Block-tc"></div><div class="art-Block-bc"></div><div class="art-Block-cl"></div><div class="art-Block-cr"></div><div class="art-Block-cc"></div>
  <div class="art-Block-body">
   <div class="art-BlockHeader"><div class="l"></div><div class="r"></div><div class="art-header-tag-icon"><div class="t">القراءات اليومية</div></div></div>
   <div class="art-BlockContent">
    <div class="art-BlockContent-tl"></div><div class="art-BlockContent-tr"></div><div class="art-BlockContent-bl"></div><div class="art-BlockContent-br"></div>
    <div class="art-BlockContent-tc"></div><div class="art-BlockContent-bc"></div><div class="art-BlockContent-cl"></div><div class="art-BlockContent-cr"></div><div class="art-BlockContent-cc"></div>
    <div class="art-BlockContent-body">
     <div class="readings" dir="rtl">
      <div class="r-title">اليوم</div>
      <div class="r-date" data-coptic-date>&nbsp;</div>
      <div class="r-head">قراءات اليوم</div>
      <a class="r-link" data-readings-link href="https://katamars.avabishoy.com/" target="_blank" rel="noopener">القطمارس (العشية، باكر، القداس)</a>
      <div class="r-head">السنكسار</div>
      <a class="r-link" data-synax-link href="https://katamars.avabishoy.com/" target="_blank" rel="noopener">سنكسار اليوم</a>
     </div>
     <div class="cleared"></div>
    </div>
   </div>
   <div class="cleared"></div>
  </div>
</div></div>'''


def page_html(key, title, main_html, extra_head=''):
    css = rel_asset(key, 'assets/css/')
    js = rel_asset(key, 'assets/js/')
    home = rel_url(key, '')
    header_img = rel_asset(key, 'assets/img/content/stories/sanawy.png')
    return f'''<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="كنيسة السيدة العذراء الدمشيرية" />
<meta name="keywords" content="كنيسة السيدة العذراء الدمشيرية" />
<link rel="icon" href="{rel_asset(key, 'favicon.ico')}" type="image/x-icon" />
<link rel="stylesheet" href="{css}variables.css" />
<link rel="stylesheet" href="{css}template.css" />
<link rel="stylesheet" href="{css}site.css" />
{extra_head}</head>
<body>
<div id="art-main">
<div class="art-Sheet">
 <div class="art-Sheet-tl"></div><div class="art-Sheet-tr"></div><div class="art-Sheet-bl"></div><div class="art-Sheet-br"></div>
 <div class="art-Sheet-tc"></div><div class="art-Sheet-bc"></div><div class="art-Sheet-cl"></div><div class="art-Sheet-cr"></div><div class="art-Sheet-cc"></div>
 <div class="art-Sheet-body">
<div class="art-Header">
 <div class="art-Header-jpeg"><a href="{home}" class="header-home" aria-label="الرئيسية"><img src="{header_img}" alt="" width="134" height="180" class="header-icon" /></a></div>
</div>
<nav class="art-nav" aria-label="القائمة الرئيسية">
 <div class="l"></div><div class="r"></div>
 <button type="button" class="menu-toggle" aria-expanded="false" aria-controls="main-menu">القائمة ☰</button>
 <div class="art-nav-center" id="main-menu">
{nav_html(key)}
 </div>
</nav>
<div class="art-contentLayout">
{main_html}
{SIDEBAR}
</div>
<div class="cleared"></div>
<footer class="art-Footer">
 <div class="art-Footer-inner">
  <div class="art-Footer-text">
  <p class="footer-p">جميع الحقوق محفوظة <br/>كنيسة السيدة العذراء الدمشيرية</p>
  </div>
 </div>
 <div class="art-Footer-background"></div>
</footer>
<div class="cleared"></div>
 </div>
</div>
<div class="cleared"></div>
</div>
<script src="{js}config.js"></script>
<script src="{js}site.js"></script>
</body>
</html>
'''


def build_page(key, path):
    raw = path.read_text(encoding='utf-8', errors='replace')
    raw = decloak(raw)
    soup = BeautifulSoup(raw, 'lxml')
    t = soup.title.get_text(strip=True) if soup.title else 'كنيسة السيدة العذراء الدمشيرية'
    main = soup.select_one('.art-content-sidebar1') or soup.select_one('.art-content')
    if key.startswith('ancient-church/icons'):
        build_gallery(soup, main, key, raw)
    if main.select('.djslider-loader'):
        build_slider(soup, main, key)
    if key.startswith('downloads') or key == 'spirituals/books':
        build_downloads(soup, main, key)
    extra = ''
    if key == 'prayer-requests':
        content = main.select_one('.art-PostContent')
        intro = None
        for d in content.find_all('div'):
            if d.get_text(strip=True).startswith('سوف يتم وضع هذه الطلبات'):
                intro = d.get_text(strip=True)
                break
        content.clear()
        p = soup.new_tag('p')
        p.string = intro or ''
        content.append(p)
        content.append(prayer_form(soup, key))
    if key == 'live/live-sound':
        build_live_sound(soup, main)
    if key == 'live/live-video':
        for ifr in main.find_all('iframe'):
            if 'damshiria.com/live.htm' in ifr.get('src', ''):
                ifr['src'] = 'https://damshiria.com/live.htm'
                ifr['class'] = 'live-frame'
                ifr['title'] = 'بث مباشر'
                ifr['loading'] = 'lazy'
    if key == 'spirituals/bible/bible-listen':
        cfg = ''
        for s in soup.find_all('script'):
            if 'alenjil_width' in (s.string or ''):
                cfg = s.string
        holder = soup.new_tag('div', attrs={'class': 'alenjil-holder'})
        art = main.select_one('.art-article')
        for s in art.find_all('script'):
            s.decompose()
        art.insert(0, holder)
        extra_js = (cfg or '').replace('// <![CDATA[', '').replace('// ]]>', '')
        extra = ''
        holder['data-alenjil'] = '1'
        holder.append(BeautifulSoup(f'<script>{extra_js}</script><script src="https://alenjil.com/alenjil.js" charset="windows-1256"></script>', 'html.parser'))
        keep = str(holder)
        holder.replace_with(soup.new_tag('div', attrs={'id': 'alenjil-placeholder'}))
    else:
        keep = None
    clean_fragment(soup, main, key)
    main_html = str(main)
    if keep:
        main_html = main_html.replace('<div id="alenjil-placeholder"></div>', keep)
    # drop empty article separators and leftover onclick
    main_html = re.sub(r'\s(onclick|onmouseover|onmouseout|mce_[a-z]+)="[^"]*"', '', main_html)
    main_html = re.sub(r'\n\s*\n+', '\n', main_html)
    out = out_path(key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_html(key, t, main_html, extra), encoding='utf-8')


def build_live_sound(soup, main):
    art = main.select_one('.art-article')
    for obj in art.find_all('object'):
        audio = soup.new_tag('div', attrs={'class': 'live-audio'})
        a = soup.new_tag('audio', attrs={'controls': '', 'preload': 'none',
                                         'src': 'https://www.damshiria.com/cgi-bin/plist.asx?user=dcc&type=asx&ext=file.asx'})
        audio.append(a)
        obj.replace_with(audio)
        LOG['dead_embeds'].append(('live/live-sound', 'wmp-activex', 'plist.asx'))


def build_stub(key, title):
    body = f'''<div class="art-content-sidebar1"><div class="art-Post"><div class="art-Post-body"><div class="art-Post-inner">
<h2 class="art-PostHeader">{title}</h2>
<div class="art-PostContent"><div class="art-article stub-page" data-stub="{key}">
<p dir="rtl" data-coptic-line>&nbsp;</p>
<p dir="rtl"><a data-readings-link href="https://katamars.avabishoy.com/" target="_blank" rel="noopener">{title}</a></p>
</div></div><div class="cleared"></div></div><div class="cleared"></div></div></div></div>'''
    out = out_path(key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_html(key, f'كنيسة السيدة العذراء الدمشيرية - {title}', body), encoding='utf-8')


def main():
    for d in ['assets/img/content', 'assets/downloads']:
        shutil.rmtree(ROOT / d, ignore_errors=True)
    asset_image('/images/stories/sanawy.png')
    for key, path in PAGES.items():
        build_page(key, path)
    for key, title in STUBS.items():
        build_stub(key, title)
    fav = IMAGES.parent / 'favicon.ico'
    print('pages', len(PAGES), 'stubs', len(STUBS))
    rep = {
        'unknown_links': {k: sorted(v) for k, v in LOG['unknown_links'].items()},
        'dead_embeds': LOG['dead_embeds'],
        'images': len(LOG['images']),
        'webp': LOG['webp'],
    }
    json.dump(rep, open(ROOT / 'tools/build-report.json', 'w'), ensure_ascii=False, indent=1)
    print('unknown links', len(rep['unknown_links']), 'dead embeds', len(rep['dead_embeds']), 'images', rep['images'], 'webp', len(rep['webp']))


if __name__ == '__main__':
    main()
