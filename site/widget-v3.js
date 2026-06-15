/*!
 * IMPT Swarm Widget v3.0.0-rc1 (2026-06-12) — "The Good Ledger" redesign.
 * STAGED FOR REVIEW — served as /widget-v3.js, does NOT replace live /widget.js.
 * Same contract as v2: <script src="https://swarm.impt.io/widget-v3.js" data-key="KEY" async>
 *   inline mount into #impt-swarm / [data-impt-swarm], else floating launcher.
 *   /api/widget/r click routing (partner cookie + attribution) · /api/widget/track beacons.
 * New: two tabs (Classic | Wavelength signal search), value ledger, vertical accents
 *   via data-accent or partner vertical (mtb/surf/walks/pride/gold), serif masthead.
 * Wavelength scoring is local-heuristic for now — swaps to the live signal API when the
 *   search team ships it (see ~/widget-v3-2026-06-12/TEAM-COORDINATION.md).
 * MIT — IMPT Systems Limited.
 */
(function () {
  'use strict';
  if (window.__imptSwarmV3) return; window.__imptSwarmV3 = 1;
  var TRACK = 'https://swarm.impt.io/api/widget/track';
  var ROUTE = 'https://swarm.impt.io/api/widget/r';
  var BRAND = 'https://swarm.impt.io/api/widget/brand';
  var me = document.currentScript || document.querySelector('script[src*="widget-v3.js"]');
  var KEY = (me && me.getAttribute('data-key')) || 'swarm-public';
  var TITLE = (me && me.getAttribute('data-title')) || 'Book your stay';
  var POS = (me && me.getAttribute('data-position')) || 'auto';
  var HOST = location.host;

  var ACCENTS = {
    lime:  { cta:'#C8FF7E', ctaText:'#08423a', dot:'#c79a2a', chip:'#C8FF7E' },
    mtb:   { cta:'#F0743A', ctaText:'#1a1a1a', dot:'#c79a2a', chip:'#F0743A' },
    surf:  { cta:'#46B8B0', ctaText:'#06302c', dot:'#e8c468', chip:'#46B8B0' },
    walks: { cta:'#7FA05A', ctaText:'#0f2812', dot:'#c79a2a', chip:'#7FA05A' },
    lgbtq: { cta:'#C8FF7E', ctaText:'#08423a', dot:'#c79a2a', chip:'linear-gradient(90deg,#e63946,#f4a261,#e9c46a,#2a9d8f,#457b9d,#7b2cbf)' },
    gold:  { cta:'#E8C468', ctaText:'#3a2a06', dot:'#c79a2a', chip:'#E8C468' }
  };
  var AC = ACCENTS[(me && me.getAttribute('data-accent')) || 'lime'] || ACCENTS.lime;

  /* Fonts must live in the light DOM */
  (function fonts() {
    if (document.getElementById('impt-v3-fonts')) return;
    var l = document.createElement('link');
    l.id = 'impt-v3-fonts'; l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif+Display:ital,wght@0,700;0,900;1,600;1,700&display=swap';
    document.head.appendChild(l);
  })();

  function track(evt, dest) {
    try {
      new Image().src = TRACK + '?key=' + encodeURIComponent(KEY) + '&evt=' + encodeURIComponent(evt) +
        '&ref=' + encodeURIComponent(HOST) + (dest ? '&dest=' + encodeURIComponent(dest) : '');
    } catch (e) {}
  }
  function pad(n){ return (n<10?'0':'')+n; }
  function iso(d){ return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate()); }
  var now = new Date(), ciD = new Date(now.getTime()+30*864e5), coD = new Date(now.getTime()+31*864e5);

  /* Wavelength local heuristic — placeholder until the live signal API ships.
     Maps the 4 dials (0-100) to a destination archetype. */
  var WL_MAP = [
    { d:'Queenstown',  t:[80,80,50,50] }, { d:'Chamonix',   t:[85,70,65,40] },
    { d:'Kyoto',       t:[15,40,55,30] }, { d:'Lisbon',     t:[45,25,35,60] },
    { d:'Banff',       t:[60,90,55,45] }, { d:'Marrakech',  t:[55,45,40,75] },
    { d:'Reykjavik',   t:[50,85,70,55] }, { d:'Barcelona',  t:[60,15,45,70] },
    { d:'Interlaken',  t:[75,75,60,50] }, { d:'Bali',       t:[40,70,30,65] },
    { d:'Dingle',      t:[35,80,30,55] }, { d:'Dubai',      t:[50,10,90,50] },
    { d:'Slovenia',    t:[55,85,25,55] }, { d:'Madrid',     t:[50,20,30,65] }
  ];
  function wlPick(v) {
    var best = WL_MAP[0], bd = 1e9;
    for (var i = 0; i < WL_MAP.length; i++) {
      var t = WL_MAP[i].t, d = 0;
      for (var j = 0; j < 4; j++) d += (v[j]-t[j])*(v[j]-t[j]);
      if (d < bd) { bd = d; best = WL_MAP[i]; }
    }
    return best.d;
  }
  var WL_PHRASES = [
    ['perfectly still','gently moving','heart racing'],
    ['in the city','near the edges','somewhere wild'],
    ['smart with money','well balanced','ready to splurge'],
    ['planned to the hour','loosely sketched','ready to go now']
  ];
  function phr(i, v) { return WL_PHRASES[i][v < 34 ? 0 : v < 67 ? 1 : 2]; }

  function go(rt, dest, extra) {
    var cin = rt.getElementById('iv-ci').value, cout = rt.getElementById('iv-co').value;
    var g = rt.getElementById('iv-g').value;
    var url = ROUTE + '?key=' + encodeURIComponent(KEY) +
      (dest ? '&dest=' + encodeURIComponent(dest) : '') +
      '&checkIn=' + encodeURIComponent(cin) + '&checkOut=' + encodeURIComponent(cout) +
      '&adults=' + encodeURIComponent(g) + '&rooms=1' + (extra || '');
    window.open(url, '_blank', 'noopener');
  }

  var BED = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18V8M3 14h18v4M21 18v-4a3 3 0 0 0-3-3h-7v3"/><circle cx="7" cy="12" r="1.5"/></svg>';
  var LEAF = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 4c0 9-6 16-14 16 0-9 6-16 14-16zM4 20C9 15 13 11 18 6"/></svg>';

  var CSS = '' +
  ':host{all:initial}' +
  '*{box-sizing:border-box;font-family:Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;margin:0;padding:0}' +
  '.serif{font-family:"Noto Serif Display",Georgia,serif}' +
  '.caps{font-size:10px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:rgba(8,66,58,.65)}' +
  '.gnum{font-family:"Noto Serif Display",Georgia,serif;font-weight:900;color:#c79a2a}' +
  '.card{width:380px;max-width:calc(100vw - 24px);background:#f5f3ea;border:1px solid rgba(8,66,58,.18);border-radius:16px;overflow:hidden;' +
    'box-shadow:0 30px 60px -30px rgba(8,66,58,.35),0 8px 20px -12px rgba(8,66,58,.15)}' +
  '.hd{position:relative;padding:18px 24px 22px;background:linear-gradient(135deg,#0b4a40 0%,#0f5d50 100%);color:#fff}' +
  '.hd .row{display:flex;align-items:center;justify-content:space-between}' +
  '.brand{display:flex;align-items:center;gap:8px;min-height:24px}' +
  '.brand img{height:22px;max-width:110px;object-fit:contain;border-radius:4px;background:#fff;padding:2px}' +
  '.brand span{font-size:11px;letter-spacing:.16em;text-transform:uppercase;opacity:.78}' +
  '.stamp{border-radius:999px;padding:3px 8px;font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;background:' + AC.chip + ';color:' + AC.ctaText + '}' +
  '.hd h2{font-family:"Noto Serif Display",Georgia,serif;font-weight:900;font-size:28px;line-height:1.05;letter-spacing:-.02em;margin-top:14px}' +
  '.hd p{font-size:12.5px;opacity:.72;margin-top:6px;letter-spacing:.01em}' +
  '.x{position:absolute;top:14px;right:14px;width:28px;height:28px;border:0;border-radius:50%;cursor:pointer;background:rgba(255,255,255,.14);color:#fff;font-size:16px;line-height:1;display:none;align-items:center;justify-content:center}' +
  '.x:hover{background:rgba(255,255,255,.26)}.fl .x{display:flex}' +
  '.tabs{margin:-14px 24px 14px;display:grid;grid-template-columns:1fr 1fr;background:#fff;border:1px solid rgba(8,66,58,.10);border-radius:999px;padding:4px;box-shadow:0 6px 16px -10px rgba(8,66,58,.25);position:relative}' +
  '.tab{border:0;border-radius:999px;padding:8px 0;cursor:pointer;font-size:10.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;background:transparent;color:rgba(8,66,58,.65);transition:background .15s,color .15s}' +
  '.tab.on{background:#08423a;color:#fff}' +
  '.bd{padding:0 24px 8px}' +
  '.fld{margin-bottom:12px}.fld>div:first-child{margin-bottom:6px}' +
  '.in{display:flex;align-items:center;height:44px;background:#fff;border:1px solid rgba(8,66,58,.18);border-radius:8px;padding:0 12px;transition:border-color .15s,box-shadow .15s}' +
  '.in:focus-within{border-color:#0b4a40;box-shadow:0 0 0 3px rgba(11,74,64,.12)}' +
  '.in input,.in select{flex:1;border:0;outline:0;background:transparent;font-size:14px;color:#08423a;height:100%}' +
  '.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}' +
  '.cta{display:block;width:100%;border:0;border-radius:8px;padding:13px 0;cursor:pointer;background:' + AC.cta + ';color:' + AC.ctaText + ';' +
    'font-size:14px;font-weight:700;letter-spacing:.02em;box-shadow:0 10px 24px -12px rgba(8,66,58,.45);transition:filter .15s,transform .12s;margin-top:4px}' +
  '.cta:hover{filter:brightness(.96)}.cta:active{transform:scale(.99)}' +
  '.sent{font-family:"Noto Serif Display",Georgia,serif;font-size:15.5px;line-height:1.5;color:#08423a;margin-bottom:14px;letter-spacing:-.005em}' +
  '.gp{color:#c79a2a;border-bottom:1px dashed rgba(199,154,42,.5);font-style:italic;font-weight:600}' +
  '.dial{margin-bottom:13px}' +
  '.dial .lbl{display:flex;justify-content:space-between;margin-bottom:6px}.dial .lbl span{font-size:9px}' +
  '.dial input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:6px;border-radius:999px;background:rgba(8,66,58,.10);outline:none;display:block}' +
  '.dial input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:14px;height:14px;border-radius:50%;background:' + AC.dot + ';cursor:pointer;box-shadow:0 2px 6px rgba(199,154,42,.4),0 0 0 3px #f5f3ea;border:0}' +
  '.dial input[type=range]::-moz-range-thumb{width:14px;height:14px;border-radius:50%;background:' + AC.dot + ';cursor:pointer;box-shadow:0 2px 6px rgba(199,154,42,.4),0 0 0 3px #f5f3ea;border:0}' +
  '.sig{background:#fff;border:1px solid rgba(8,66,58,.10);border-radius:8px;padding:12px;margin-bottom:14px}' +
  '.sig .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}' +
  '.sig .bars{display:flex;align-items:flex-end;gap:3px;height:32px}' +
  '.sig .bars i{flex:1;border-radius:1px;display:block}' +
  '.ledg{margin:14px 24px 12px;background:rgba(8,66,58,.03);border:1px solid rgba(8,66,58,.10);border-radius:8px}' +
  '.ledg .r{display:flex;align-items:baseline;justify-content:space-between;padding:8px 12px;border-top:1px solid rgba(8,66,58,.10)}' +
  '.ledg .r:first-child{border-top:0}' +
  '.ledg .l{display:flex;align-items:baseline;gap:10px}.ledg .l b{font-size:11px}' +
  '.ledg .l span{font-size:11.5px;color:rgba(8,66,58,.65);letter-spacing:.04em}' +
  '.ledg .v{font-family:"Noto Serif Display",Georgia,serif;font-weight:900;font-size:14px;color:#08423a}' +
  '.ft{display:flex;align-items:center;justify-content:space-between;padding:10px 24px;border-top:1px solid rgba(8,66,58,.10);color:rgba(8,66,58,.45)}' +
  '.ft .p{display:flex;align-items:center;gap:6px;font-size:10px;letter-spacing:.14em;text-transform:uppercase}' +
  '.ft .g{font-family:"Noto Serif Display",Georgia,serif;font-style:italic;font-size:11px}' +
  '.fl{position:fixed;right:20px;bottom:20px;z-index:2147483000}' +
  '.fl.left{right:auto;left:20px}.fl.left .card{right:auto;left:0}' +
  '.fab{display:inline-flex;align-items:center;gap:11px;cursor:pointer;border:0;border-radius:999px;padding:9px 16px 9px 9px;background:#08423a;color:#fff;' +
    'box-shadow:0 18px 40px -16px rgba(8,66,58,.6),0 0 0 4px rgba(8,66,58,.06);transition:transform .18s,box-shadow .18s}' +
  '.fab:hover{transform:translateY(-2px)}' +
  '.fab .ic{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:' + AC.cta + ';color:' + AC.ctaText + '}' +
  '.fab .tx{text-align:left;line-height:1.25}' +
  '.fab .tx b{display:block;font-size:12.5px;font-weight:600;letter-spacing:.01em}' +
  '.fab .tx small{display:block;font-size:10px;opacity:.7;letter-spacing:.04em}' +
  '.fl .card{position:absolute;right:0;bottom:0;opacity:0;transform:translateY(12px) scale(.98);pointer-events:none;transition:opacity .2s,transform .2s}' +
  '.fl.open .card{opacity:1;transform:none;pointer-events:auto}.fl.open .fab{display:none}' +
  '@media(max-width:480px){.fl{right:12px;bottom:12px}.fl.left{right:auto;left:12px}}';

  function cardHTML(floating) {
    var bars = '';
    for (var i = 0; i < 14; i++) bars += '<i></i>';
    return '<style>' + CSS + '</style>' +
      (floating ? '<button class="fab" id="iv-fab"><span class="ic">' + BED + '</span><span class="tx"><b>Book a hotel</b><small>5% back &middot; 1t CO&#8322; offset</small></span></button>' : '') +
      '<div class="card" role="dialog" aria-label="Book a hotel">' +
        '<div class="hd"><div class="row"><div class="brand" id="iv-brand"></div><span class="stamp">IMPT</span></div>' +
          '<h2>' + TITLE + '</h2><p>Every night gives back &mdash; to you, to them, to the air.</p>' +
          '<button class="x" id="iv-x" aria-label="Close">&times;</button></div>' +
        '<div class="tabs"><button class="tab on" id="iv-tc">Classic</button><button class="tab" id="iv-tw">Wavelength</button></div>' +
        '<div class="bd" id="iv-classic">' +
          '<div class="fld"><div class="caps">Destination</div><div class="in"><input id="iv-dest" placeholder="City, region or hotel" autocomplete="off"></div></div>' +
          '<div class="two fld"><div><div class="caps">Check-in</div><div class="in"><input id="iv-ci" type="date" value="' + iso(ciD) + '"></div></div>' +
            '<div><div class="caps">Check-out</div><div class="in"><input id="iv-co" type="date" value="' + iso(coD) + '"></div></div></div>' +
          '<div class="fld"><div class="caps">Guests</div><div class="in"><select id="iv-g"><option value="2">2 adults &middot; 1 room</option><option value="1">1 adult &middot; 1 room</option><option value="3">3 guests &middot; 1 room</option><option value="4">4 guests &middot; 1 room</option><option value="5">5 guests &middot; 1 room</option><option value="6">6 guests &middot; 1 room</option></select></div></div>' +
          '<button class="cta" id="iv-go">Search hotels &rarr;</button>' +
        '</div>' +
        '<div class="bd" id="iv-wave" style="display:none">' +
          '<p class="sent">Wake me up <span class="gp" id="iv-p1"></span>, <span class="gp" id="iv-p0"></span>, <span class="gp" id="iv-p2"></span> &mdash; <span class="gp" id="iv-p3"></span>.</p>' +
          '<div class="dial"><div class="lbl"><span class="caps">Stillness</span><span class="caps">Adrenaline</span></div><input type="range" id="iv-d0" min="0" max="100" value="72"></div>' +
          '<div class="dial"><div class="lbl"><span class="caps">Urban</span><span class="caps">Wild</span></div><input type="range" id="iv-d1" min="0" max="100" value="84"></div>' +
          '<div class="dial"><div class="lbl"><span class="caps">Smart</span><span class="caps">Splurge</span></div><input type="range" id="iv-d2" min="0" max="100" value="28"></div>' +
          '<div class="dial"><div class="lbl"><span class="caps">Planned</span><span class="caps">Spontaneous</span></div><input type="range" id="iv-d3" min="0" max="100" value="90"></div>' +
          '<div class="sig"><div class="top"><span class="caps" style="font-size:9px">Your demand signature</span><b class="gnum" style="font-size:11px">&#8470; ' + String(1000 + Math.floor(Math.random()*9000)) + '</b></div>' +
            '<div class="bars" id="iv-bars">' + bars + '</div></div>' +
          '<button class="cta" id="iv-tune">Tune my stay &rarr;</button>' +
        '</div>' +
        '<div class="ledg">' +
          '<div class="r"><div class="l"><b class="gnum">&#8470; 01</b><span>to the partner</span></div><span class="v">5%</span></div>' +
          '<div class="r"><div class="l"><b class="gnum">&#8470; 02</b><span>guest credit</span></div><span class="v">&euro;5</span></div>' +
          '<div class="r"><div class="l"><b class="gnum">&#8470; 03</b><span>CO&#8322; retired / night</span></div><span class="v">1 t</span></div>' +
        '</div>' +
        '<div class="ft"><span class="p">' + LEAF + ' Powered by IMPT</span><span class="g">The Good Ledger</span></div>' +
      '</div>';
  }

  function loadBrand(rt) {
    try {
      fetch(BRAND + '?key=' + encodeURIComponent(KEY)).then(function(r){ return r.json(); }).then(function(b){
        if (!b || (!b.name && !b.logo)) return;
        var el = rt.getElementById('iv-brand'); if (!el) return;
        var h = '';
        if (b.logo) h += '<img src="' + b.logo + '" alt="">';
        if (b.name) h += '<span>' + String(b.name).replace(/[<>]/g,'').slice(0,40) + '</span>';
        el.innerHTML = h;
      }).catch(function(){});
    } catch (e) {}
  }

  function wire(rt, floating, wrap) {
    if (floating) {
      rt.getElementById('iv-fab').addEventListener('click', function(){ wrap.classList.add('open'); track('view'); });
      rt.getElementById('iv-x').addEventListener('click', function(){ wrap.classList.remove('open'); });
    }
    var tc = rt.getElementById('iv-tc'), tw = rt.getElementById('iv-tw');
    var pc = rt.getElementById('iv-classic'), pw = rt.getElementById('iv-wave');
    tc.addEventListener('click', function(){ tc.classList.add('on'); tw.classList.remove('on'); pc.style.display=''; pw.style.display='none'; });
    tw.addEventListener('click', function(){ tw.classList.add('on'); tc.classList.remove('on'); pw.style.display=''; pc.style.display='none'; track('wl_open'); });
    rt.getElementById('iv-go').addEventListener('click', function(){
      var d = (rt.getElementById('iv-dest').value || '').trim();
      go(rt, d);
    });
    rt.getElementById('iv-dest').addEventListener('keydown', function(e){
      if (e.key === 'Enter') go(rt, (rt.getElementById('iv-dest').value || '').trim());
    });
    function vals() {
      return [0,1,2,3].map(function(i){ return parseInt(rt.getElementById('iv-d'+i).value, 10); });
    }
    function paint() {
      var v = vals();
      for (var i = 0; i < 4; i++) rt.getElementById('iv-p'+i).textContent = phr(i, v[i]);
      var bars = rt.getElementById('iv-bars').children;
      for (var j = 0; j < bars.length; j++) {
        var base = v[j % 4], h = Math.max(12, Math.min(96, base + ((j * 37) % 41) - 20));
        bars[j].style.height = h + '%';
        bars[j].style.background = (j % 3 === 0) ? '' + AC.dot : '#08423a';
        bars[j].style.opacity = (j % 3 === 0) ? '1' : '.55';
      }
    }
    [0,1,2,3].forEach(function(i){ rt.getElementById('iv-d'+i).addEventListener('input', paint); });
    paint();
    rt.getElementById('iv-tune').addEventListener('click', function(){
      var v = vals(), dest = wlPick(v);
      track('wl_tune', dest);
      go(rt, dest, '&wl=1&sig=' + v.join('-'));
    });
  }

  function mount() {
    var inlineHost = document.getElementById('impt-swarm') || document.querySelector('[data-impt-swarm]');
    if (inlineHost) {
      var rt = inlineHost.attachShadow ? inlineHost.attachShadow({mode:'open'}) : inlineHost;
      rt.innerHTML = cardHTML(false);
      wire(rt, false, null);
      loadBrand(rt);
      track('view');
    } else {
      var host = document.createElement('div');
      document.body.appendChild(host);
      var rt2 = host.attachShadow ? host.attachShadow({mode:'open'}) : host;
      var wrap = document.createElement('div'); wrap.className = 'fl';
      wrap.innerHTML = cardHTML(true);
      rt2.appendChild(wrap);
      wire(rt2, true, wrap);
      loadBrand(rt2);
      function flip(left){ wrap.classList.toggle('left', left); try { host.setAttribute('data-impt-side', left ? 'left' : 'right'); } catch(_){} }
      function place(){
        try {
          if (POS === 'left') { flip(true); return; }
          if (POS === 'right') { flip(false); return; }
          var vw = window.innerWidth, vh = window.innerHeight, all = document.body.getElementsByTagName('*'), taken = false;
          for (var i = 0; i < all.length; i++) {
            var e = all[i];
            if (e === host || (host.contains && host.contains(e))) continue;
            var s; try { s = getComputedStyle(e); } catch(_) { continue; }
            if (s.position !== 'fixed' && s.position !== 'sticky') continue;
            if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity || '1') === 0) continue;
            var r = e.getBoundingClientRect();
            if (r.width < 8 || r.height < 8 || r.width > vw * 0.85) continue;
            if (r.left > vw * 0.5 && r.right > vw - 170 && r.bottom > vh * 0.5) { taken = true; break; }
          }
          flip(taken);
        } catch (e) {}
      }
      place(); [600,1500,3500,7000].forEach(function(t){ setTimeout(place, t); });
      window.addEventListener('resize', place);
      if (window.MutationObserver) { try { new MutationObserver(place).observe(document.body, {childList:true, subtree:false}); } catch(e) {} }
      track('load');
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
