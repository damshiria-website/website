# كنيسة السيدة العذراء الدمشيرية — static site

A static rebuild of https://stmarydamshiria.net/ (previously Joomla). It is plain HTML, CSS and JS with no build step, so GitHub Pages serves it as it is.

- `index.html` and one `<path>/index.html` per page. Old URLs keep working.
- `assets/css/variables.css` holds the palette and fonts. `template.css` is the original theme, with its colors moved to variables. `site.css` holds the widgets and the phone layout.
- `assets/js/config.js` holds the settings you may need to change. `site.js` runs the menu, slider, gallery, readings date, audio and form.
- `docs/inventory.md` lists what was on the old site and how each part was handled. `docs/compare/` has screenshots of the old and new site side by side.
- `tools/build.py` is the one-time converter from the crawl. The site does not need it.

## Preview locally

    python3 -m http.server 8000
    # open http://localhost:8000/

## Publish on GitHub Pages

1. Create a new repository on GitHub (public, or private on a paid plan), e.g. `stmarydamshiria-site`.
2. Push this folder:

       git remote add origin https://github.com/<user>/stmarydamshiria-site.git
       git push -u origin main

3. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save.**
4. The `CNAME` file (already here) contains `stmarydamshiria.net`. Under **Settings → Pages → Custom domain** enter `stmarydamshiria.net`, wait for the DNS check, then tick **Enforce HTTPS**.
5. At the domain's DNS provider, delete the old A/AAAA records for the root and `www`, then add:

   | Type | Name | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | CNAME | www | `<user>.github.io` |

   (Optional IPv6: AAAA records `2606:50c0:8000::153`, `8001::153`, `8002::153`, `8003::153`.)

`.nojekyll` is included so Pages serves the files as they are.

## Before switching the domain: decisions needed

1. **Audio and large files (~1.4 GB).** These are too big for the repository. The originals are saved outside the repo in `../damshiria-site-source/crawl/downloads/` and `.../spirituals/`. Upload them, for example as assets of a GitHub Release (2 GB per file limit) or to archive.org. Then set `MEDIA_BASE` in `assets/js/config.js` to the folder URL, for example `https://github.com/<user>/<repo>/releases/download/media-v1/`. Files are looked up by their original file name. Until this is done the links point to the old server and stop working when it goes away.
2. **Prayer requests.** Create a free form at formspree.io, put its id in `FORMSPREE_ID`, and set `PRAYER_EMAIL` as a fallback.
3. **Daily readings.** `READINGS_URL` links out to an external katameros site. Choose the one the church prefers.
4. **The old server is hacked** (hidden spam links on every page). Change its passwords and do not copy files back from it without checking them.
