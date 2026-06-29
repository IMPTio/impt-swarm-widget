/*!
 * IMPT Swarm Widget v2.2.4 (2026-06-25) — professional, shadow-DOM isolated.
 * Dual mode: renders a polished inline card into #impt-swarm / [data-impt-swarm] if present,
 * otherwise a floating bottom-right launcher. Preserves the v1 contract:
 *   <script src="https://swarm.impt.io/widget.js" data-key="YOUR_KEY" async></script>
 *   utm_source=swarm-<key> redirect (partner 5% intact) · /api/widget/track view+click.
 * MIT — IMPT Systems Limited.
 */
(function () {
  'use strict';
  if (window.__imptSwarmV2) return; window.__imptSwarmV2 = 1;
  var REDIRECT = 'https://app.impt.io/find-hotel-input';
  var TRACK = 'https://swarm.impt.io/api/widget/track';
  var me = document.currentScript ||
    document.querySelector('script[src*="widget.js"]');
  var KEY = (me && me.getAttribute('data-key')) || 'swarm-public';
  var TITLE = (me && me.getAttribute('data-title')) || 'Book your stay';
  var HOST = location.host;
  var BRAND = 'https://swarm.impt.io/api/widget/brand';
  var CONFIG_URL = 'https://swarm.impt.io/api/widget/config';
  var POS = (me && me.getAttribute('data-position')) || 'auto';

  function _applyBrand(rt, b) {
    if (!b) return;
    // Brand name + logo
    if (b.name || b.logo) {
      var el = rt.querySelector('#impt-brand'); if (el) {
        var h = '';
        if (b.logo) h += '<img src="' + b.logo + '" alt="" style="height:22px;max-width:100px;object-fit:contain;border-radius:4px;background:#fff;padding:2px 5px;margin-right:6px">';
        if (b.name) h += '<span>' + String(b.name).replace(/[<>]/g,'').slice(0,40) + '</span>';
        el.innerHTML = h;
      }
    }
    // Primary color — widget AND chat globals
    var c = (b.color || '').replace(/[^#0-9a-fA-F]/g,'');
    window.__imptPrimaryColor = c || '';
    if (c) {
      // CSS injection covers elements not yet in DOM (floating FAB on load)
      var bsEl = rt.querySelector('#impt-brand-style');
      if (!bsEl) { bsEl = document.createElement('style'); bsEl.id = 'impt-brand-style'; (rt.head || rt).appendChild(bsEl); }
      bsEl.textContent = '.hd{background:linear-gradient(135deg,' + c + 'dd,' + c + ')!important}.btn{background:' + c + '!important}.fab{background:' + c + '!important}';
      // Direct inline !important — beats any CSS !important (including loadSurf vertical themes)
      var _hd = rt.querySelector('.hd'); if (_hd) _hd.style.setProperty('background', 'linear-gradient(135deg,' + c + 'dd,' + c + ')', 'important');
      var _bt = rt.querySelector('.btn'); if (_bt) _bt.style.setProperty('background', c, 'important');
      var _fb = rt.querySelector('.fab'); if (_fb) _fb.style.setProperty('background', c, 'important');
    }
    // FAB button text + emoji
    var fabEl = rt.querySelector('#impt-fab');
    if (fabEl) {
      var emoji = (b.buttonEmoji || '').replace(/[<>]/g,'');
      var txt = (b.buttonText || '').replace(/[<>]/g,'').slice(0,30);
      if (emoji || txt) {
        var subHtml = b.buttonSubtitle ? '<br><small style="font-weight:500;opacity:.82;font-size:11px">' + String(b.buttonSubtitle).replace(/[<>]/g,'').slice(0,50) + '</small>' : '';
        fabEl.innerHTML = '<span style="font-size:20px">' + (emoji || '🏨') + '</span><span>' + (txt || 'Book a hotel') + subHtml + '</span>';
      }
    }
    // Widget title + tagline (inline card) — only override if non-empty, let template default show otherwise
    var _h4 = rt.querySelector('h4');
    if (_h4 && b.widgetTitle) _h4.textContent = b.widgetTitle;
    var _hdp = rt.querySelector('.hd p');
    if (_hdp && b.widgetTagline) _hdp.textContent = b.widgetTagline;
    // Inline card search button — show custom text+emoji
    var _btnEl = rt.querySelector('.btn');
    if (_btnEl && (b.buttonText || b.buttonEmoji)) {
      var _be = (b.buttonEmoji || '').replace(/[<>]/g,'');
      var _bt = (b.buttonText || '').replace(/[<>]/g,'').slice(0,30);
      _btnEl.textContent = (_be ? _be + ' ' : '') + (_bt || 'Search hotels') + ' →';
    }
    // Chat globals
    if (b.greetingText) window.__imptGreeting = b.greetingText;
    if (b.chatPlaceholder) window.__imptPlaceholder = b.chatPlaceholder;
    window.__imptHidePowered = !!b.hidePoweredBy;
    // Hide simple widget footer
    if (b.hidePoweredBy) {
      var hsEl = rt.querySelector('#impt-hide-ft');
      if (!hsEl) { hsEl = document.createElement('style'); hsEl.id = 'impt-hide-ft'; (rt.head || rt).appendChild(hsEl); }
      hsEl.textContent = '.ft{display:none!important}';
    }
  }

  function loadBrand(rt) {
    // Apply cached settings instantly — eliminates the color-flash on load
    try {
      var _lsk = '_impt_b_' + KEY;
      var _stored = localStorage.getItem(_lsk);
      if (_stored) _applyBrand(rt, JSON.parse(_stored));
    } catch(e) {}
    // Fetch fresh from API, update cache
    try {
      fetch(BRAND + '?key=' + encodeURIComponent(KEY))
        .then(function(r){ return r.json(); })
        .then(function(b) {
          if (!b) return;
          _applyBrand(rt, b);
          try { localStorage.setItem('_impt_b_' + KEY, JSON.stringify(b)); } catch(e) {}
        }).catch(function(){});
    } catch(e) {}
  }

  // Vertical colour themes
  var THEMES = {
    mtb:   { d1:'#1a2e05', d2:'#3a5c0a', br:'#5a8a1a', ca:'#d4e6b5', tx:'#1a2e05', ft:'#f0f7e8', fc:'#3a5c0a', fb:'#c4d9a5' },
    surf:  { d1:'#003366', d2:'#0055a4', br:'#0077cc', ca:'#b3d4f0', tx:'#00264d', ft:'#e8f2fb', fc:'#0055a4', fb:'#99c4e8' },
    golf:  { d1:'#1a3300', d2:'#2d5500', br:'#4a8800', ca:'#d4eab5', tx:'#1a3300', ft:'#eef7e0', fc:'#2d5500', fb:'#c0dea0' },
    lgbtq: { d1:'#5c0078', d2:'#8b00a8', br:'#b300d4', ca:'#e8b3f5', tx:'#3a004f', ft:'#f7eafc', fc:'#8b00a8', fb:'#d699f0' },
    walks: { d1:'#2a1a00', d2:'#6b3d00', br:'#a05a00', ca:'#edd5b0', tx:'#2a1a00', ft:'#faf3e8', fc:'#6b3d00', fb:'#e0c090' },
    scuba: { d1:'#001433', d2:'#002966', br:'#0042a8', ca:'#b0c8f5', tx:'#001433', ft:'#e8edfb', fc:'#002966', fb:'#9ab8f0' },
    clubs: { d1:'#1a001a', d2:'#4d004d', br:'#7a007a', ca:'#e8b0e8', tx:'#1a001a', ft:'#f9eaf9', fc:'#4d004d', fb:'#d999d9' },
    brands:{ d1:'#3a2e00', d2:'#9A7B12', br:'#C9A227', ca:'#ecddb0', tx:'#2a2000', ft:'#faf6e8', fc:'#7a6010', fb:'#e0cc90' },
    carbon:{ d1:'#0a2a00', d2:'#0a5c00', br:'#0a8f5b', ca:'#c8eed8', tx:'#0a2a00', ft:'#eafaf0', fc:'#0a5c00', fb:'#b0e0c8' },
    yoga:  { d1:'#2a0033', d2:'#5c006e', br:'#8a00a8', ca:'#e0b3f0', tx:'#1a0022', ft:'#f7e8fc', fc:'#5c006e', fb:'#cc99e8' },
  };

  function loadSurf(rt) {
    try {
      fetch(CONFIG_URL + '?key=' + encodeURIComponent(KEY)).then(function(r){ return r.json(); }).then(function(cfg) {
        var vertical = cfg && cfg.vertical;
        var th = THEMES[vertical];
        if (!th) return;
        var style = rt.querySelector('#impt-surf-style');
        if (!style) { style = document.createElement('style'); style.id = 'impt-surf-style'; (rt.head || rt).appendChild(style); }
        style.textContent = (
          '.hd{background:linear-gradient(135deg,' + th.d1 + ',' + th.d2 + ')!important}' +
          '.hd h4{color:#ffffff!important;font-size:17px!important;font-weight:700!important}' +
          '.hd p{color:rgba(255,255,255,.82)!important}' +
          '.card{border-color:' + th.ca + '!important}' +
          'label{color:' + th.d2 + '!important;font-weight:700!important;letter-spacing:.16em!important}' +
          'input,select{color:' + th.tx + '!important;border-color:' + th.ca + '!important;background:#fafaf8!important}' +
          'input:focus,select:focus{border-color:' + th.br + '!important;box-shadow:0 0 0 3px rgba(128,128,128,.15)!important;background:#fff!important}' +
          '.btn{background:linear-gradient(135deg,' + th.br + ',' + th.d2 + ')!important;color:#ffffff!important;font-weight:700!important;box-shadow:0 4px 18px -4px rgba(0,0,0,.3)!important}' +
          '.ft{background:' + th.ft + '!important;color:' + th.fc + '!important;border-top:1px solid ' + th.fb + '!important}' +
          '.brand span{color:rgba(255,255,255,.92)!important}' +
          '.fab{background:linear-gradient(135deg,' + th.d1 + ' 0%,' + th.d2 + ' 100%)!important;box-shadow:0 10px 30px -8px rgba(0,0,0,.4)!important}'
        );
      }).catch(function(){});
    } catch(e) {}
  }

  function track(evt, dest) {
    try {
      new Image().src = TRACK + '?key=' + encodeURIComponent(KEY) + '&evt=' + encodeURIComponent(evt) +
        '&ref=' + encodeURIComponent(HOST) + (dest ? '&dest=' + encodeURIComponent(dest) : '');
    } catch (e) {}
  }
  function pad(n){return (n<10?'0':'')+n;}
  function iso(d){return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());}
  var now = new Date(), ciD = new Date(now.getTime()+30*864e5), coD = new Date(now.getTime()+31*864e5);

  function go(rt) {
    var dest = (rt.getElementById('impt-dest').value || '').trim();
    var cin = rt.getElementById('impt-ci').value, cout = rt.getElementById('impt-co').value;
    var g = rt.getElementById('impt-guests').value;
    var url = 'https://swarm.impt.io/api/widget/r?key=' + encodeURIComponent(KEY) +
      (dest ? '&dest=' + encodeURIComponent(dest) : '') +
      '&checkIn=' + encodeURIComponent(cin) + '&checkOut=' + encodeURIComponent(cout) +
      '&adults=' + encodeURIComponent(g) + '&rooms=1';
    window.open(url, '_blank', 'noopener');
  }

  var ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C8FF7E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6"/><path d="M3 18h18"/><path d="M6 10V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v3"/></svg>';

  var CSS = '\
  :host{all:initial}\
  *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}\
  .card{background:#fff;border:1px solid rgba(8,66,58,.10);border-radius:18px;overflow:hidden;\
    box-shadow:0 18px 48px -18px rgba(8,42,58,.32);max-width:420px}\
  .fl{position:fixed;right:20px;bottom:20px;z-index:2147483000}\
  .fl.left{right:auto;left:20px}\
  .fl.left .card{right:auto;left:0}\
  .fab{display:inline-flex;align-items:center;gap:9px;cursor:pointer;border:0;\
    background:linear-gradient(135deg,#0b4a40,#0f5d50);color:#fff;font-size:14px;font-weight:600;\
    padding:13px 18px;border-radius:999px;box-shadow:0 10px 30px -8px rgba(11,74,64,.55);\
    transition:transform .18s ease,box-shadow .18s ease}\
  .fab:hover{transform:translateY(-2px)}\
  .fab small{font-weight:500;opacity:.82;font-size:11px}\
  .fl .card{position:absolute;right:0;bottom:0;width:360px;max-width:calc(100vw - 24px);\
    opacity:0;transform:translateY(12px) scale(.98);pointer-events:none;transition:opacity .2s,transform .2s}\
  .fl.open .card{opacity:1;transform:none;pointer-events:auto}\
  .fl.open .fab{display:none}\
  .hd{position:relative;padding:18px 20px;background:linear-gradient(135deg,#0b4a40,#0f5d50);color:#fff}\
  .hd h4{margin:0;font-size:16px;font-weight:600}\
  .hd p{margin:4px 0 0;font-size:11.5px;color:rgba(255,255,255,.78)}\
  .brand{display:flex;align-items:center;gap:8px;margin:0 0 8px;min-height:1px}\
  .brand img{height:24px;max-width:120px;object-fit:contain;border-radius:5px;background:#fff;padding:3px}\
  .brand span{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:rgba(255,255,255,.9);font-weight:700}\
  .x{position:absolute;top:14px;right:14px;width:28px;height:28px;border:0;border-radius:50%;cursor:pointer;\
    background:rgba(255,255,255,.14);color:#fff;font-size:16px;line-height:1;display:none;align-items:center;justify-content:center}\
  .fl .x{display:flex}\
  .x:hover{background:rgba(255,255,255,.26)}\
  .bd{padding:18px 20px 16px;display:grid;gap:12px}\
  label{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:#3a6b62;font-weight:600;display:block;margin:0 0 5px}\
  input,select{width:100%;height:44px;border:1px solid #dde7e3;border-radius:11px;padding:0 13px;font-size:14px;color:#08423a;background:#fff;outline:0;transition:border-color .15s,box-shadow .15s}\
  input:focus,select:focus{border-color:#0b4a40;box-shadow:0 0 0 3px rgba(11,74,64,.12)}\
  .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}\
  .btn{height:48px;border:0;border-radius:12px;background:#C8FF7E;color:#08423a;font-size:14.5px;font-weight:700;cursor:pointer;transition:filter .15s,transform .12s;margin-top:2px}\
  .btn:hover{filter:brightness(.96)}.btn:active{transform:scale(.99)}\
  .ft{padding:10px 20px;background:#FAF7F0;font-size:10.5px;color:#6b8a82;text-align:center}\
  @media(max-width:480px){.fl .card{width:calc(100vw - 24px)}.fl{right:12px;bottom:12px}.fl.left{right:auto;left:12px}}';

  function panelHTML(floating) {
    return '<style>'+CSS+'</style>'+
      (floating ? '<button class="fab" id="impt-fab">'+ICON+'<span>Book a hotel<br><small>5% back &middot; 1t CO&#8322; offset</small></span></button>' : '')+
      '<div class="card" role="dialog" aria-label="Book a hotel">'+
        '<div class="hd"><div class="brand" id="impt-brand"></div><h4>'+TITLE+'</h4><p>5% cash back &middot; 1 tonne CO&#8322; offset per night</p>'+
          '<button class="x" id="impt-x" aria-label="Close">&times;</button></div>'+
        '<div class="bd">'+
          '<div><label>Destination</label><input id="impt-dest" placeholder="City, region or hotel" autocomplete="off"></div>'+
          '<div class="row"><div><label>Check in</label><input id="impt-ci" type="date" value="'+iso(ciD)+'"></div>'+
            '<div><label>Check out</label><input id="impt-co" type="date" value="'+iso(coD)+'"></div></div>'+
          '<div><label>Guests</label><select id="impt-guests"><option value="2">2 guests</option><option value="1">1 guest</option><option value="3">3 guests</option><option value="4">4 guests</option><option value="5">5 guests</option><option value="6">6 guests</option></select></div>'+
          '<button class="btn" id="impt-go">Search hotels &rarr;</button>'+
        '</div><div class="ft">Powered by IMPT &mdash; book anywhere, earn rewards</div>'+
      '</div>';
  }

  function wire(rt, floating, wrap) {
    if (floating) {
      rt.getElementById('impt-fab').addEventListener('click', function(){ wrap.classList.add('open'); track('view'); });
      rt.getElementById('impt-x').addEventListener('click', function(){ wrap.classList.remove('open'); });
    }
    rt.getElementById('impt-go').addEventListener('click', function(){ go(rt); });
    rt.getElementById('impt-dest').addEventListener('keydown', function(e){ if(e.key==='Enter') go(rt); });
    _addWhatsApp(rt);
  }

  // WhatsApp entry point on EVERY widget render (additive, 2026-06-28) — book via Laura's AI on WhatsApp.
  function _addWhatsApp(rt) {
    try {
      var bd = rt.querySelector('.bd');
      if (!bd || rt.getElementById('impt-wa')) return;
      var host = '';
      try { host = location.hostname; } catch (e) {}
      var a = document.createElement('a');
      a.id = 'impt-wa';
      a.href = 'https://wa.me/353877868878?text=' +
        encodeURIComponent('Hi IMPT — I want to book a hotel' + (host ? ' (from ' + host + ')' : ''));
      a.target = '_blank'; a.rel = 'noopener';
      a.innerHTML = '&#128172; Book on WhatsApp &mdash; we find it for you';
      a.setAttribute('style', [
        'display:block;width:100%;box-sizing:border-box;padding:11px 0;margin-top:8px;text-align:center;',
        'background:#25D366;border:none;border-radius:12px;color:#073d27;font-size:13px;font-weight:700;',
        'cursor:pointer;text-decoration:none;font-family:inherit;letter-spacing:.01em;'
      ].join(''));
      a.addEventListener('click', function(){ try { track('whatsapp'); } catch (e) {} });
      bd.appendChild(a);
    } catch (e) {}
  }

  function _addChatBtn(rt, inlineHost) {
    var btn = document.createElement('button');
    btn.textContent = '🤖 AI Concierge';
    btn.setAttribute('style', [
      'display:block;width:100%;padding:11px 0;margin-top:8px;',
      'background:transparent;border:1.5px solid rgba(10,143,91,.35);border-radius:12px;',
      'color:#0a8f5b;font-size:13px;font-weight:600;cursor:pointer;',
      'transition:background .18s,border-color .18s;font-family:inherit;letter-spacing:.01em;'
    ].join(''));
    btn.addEventListener('mouseover', function(){ this.style.background='rgba(10,143,91,.07)'; this.style.borderColor='rgba(10,143,91,.7)'; });
    btn.addEventListener('mouseout',  function(){ this.style.background='transparent'; this.style.borderColor='rgba(10,143,91,.35)'; });
    btn.addEventListener('click', function() { _mountChat(rt, inlineHost); });
    var bd = rt.querySelector('.bd');
    if (bd) bd.appendChild(btn);
  }

  function _mountChat(rt, inlineHost) {
    while (rt.firstChild) rt.removeChild(rt.firstChild);
    inlineHost.style.cssText = 'display:none';

    var chatBox = document.createElement('div');
    chatBox.id = 'impt-chatbox';
    chatBox.style.cssText = 'width:100%;max-width:420px;';
    inlineHost.parentNode.insertBefore(chatBox, inlineHost.nextSibling);

    var chatWrap = document.createElement('div');
    chatWrap.style.cssText = 'height:520px;';
    chatBox.appendChild(chatWrap);

    function backFn() {
      chatBox.parentNode.removeChild(chatBox);
      inlineHost.style.cssText = '';
      rt.innerHTML = panelHTML(false);
      wire(rt, false, null);
      loadBrand(rt);
      loadSurf(rt);
      _addChatBtn(rt, inlineHost);
    }


    function injectBackArrow() {
      // Replace the pulsing dot with a ← back button
      var dot = chatWrap.querySelector('.animate-pulse');
      if (!dot) return;
      var arrow = document.createElement('button');
      arrow.innerHTML = '&#8592;';
      arrow.title = 'Back to search';
      arrow.style.cssText = 'background:rgba(255,255,255,.22);border:none;color:#fff;font-size:15px;font-weight:700;' +
        'cursor:pointer;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;' +
        'justify-content:center;flex-shrink:0;transition:background .15s;padding:0;';
      arrow.addEventListener('mouseover', function(){ this.style.background='rgba(255,255,255,.38)'; });
      arrow.addEventListener('mouseout',  function(){ this.style.background='rgba(255,255,255,.22)'; });
      arrow.addEventListener('click', backFn);
      dot.parentNode.replaceChild(arrow, dot);
    }

    function doMount() {
      window.IMPTChat.mount({ root: chatWrap, variant: 'embedded', partnerKey: KEY,
        greetingText: window.__imptGreeting || '', chatPlaceholder: window.__imptPlaceholder || '',
        hidePoweredBy: !!window.__imptHidePowered, primaryColor: window.__imptPrimaryColor || '' });
      setTimeout(injectBackArrow, 300);
    }

    function loadChatJs(cb) {
      if (window.IMPTChat) { cb(); return; }
      var cs = document.createElement('script');
      cs.src = 'https://swarm.impt.io/assets/chat.js?v=20260626b';
      cs.onload = function() { if (window.IMPTChat) cb(); };
      document.head.appendChild(cs);
    }

    function ensureTailwind(cb) {
      if (window.tailwind) { cb(); return; }
      if (document.querySelector('script[src*="cdn.tailwindcss.com"]')) { cb(); return; }
      var tw = document.createElement('script');
      tw.src = 'https://cdn.tailwindcss.com?plugins=typography,line-clamp';
      tw.onload = function() {
        if (window.tailwind && window.tailwind.config) {
          window.tailwind.config = {
            theme: { extend: { colors: {
              'impt-green': '#0a8f5b', 'impt-dark': '#1C3829',
              'impt-cream': '#F4F1EA', 'impt-accent': '#E8A838',
            }}}
          };
        }
        cb();
      };
      document.head.appendChild(tw);
    }

    ensureTailwind(function() { loadChatJs(doMount); });
  }

  function _addChatBtnFloat(rt, wrap, host) {
    var btn = document.createElement('button');
    btn.textContent = '🤖 AI Concierge';
    btn.setAttribute('style', [
      'display:block;width:100%;padding:11px 0;margin-top:8px;',
      'background:transparent;border:1.5px solid rgba(10,143,91,.35);border-radius:12px;',
      'color:#0a8f5b;font-size:13px;font-weight:600;cursor:pointer;',
      'transition:background .18s,border-color .18s;font-family:inherit;letter-spacing:.01em;'
    ].join(''));
    btn.addEventListener('mouseover', function(){ this.style.background='rgba(10,143,91,.07)'; this.style.borderColor='rgba(10,143,91,.7)'; });
    btn.addEventListener('mouseout',  function(){ this.style.background='transparent'; this.style.borderColor='rgba(10,143,91,.35)'; });
    btn.addEventListener('click', function() { _mountChatFloat(rt, wrap, host); });
    var bd = rt.querySelector('.bd'); if (bd) bd.appendChild(btn);
  }

  function _mountChatFloat(rt, wrap, host) {
    while (rt.firstChild) rt.removeChild(rt.firstChild);
    var chatBox = document.createElement('div'); chatBox.id = 'impt-chatbox';
    chatBox.style.cssText = 'position:fixed;bottom:20px;right:20px;width:420px;max-width:calc(100vw - 24px);z-index:2147483647;';
    document.body.appendChild(chatBox);
    var chatWrap = document.createElement('div'); chatWrap.style.cssText = 'height:520px;';
    chatBox.appendChild(chatWrap);

    function backFn() {
      document.body.removeChild(chatBox);
      var nw = document.createElement('div'); nw.className = 'fl';
      nw.innerHTML = panelHTML(true); rt.appendChild(nw);
      wire(rt, true, nw); loadBrand(rt); loadSurf(rt);
      _addChatBtnFloat(rt, nw, host); nw.classList.add('open');
    }

    function injectBackArrow() {
      var dot = chatWrap.querySelector('.animate-pulse'); if (!dot) return;
      var arrow = document.createElement('button');
      arrow.innerHTML = '&#8592;'; arrow.title = 'Back to search';
      arrow.style.cssText = 'background:rgba(255,255,255,.22);border:none;color:#fff;font-size:15px;font-weight:700;' +
        'cursor:pointer;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;' +
        'justify-content:center;flex-shrink:0;transition:background .15s;padding:0;';
      arrow.addEventListener('mouseover', function(){ this.style.background='rgba(255,255,255,.38)'; });
      arrow.addEventListener('mouseout',  function(){ this.style.background='rgba(255,255,255,.22)'; });
      arrow.addEventListener('click', backFn);
      dot.parentNode.replaceChild(arrow, dot);
    }
    function doMount() {
      window.IMPTChat.mount({ root: chatWrap, variant: 'embedded', partnerKey: KEY,
        greetingText: window.__imptGreeting || '', chatPlaceholder: window.__imptPlaceholder || '',
        hidePoweredBy: !!window.__imptHidePowered, primaryColor: window.__imptPrimaryColor || '' });
      setTimeout(injectBackArrow, 300);
    }
    function loadChatJs(cb) {
      if (window.IMPTChat) { cb(); return; }
      var cs = document.createElement('script');
      cs.src = 'https://swarm.impt.io/assets/chat.js?v=20260626b';
      cs.onload = function() { if (window.IMPTChat) cb(); };
      document.head.appendChild(cs);
    }
    function ensureTailwind(cb) {
      if (window.tailwind) { cb(); return; }
      if (document.querySelector('script[src*="cdn.tailwindcss.com"]')) { cb(); return; }
      var tw = document.createElement('script');
      tw.src = 'https://cdn.tailwindcss.com?plugins=typography,line-clamp';
      tw.onload = function() {
        if (window.tailwind && window.tailwind.config) {
          window.tailwind.config = { theme: { extend: { colors: {
            'impt-green': '#0a8f5b', 'impt-dark': '#1C3829',
            'impt-cream': '#F4F1EA', 'impt-accent': '#E8A838' } } } };
        } cb();
      }; document.head.appendChild(tw);
    }
    ensureTailwind(function() { loadChatJs(doMount); });
  }

  function _mountDropdown() {
    var inlineHost = document.getElementById('impt-swarm') || document.querySelector('[data-impt-swarm]');
    if (inlineHost) {
      var rt = inlineHost.attachShadow ? inlineHost.attachShadow({mode:'open'}) : inlineHost;
      rt.innerHTML = panelHTML(false);
      wire(rt, false, null);
      loadBrand(rt);
      loadSurf(rt);
      // Expose live-preview hook for dashboard customization page
      window.__imptApplyBrand = function(b) { _applyBrand(rt, b); };
      track('view');
      try {
        fetch('https://swarm.impt.io/api/widget/fuel?key=' + encodeURIComponent(KEY))
          .then(function(r) { return r.ok ? r.json() : null; })
          .then(function(fuel) {
            if (fuel && fuel.features && fuel.features.chat_enabled && fuel.balance > 0) {
              _addChatBtn(rt, inlineHost);
            }
          }).catch(function(){});
      } catch(e) {}
    } else {
      var host = document.createElement('div');
      document.body.appendChild(host);
      var rt2 = host.attachShadow ? host.attachShadow({mode:'open'}) : host;
      var wrap = document.createElement('div'); wrap.className='fl';
      wrap.innerHTML = panelHTML(true);
      rt2.appendChild(wrap);
      wire(rt2, true, wrap);
      loadBrand(rt2);
      loadSurf(rt2);
      try {
        fetch('https://swarm.impt.io/api/widget/fuel?key=' + encodeURIComponent(KEY))
          .then(function(r) { return r.ok ? r.json() : null; })
          .then(function(fuel) {
            if (fuel && fuel.features && fuel.features.chat_enabled && fuel.balance > 0) {
              _addChatBtnFloat(rt2, wrap, host);
            }
          }).catch(function(){});
      } catch(e) {}
      function flip(left){ wrap.classList.toggle('left', left); try{ host.setAttribute('data-impt-side', left?'left':'right'); }catch(_){ } }
      function place(){
        try{
          if(POS==='left'){ flip(true); return; }
          if(POS==='right'){ flip(false); return; }
          var vw=window.innerWidth, vh=window.innerHeight, all=document.body.getElementsByTagName('*'), taken=false;
          for(var i=0;i<all.length;i++){ var e=all[i];
            if(e===host||(host.contains&&host.contains(e))) continue;
            var s; try{ s=getComputedStyle(e); }catch(_){ continue; }
            if(s.position!=='fixed' && s.position!=='sticky') continue;
            if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity||'1')===0) continue;
            var r=e.getBoundingClientRect();
            if(r.width<8||r.height<8||r.width>vw*0.85) continue;
            if(r.left>vw*0.5 && r.right>vw-170 && r.bottom>vh*0.5){ taken=true; break; }
          }
          flip(taken);
        }catch(e){}
      }
      place(); [600,1500,3500,7000].forEach(function(t){ setTimeout(place, t); });
      window.addEventListener('resize', place);
      if(window.MutationObserver){ try{ new MutationObserver(place).observe(document.body,{childList:true,subtree:false}); }catch(e){} }
      track('load');
    }
  }

  // Always-on WhatsApp bubble on EVERY page the widget loads (Mike 2026-06-28: WhatsApp owns the whole CTA).
  // Independent of the booking card; bottom-LEFT so it never collides with the bottom-right launcher.
  function _imptWaBubble() {
    // Single source of truth: load the canonical help-bubble script (the inviting labelled pill).
    try {
      if (window.__imptWaBubble || document.getElementById('impt-wa-bubble') ||
          document.querySelector('script[src*="wa-bubble.js"]')) return;
      var s = document.createElement('script');
      s.src = 'https://swarm.impt.io/wa-bubble.js'; s.async = true;
      document.head.appendChild(s);
    } catch (e) {}
  }

  function mount() { _mountDropdown(); _imptWaBubble(); }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
