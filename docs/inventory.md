# Inventory of stmarydamshiria.com (crawled 2026-10-11)

## What the live site is

- **Joomla 1.5** with an Artisteer 2.3 template ("damshiria"). The request called it WordPress, but it is not WordPress.
- **Arabic only, RTL** (`lang="ar-dz"`). There is no English version. Fonts: Tahoma (body, 12px) and Arial (headings 22px bold, menu 17px bold). No web fonts.
- **The site is compromised.** Every page ends with six hidden links placed off-screen (`position:absolute; left:-5000px`) to `xxxhub.cc` (adult) and `farmakosha.com` (pharmacy spam). This is SEO spam injection. The rebuild strips these links. The old server should be considered hacked: change its passwords and do not reuse anything from it without checking it.
- The crawler needed a browser User-Agent and Accept headers. Plain curl gets a 406 from Mod_Security.

## Pages (192 crawled + 3 stand-ins = 195 HTML files)

| Section (menu) | Pages |
|---|---|
| الرئيسية (home) | 1 |
| الكنيسة الاثرية: history, saints (7 categories, 30 saint pages), icons gallery (2 pages + 2 duplicate category views) | 43 |
| عن الكنيسة: mass schedule, 11 church-service pages, committee, fathers | 15 |
| عقيدتنا: Christian faith (4 articles), Orthodox faith | 6 |
| لحياتك: parents (5 articles), youth, servants | 10 |
| غذاء الروح: Bible listen, publications (6), quotes (24), books, articles (2 series, 13) | 50 |
| تحميلات (downloads): sections and categories | 16 |
| بث مباشر: live video, live sound, recordings (4 series, 39 pages) | 46 |
| طلبات صلاة (prayer requests) | 1 |
| Plus one standalone article (message from Fr. Yohanna) | 1 |
| **Menu items that already return 404 on the live site:** السنكسار `/spirituals/seneksar`, القطمارس `/spirituals/katamaras`, قراءة الكتاب المقدس `/spirituals/bible/bible-read` | 3 stand-ins |

URLs keep the old paths as folders (`/about-us/schedule` becomes `/about-us/schedule/index.html`), so old links and search results still land on the right page. The icons gallery page 2 (`?start=20`) becomes `/ancient-church/icons/page-2/`. Two Arabic article slugs under `/life/fathers/` had spaces in them; the spaces became `-`.

## Interactive sections and how each is handled

| Section | Live implementation | Static rebuild |
|---|---|---|
| Drop-down main menu (3 levels) | CSS hover (Artisteer) | Same CSS hover on desktop. On phones it becomes a "القائمة ☰" toggle and opens submenus on tap (`site.js`). |
| Image slider on 4 section pages (about, ancient church, life, spirituals) | DJ Image Slider (MooTools): auto-advance every 3.6 s, arrows, play/pause | Vanilla JS slider with the same delay, arrows and pause. The live "القطمارس" slide points at a missing `/blank.png`, so it was dropped. |
| Icons gallery, 37 icons | Phoca Gallery, modal iframe | Grid with thumbnails and a lightbox (keyboard arrows, Esc), 2 pages like the original. |
| Daily readings sidebar (katameros + synaxarium) on every page | `com_reading`: a server-side database keyed by the Coptic date | **This cannot be static.** The box keeps the same look and computes today's Coptic date in JS (Cairo time). Its links go to `READINGS_URL` (katamars.avabishoy.com, set in `config.js`). Note: the live box shows the wrong date ("1742 توت 30" on 11 Oct 2026; the correct date is 1743 بابه 1). |
| Prayer request form | PrayerCenter component (stores requests, public list) | Same fields and labels. It posts to Formspree once `FORMSPREE_ID` is set. Until then it opens the visitor's mail app addressed to `PRAYER_EMAIL` (TODO). The public "view all requests" list is dropped. It held visitors' personal requests and needs a backend. |
| Downloads (84 files: 17 books, 67 sermon/conference MP3s) | Phoca Download + "Play" popup | Static lists. "Play" opens an inline HTML5 audio player. 10 valid small books ship in `assets/downloads/`. Audio (~1.4 GB) and the large or broken books are fetched from `MEDIA_BASE` (see README). |
| YouTube videos (13, old Flash `/v/` embeds) | `<object>` Flash | Converted to `youtube-nocookie.com` iframes, responsive. |
| Ustream recordings (61 videos) | Flash ustream viewer | **Dead.** Ustream shut those down years ago. Each is replaced by a notice ("هذا التسجيل كان على Ustream ولم يعد متاحًا."), with the video id kept in `data-ustream-vid`. |
| Live video | iframe of `damshiria.com/live.htm` | Same iframe over https. The stream host is the church's own server. |
| Live sound | Windows Media ActiveX + .asx/.ram/.pls links | ActiveX replaced by an `<audio>` tag on the same stream URL. The player-app links are kept. Whether the stream still runs is unverified. |
| Bible listening | alenjil.com widget script | Same widget, loaded over https with its original settings. |
| Twitter share / Facebook share and Like | Old widgets.js / FB.Share / like iframes | Twitter becomes a plain X share-intent link with the same text "شارك على تويتر". The Facebook widgets are dead and were removed. |
| "Visitors online" counter | Joomla session count | Dropped. A static site has no session count. |
| Email addresses | Joomla JS email cloaking | Decoded to plain `mailto:` links. |

## Colors (from template.css, checked against the live computed styles)

Page background `#E6CE9B` + `back.jpg`; text `#40463E`; headings `#2F332E`; links `#887A44` (hover `#B3911A`, visited `#665C33`); menu text white, hover `#232622`, active `#070807`; submenu `#474024`; sidebar header text `#F0EDE0`; sidebar text `#43280A`; readings red `#8B0000`; footer text white bold. The gradients are bitmaps (header, nav, tabs, blocks, footer) and are kept as the original files. All tokens are in `assets/css/variables.css`.
