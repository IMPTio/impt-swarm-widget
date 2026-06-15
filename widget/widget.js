/*!
 * IMPT Swarm Widget v2.0.0 (2026-06-07) — professional, shadow-DOM isolated.
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
  var TITLE = (me && me.getAttribute('data-title')) || 'Book your stay';  /* v2.1 brand name */
  var HOST = location.host;
  var BRAND = 'https://swarm.impt.io/api/widget/brand';
  var POS = (me && me.getAttribute('data-position')) || 'auto';
  function loadBrand(rt) {
    try {
      fetch(BRAND + '?key=' + encodeURIComponent(KEY)).then(function(r){return r.json();}).then(function(b){
        if (!b || (!b.name && !b.logo)) return;
        var el = rt.getElementById('impt-brand'); if (!el) return;
        var h = '';
        if (b.logo) h += '<img src="' + b.logo + '" alt="">';
        if (b.name) h += '<span>' + String(b.name).replace(/[<>]/g,'').slice(0,40) + '</span>';
        el.innerHTML = h;
      }).catch(function(){});
    } catch (e) {}
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
    // Route via swarm.impt.io/api/widget/r — it logs the click, sets the first-party
    // impt_partner cookie on .impt.io (so the booking attributes to THIS partner),
    // then 302s to the search. This is what makes partner bookings show on the dashboard.
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
  }

  function mount() {
    var inlineHost = document.getElementById('impt-swarm') || document.querySelector('[data-impt-swarm]');
    if (inlineHost) {
      var rt = inlineHost.attachShadow ? inlineHost.attachShadow({mode:'open'}) : inlineHost;
      rt.innerHTML = panelHTML(false);
      wire(rt, false, null);
      loadBrand(rt);
      track('view');
    } else {
      var host = document.createElement('div');
      document.body.appendChild(host);
      var rt2 = host.attachShadow ? host.attachShadow({mode:'open'}) : host;
      var wrap = document.createElement('div'); wrap.className='fl';
      wrap.innerHTML = panelHTML(true);
      rt2.appendChild(wrap);
      wire(rt2, true, wrap);
      loadBrand(rt2);
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
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
