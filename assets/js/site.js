/* St. Mary Damshiria static site: menu, slider, gallery lightbox, daily-readings
   date, download links, audio player, prayer form. Vanilla JS, no dependencies. */
(function () {
  'use strict';
  var CFG = window.SITE_CONFIG || {};

  /* ---------- menu: mobile toggle + tap-to-open submenus ---------- */
  var toggle = document.querySelector('.menu-toggle');
  var nav = document.querySelector('.art-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.art-menu li.parent > a').forEach(function (a) {
    a.setAttribute('aria-haspopup', 'true');
    a.addEventListener('click', function (e) {
      var li = a.parentNode;
      var small = window.matchMedia('(max-width: 900px)').matches;
      var isSeparator = a.getAttribute('href') === '#';
      // on touch / small screens the first tap opens the submenu
      if (isSeparator || (small && !li.classList.contains('sub-open'))) {
        e.preventDefault();
        li.classList.toggle('sub-open');
      }
    });
  });

  /* ---------- share on X/Twitter (the old Twitter button) ---------- */
  document.querySelectorAll('a.share-x').forEach(function (a) {
    a.href = 'https://twitter.com/intent/tweet?url=' + encodeURIComponent(location.href) +
      '&text=' + encodeURIComponent(document.title);
  });

  /* ---------- slider (was DJ Image Slider: auto 3.6 s, arrows, pause) ---------- */
  document.querySelectorAll('.slider').forEach(function (box) {
    var track = box.querySelector('.slider-track');
    var slides = box.querySelectorAll('.slide');
    if (!track || slides.length < 2) return;
    var i = 0, timer = null, delay = parseInt(box.getAttribute('data-delay'), 10) || 3600;
    function go(n) {
      i = (n + slides.length) % slides.length;
      track.style.transform = 'translateX(' + (i * 100) + '%)'; // RTL: positive moves left-to-right
    }
    function play() { stop(); timer = setInterval(function () { go(i + 1); }, delay); box.classList.remove('paused'); }
    function stop() { if (timer) clearInterval(timer); timer = null; }
    box.querySelector('.slider-next').addEventListener('click', function () { go(i + 1); if (timer) play(); });
    box.querySelector('.slider-prev').addEventListener('click', function () { go(i - 1); if (timer) play(); });
    box.querySelector('.slider-pause').addEventListener('click', function () {
      if (timer) { stop(); box.classList.add('paused'); } else { play(); }
    });
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) play();
  });

  /* ---------- gallery lightbox (was Phoca Gallery modal) ---------- */
  var links = Array.prototype.slice.call(document.querySelectorAll('a.lightbox'));
  if (links.length) {
    var lb = document.createElement('div');
    lb.className = 'lb';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.innerHTML = '<button type="button" class="lb-close" aria-label="إغلاق">×</button>' +
      '<button type="button" class="lb-prev" aria-label="السابق">‹</button>' +
      '<figure><img alt="" /><figcaption></figcaption></figure>' +
      '<button type="button" class="lb-next" aria-label="التالي">›</button>';
    document.body.appendChild(lb);
    var img = lb.querySelector('img'), cap = lb.querySelector('figcaption'), cur = 0;
    function show(n) {
      cur = (n + links.length) % links.length;
      img.src = links[cur].getAttribute('href');
      img.alt = cap.textContent = links[cur].getAttribute('title') || '';
      lb.classList.add('open');
    }
    function close() { lb.classList.remove('open'); img.removeAttribute('src'); }
    links.forEach(function (a, n) {
      a.addEventListener('click', function (e) { e.preventDefault(); show(n); });
    });
    lb.querySelector('.lb-close').addEventListener('click', close);
    lb.querySelector('.lb-next').addEventListener('click', function () { show(cur + 1); });
    lb.querySelector('.lb-prev').addEventListener('click', function () { show(cur - 1); });
    lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
    document.addEventListener('keydown', function (e) {
      if (!lb.classList.contains('open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') show(cur + 1);
      if (e.key === 'ArrowRight') show(cur - 1);
    });
  }

  /* ---------- Coptic date for the daily readings box ---------- */
  var MONTHS = ['توت', 'بابه', 'هاتور', 'كيهك', 'طوبة', 'أمشير', 'برمهات', 'برمودة', 'بشنس', 'بؤونة', 'أبيب', 'مسرى', 'نسيء'];
  var EPOCH = 1825030; // JDN of 1 Tout, year 1 A.M.
  function gregToJdn(y, m, d) {
    var a = Math.floor((14 - m) / 12), yy = y + 4800 - a, mm = m + 12 * a - 3;
    return d + Math.floor((153 * mm + 2) / 5) + 365 * yy + Math.floor(yy / 4) - Math.floor(yy / 100) + Math.floor(yy / 400) - 32045;
  }
  function copticToJdn(y, m, d) { return EPOCH - 1 + 365 * (y - 1) + Math.floor(y / 4) + 30 * (m - 1) + d; }
  function copticFromGreg(y, m, d) {
    var jdn = gregToJdn(y, m, d);
    var cy = Math.floor((4 * (jdn - EPOCH) + 1463) / 1461);
    var cm = Math.floor((jdn - copticToJdn(cy, 1, 1)) / 30) + 1;
    var cd = jdn + 1 - copticToJdn(cy, cm, 1);
    return { y: cy, m: cm, d: cd };
  }
  window.copticFromGreg = copticFromGreg; // exposed for the self-test
  function cairoToday() {
    try {
      var p = new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit' })
        .format(new Date()).split('-');
      return [parseInt(p[0], 10), parseInt(p[1], 10), parseInt(p[2], 10)];
    } catch (e) {
      var n = new Date();
      return [n.getFullYear(), n.getMonth() + 1, n.getDate()];
    }
  }
  var t = cairoToday(), c = copticFromGreg(t[0], t[1], t[2]);
  var label = c.y + ' ' + MONTHS[c.m - 1] + ' ' + c.d; // same order as the old module: "1742 توت 30"
  document.querySelectorAll('[data-coptic-date]').forEach(function (el) { el.textContent = label; });
  document.querySelectorAll('[data-coptic-line]').forEach(function (el) { el.textContent = 'اليوم: ' + label; });
  if (CFG.READINGS_URL) {
    document.querySelectorAll('[data-readings-link],[data-synax-link]').forEach(function (a) { a.href = CFG.READINGS_URL; });
  }

  /* ---------- downloads: point large files at MEDIA_BASE ---------- */
  function mediaUrl(name, orig) {
    if (CFG.MEDIA_BASE) return CFG.MEDIA_BASE.replace(/\/?$/, '/') + encodeURIComponent(name);
    return 'https://stmarydamshiria.com' + orig;
  }
  document.querySelectorAll('a[data-media]').forEach(function (a) {
    a.href = mediaUrl(a.getAttribute('data-media'), a.getAttribute('data-orig'));
  });

  /* ---------- "Play" buttons in the downloads list -> inline audio ---------- */
  document.querySelectorAll('.play-btn').forEach(function (b) {
    b.addEventListener('click', function () {
      var row = b.closest('tr') || b.parentNode;
      var dl = row.querySelector('a[data-media], a[download]');
      var src = b.getAttribute('data-src') || (dl ? dl.href : '');
      var existing = row.parentNode.querySelector('audio[data-for="' + src + '"]');
      if (existing) { existing.paused ? existing.play() : existing.pause(); return; }
      document.querySelectorAll('audio.inline-player').forEach(function (a) { a.pause(); });
      var audio = document.createElement('audio');
      audio.className = 'inline-player';
      audio.controls = true;
      audio.src = src;
      audio.setAttribute('data-for', src);
      var holder = document.createElement(row.tagName === 'TR' ? 'tr' : 'div');
      if (row.tagName === 'TR') {
        var td = document.createElement('td');
        td.colSpan = row.children.length;
        td.appendChild(audio);
        holder.appendChild(td);
      } else holder.appendChild(audio);
      row.parentNode.insertBefore(holder, row.nextSibling);
      audio.play().catch(function () {});
    });
  });

  /* ---------- prayer request form ---------- */
  document.querySelectorAll('form.prayer-form').forEach(function (f) {
    var status = f.querySelector('.form-status');
    if (CFG.FORMSPREE_ID) f.action = 'https://formspree.io/f/' + CFG.FORMSPREE_ID;
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      if (f._gotcha && f._gotcha.value) return;
      var name = f.newrequester.value.trim(), req = f.newrequest.value.trim();
      if (!name) { status.textContent = 'لابد من كتابة الاسم'; f.newrequester.focus(); return; }
      if (!req) { status.textContent = 'من  فضلك ادخل طلبتك'; f.newrequest.focus(); return; }
      if (!CFG.FORMSPREE_ID) {
        var to = CFG.PRAYER_EMAIL || '';
        var body = 'الاسم: ' + name + '\nالبريد: ' + f.newemail.value + '\n' +
          (f.private.checked ? 'لا تعرضها على الموقع\n' : '') + '\n' + req;
        window.location.href = 'mailto:' + to + '?subject=' + encodeURIComponent('طلبة صلاة') + '&body=' + encodeURIComponent(body);
        return;
      }
      status.textContent = '...';
      fetch(f.action, { method: 'POST', body: new FormData(f), headers: { Accept: 'application/json' } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          f.reset();
          status.textContent = 'تم ارسال طلبتك. سوف يتم وضعها على مذبح الكنيسة.';
        })
        .catch(function () { status.textContent = 'تعذر الارسال، حاول مرة اخرى.'; });
    });
  });
})();
