/*!
 * IMPT Swarm Widget — Launcher v1.0.0 (2026-06-07)
 * Professional collapsible booking launcher, bottom-right, Shadow-DOM isolated.
 * Embed: <script src="https://swarm.impt.io/widget-launcher.js" data-key="YOUR_KEY" async></script>
 * Redirects to app.impt.io/find-hotel-input with utm_source=swarm-<key> (channel=widget).
 * MIT — IMPT Systems Limited.
 */
(function () {
  'use strict';
  if (window.__imptLauncher) return; window.__imptLauncher = 1;
  var REDIRECT = 'https://app.impt.io/find-hotel-input';
  var TRACK = 'https://swarm.impt.io/api/widget/track';
  var me = document.currentScript ||
    document.querySelector('script[src*="widget-launcher.js"]');
  var KEY = (me && me.getAttribute('data-key')) || 'swarm-public';
  var HOST = location.host;
  var BRAND = 'https://swarm.impt.io/api/widget/brand';
  var POS = (me && me.getAttribute('data-position')) || 'auto';

  function track(evt, dest) {
    try {
      var u = TRACK + '?key=' + encodeURIComponent(KEY) + '&evt=' + encodeURIComponent(evt) +
        '&ref=' + encodeURIComponent(HOST) + (dest ? '&dest=' + encodeURIComponent(dest) : '');
      new Image().src = u;
    } catch (e) {}
  }
  function pad(n){return (n<10?'0':'')+n;}
  function iso(d){return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());}
  var now = new Date();
  var ci = new Date(now.getTime()+30*864e5), co = new Date(now.getTime()+31*864e5);

  function go() {
    var dest = (root.getElementById('impt-dest').value || '').trim();
    var cin = root.getElementById('impt-ci').value, cout = root.getElementById('impt-co').value;
    var g = root.getElementById('impt-guests').value;
    track('click', dest || '(open)');
    // Route via /api/widget/r so vertical widgets land on THEIR page (mtb/surf/walks/worlds),
    // never the main hotel search, and the .impt.io attribution cookie is set (Mike 2026-06-13).
    var url = 'https://swarm.impt.io/api/widget/r?key=' + encodeURIComponent(KEY) +
      '&med=launcher' +
      (dest ? '&dest=' + encodeURIComponent(dest) : '') +
      '&checkIn=' + encodeURIComponent(cin) + '&checkOut=' + encodeURIComponent(cout) +
      '&adults=' + encodeURIComponent(g) + '&rooms=1';
    window.open(url, '_blank', 'noopener');
  }

  var ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C8FF7E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6"/><path d="M3 18h18"/><path d="M6 10V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v3"/></svg>';

  var host = document.createElement('div');
  host.setAttribute('aria-label', 'IMPT hotel booking');
  document.body.appendChild(host);
  var root = host.attachShadow ? host.attachShadow({mode:'open'}) : host;

  var CSS = '\
  :host{all:initial}\
  *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}\
  .wrap{position:fixed;right:20px;bottom:20px;z-index:2147483000}\
  .wrap.left{right:auto;left:20px}\
  .wrap.left .panel{right:auto;left:0}\
  .fab{display:inline-flex;align-items:center;gap:9px;cursor:pointer;border:0;\
    background:linear-gradient(135deg,#0b4a40,#0f5d50);color:#fff;font-size:14px;font-weight:600;\
    padding:13px 18px;border-radius:999px;box-shadow:0 10px 30px -8px rgba(11,74,64,.55);\
    transition:transform .18s ease,box-shadow .18s ease}\
  .fab:hover{transform:translateY(-2px);box-shadow:0 16px 38px -8px rgba(11,74,64,.6)}\
  .fab small{font-weight:500;opacity:.8;font-size:11px}\
  .panel{position:absolute;right:0;bottom:0;width:360px;max-width:calc(100vw - 24px);\
    background:#fff;border:1px solid rgba(8,66,58,.08);border-radius:20px;overflow:hidden;\
    box-shadow:0 28px 64px -16px rgba(8,42,58,.45);opacity:0;transform:translateY(12px) scale(.98);\
    pointer-events:none;transition:opacity .2s ease,transform .2s ease}\
  .open .panel{opacity:1;transform:none;pointer-events:auto}\
  .open .fab{display:none}\
  .hd{position:relative;padding:18px 20px;background:linear-gradient(135deg,#0b4a40,#0f5d50);color:#fff}\
  .hd h4{margin:0;font-size:16px;font-weight:600;letter-spacing:.1px}\
  .hd p{margin:4px 0 0;font-size:11.5px;color:rgba(255,255,255,.78)}\
  .brand{display:flex;align-items:center;gap:8px;margin:0 0 8px;min-height:1px}\
  .brand img{height:24px;max-width:120px;object-fit:contain;border-radius:5px;background:#fff;padding:3px}\
  .brand span{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:rgba(255,255,255,.9);font-weight:700}\
  .x{position:absolute;top:14px;right:14px;width:28px;height:28px;border:0;border-radius:50%;cursor:pointer;\
    background:rgba(255,255,255,.14);color:#fff;font-size:16px;line-height:1;display:flex;align-items:center;justify-content:center}\
  .x:hover{background:rgba(255,255,255,.26)}\
  .bd{padding:18px 20px 16px;display:grid;gap:12px}\
  label{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:#3a6b62;font-weight:600;display:block;margin:0 0 5px}\
  input,select{width:100%;height:44px;border:1px solid #dde7e3;border-radius:11px;padding:0 13px;\
    font-size:14px;color:#08423a;background:#fff;outline:0;transition:border-color .15s,box-shadow .15s}\
  input:focus,select:focus{border-color:#0b4a40;box-shadow:0 0 0 3px rgba(11,74,64,.12)}\
  .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}\
  .btn{height:48px;border:0;border-radius:12px;background:#C8FF7E;color:#08423a;font-size:14.5px;font-weight:700;\
    cursor:pointer;transition:filter .15s,transform .12s;margin-top:2px}\
  .btn:hover{filter:brightness(.96)}\
  .btn:active{transform:scale(.99)}\
  .ft{padding:10px 20px;background:#FAF7F0;font-size:10.5px;color:#6b8a82;text-align:center}\
  @media(max-width:480px){.panel{width:calc(100vw - 24px)}.wrap{right:12px;bottom:12px}.wrap.left{right:auto;left:12px}}';

  root.innerHTML = '<style>'+CSS+'</style>'+
    '<div class="wrap" id="impt-wrap">'+
      '<button class="fab" id="impt-fab">'+ICON+'<span>Book a hotel<br><small>5% back · 1t CO₂ offset</small></span></button>'+
      '<div class="panel" role="dialog" aria-label="Book a hotel">'+
        '<div class="hd"><div class="brand" id="impt-brand"></div><h4>Book your stay</h4><p>5% cash back · 1 tonne CO₂ offset per night</p>'+
          '<button class="x" id="impt-x" aria-label="Close">&times;</button></div>'+
        '<div class="bd">'+
          '<div><label>Destination</label><input id="impt-dest" placeholder="City, region or hotel" autocomplete="off"></div>'+
          '<div class="row">'+
            '<div><label>Check in</label><input id="impt-ci" type="date" value="'+iso(ci)+'"></div>'+
            '<div><label>Check out</label><input id="impt-co" type="date" value="'+iso(co)+'"></div>'+
          '</div>'+
          '<div><label>Guests</label><select id="impt-guests">'+
            '<option value="2">2 guests</option><option value="1">1 guest</option>'+
            '<option value="3">3 guests</option><option value="4">4 guests</option>'+
            '<option value="5">5 guests</option><option value="6">6 guests</option></select></div>'+
          '<button class="btn" id="impt-go">Search hotels &rarr;</button>'+
        '</div>'+
        '<div class="ft">Powered by IMPT — book anywhere, earn rewards</div>'+
      '</div>'+
    '</div>';

  try {
    fetch(BRAND + '?key=' + encodeURIComponent(KEY)).then(function(r){return r.json();}).then(function(b){
      if (!b || (!b.name && !b.logo)) return;
      var el = root.getElementById('impt-brand'); if (!el) return;
      var h = '';
      if (b.logo) h += '<img src="' + b.logo + '" alt="">';
      if (b.name) h += '<span>' + String(b.name).replace(/[<>]/g,'').slice(0,40) + '</span>';
      el.innerHTML = h;
    }).catch(function(){});
  } catch (e) {}
  var wrap = root.getElementById('impt-wrap');
  root.getElementById('impt-fab').addEventListener('click', function(){ wrap.classList.add('open'); track('view'); });
  root.getElementById('impt-x').addEventListener('click', function(){ wrap.classList.remove('open'); });
  root.getElementById('impt-go').addEventListener('click', go);
  root.getElementById('impt-dest').addEventListener('keydown', function(e){ if(e.key==='Enter') go(); });
  // Don't cover an existing bottom-right widget (chat/AI tools etc.) — flip to bottom-left if the corner is taken.
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
        if(r.width<8||r.height<8||r.width>vw*0.85) continue;            // skip full-width bars/navs
        if(r.left>vw*0.5 && r.right>vw-170 && r.bottom>vh*0.5){ taken=true; break; }  // something already bottom-right
      }
      flip(taken);
    }catch(e){}
  }
  place(); [600,1500,3500,7000].forEach(function(t){ setTimeout(place, t); });
  window.addEventListener('resize', place);
  if(window.MutationObserver){ try{ new MutationObserver(place).observe(document.body,{childList:true,subtree:false}); }catch(e){} }
  track('load');
})();
