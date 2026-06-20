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
  var CONFIG_URL = 'https://swarm.impt.io/api/widget/config';
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


  var SURF_DESTS = [
    ['Asia','Pecatu, Bali — 9 breaks','Pecatu Bali'],
    ['Asia','Siargao, Philippines — 8 breaks','Siargao'],
    ['Asia','Canggu, Bali — 6 breaks','Canggu Bali'],
    ['Asia','Uluwatu, Bali — 6 breaks','Uluwatu Bali'],
    ['Asia','Maldives — 5 breaks','Maldives'],
    ['Asia','Arugam Bay, Sri Lanka — 4 breaks','Arugam Bay'],
    ['Asia','Kuta Lombok — 3 breaks','Kuta Lombok'],
    ['Asia','Kuta, Bali — 3 breaks','Kuta Bali'],
    ['Asia','Nusa Lembongan, Bali — 3 breaks','Nusa Lembongan'],
    ['Asia','Matara, Sri Lanka — 3 breaks','Matara Sri Lanka'],
    ['Asia','Tabanan, Bali — 3 breaks','Tabanan Bali'],
    ['Asia','Tel Aviv, Israel — 3 breaks','Tel Aviv'],
    ['Asia','Midigama, Sri Lanka — 2 breaks','Midigama'],
    ['Asia','Weligama, Sri Lanka — 1 break','Weligama'],
    ['Asia','Ahangama, Sri Lanka — 1 break','Ahangama'],
    ['Asia','Keramas, Bali — 1 break','Keramas Bali'],
    ['Asia','Sanur, Bali — 1 break','Sanur Bali'],
    ['Asia','Serangan, Bali — 1 break','Serangan Bali'],
    ['Asia','Sumba, Indonesia — 1 break','Sumba'],
    ['Asia','Sumbawa, Indonesia — 1 break','Sumbawa'],
    ['Asia','Nias, Indonesia — 1 break','Nias'],
    ['Asia','Cimaja, Java — 1 break','Cimaja Java'],
    ['Asia','Timor — 1 break','Timor'],
    ['Asia','West Papua — 1 break','West Papua'],
    ['Asia','Hainan Island, China — 1 break','Hainan Island'],
    ['Asia','Chigasaki, Japan — 1 break','Chigasaki'],
    ['Asia','Taiwan — 1 break','Taiwan'],
    ['Europe','Ericeira, Portugal — 12 breaks','Ericeira'],
    ['Europe','Capbreton, France — 7 breaks','Capbreton'],
    ['Europe','Seignosse, France — 6 breaks','Seignosse'],
    ['Europe','Fuerteventura — 5 breaks','Fuerteventura Canary Islands'],
    ['Europe','Hossegor, France — 4 breaks','Hossegor'],
    ['Europe','Aljezur, Portugal — 3 breaks','Aljezur'],
    ['Europe','Nazar\u00e9, Portugal — 3 breaks','Nazar\u00e9'],
    ['Europe','Landes, France — 3 breaks','Landes France'],
    ['Europe','Basque Coast, France — 3 breaks','Basque Coast France'],
    ['Europe','Peniche, Portugal — 2 breaks','Peniche'],
    ['Europe','Algarve, Portugal — 2 breaks','Algarve'],
    ['Europe','Bundoran, Ireland — 2 breaks','Bundoran'],
    ['Europe','Figueira da Foz, Portugal — 2 breaks','Figueira da Foz'],
    ['Europe','Canary Islands, Spain — 2 breaks','Canary Islands'],
    ['Europe','Biarritz, France — 1 break','Biarritz'],
    ['Europe','Lagos, Portugal — 1 break','Lagos Portugal'],
    ['Europe','Comporta, Portugal — 1 break','Comporta'],
    ['Europe','Santa Cruz, Portugal — 1 break','Santa Cruz Portugal'],
    ['Europe','Sintra, Portugal — 1 break','Sintra'],
    ['Europe','Newquay, UK — 1 break','Newquay'],
    ['Europe','Pembrokeshire, Wales — 1 break','Pembrokeshire Wales'],
    ['Europe','Zarautz, Spain — 1 break','Zarautz'],
    ['Europe','San Sebasti\u00e1n, Spain — 1 break','San Sebasti\u00e1n'],
    ['Europe','Sopelana, Spain — 1 break','Sopelana'],
    ['Europe','Cantabria, Spain — 1 break','Cantabria'],
    ['Europe','Vejer de la Frontera, Spain — 1 break','Vejer de la Frontera C\u00e1diz'],
    ['Europe','Hoddevik, Norway — 1 break','Hoddevik'],
    ['Europe','Lofoten Islands, Norway — 1 break','Lofoten Islands'],
    ['Americas','Oahu, Hawaii — 18 breaks','Oahu Hawaii'],
    ['Americas','Tamarindo, Costa Rica — 9 breaks','Tamarindo Guanacaste'],
    ['Americas','San Clemente, California — 8 breaks','San Clemente California'],
    ['Americas','Popoyo, Nicaragua — 8 breaks','Popoyo Tola'],
    ['Americas','Rinc\u00f3n, Puerto Rico — 7 breaks','Rinc\u00f3n'],
    ['Americas','Puntarenas, Costa Rica — 7 breaks','Puntarenas'],
    ['Americas','Tumbes, Peru — 7 breaks','Tumbes'],
    ['Americas','Guanacaste, Costa Rica — 6 breaks','Guanacaste'],
    ['Americas','Lima, Peru — 6 breaks','Lima'],
    ['Americas','Lima Province, Peru — 6 breaks','Lima Province'],
    ['Americas','San Juan del Sur, Nicaragua — 5 breaks','San Juan del Sur'],
    ['Americas','Piura, Peru — 5 breaks','Piura'],
    ['Americas','Lambayeque, Peru — 4 breaks','Lambayeque Peru'],
    ['Americas','Waikiki, Hawaii — 3 breaks','Waikiki Honolulu Hawaii'],
    ['Americas','Santa Cruz, California — 3 breaks','Santa Cruz California'],
    ['Americas','Encinitas, California — 3 breaks','Encinitas California'],
    ['Americas','Outer Banks, NC — 3 breaks','Outer Banks North Carolina'],
    ['Americas','Nosara, Costa Rica — 3 breaks','Nosara Guanacaste'],
    ['Americas','Santa Teresa, Costa Rica — 3 breaks','Santa Teresa Puntarenas'],
    ['Americas','Puerto Viejo, Costa Rica — 3 breaks','Puerto Viejo de Talamanca Lim\u00f3n'],
    ['Americas','Puerto Escondido, Mexico — 3 breaks','Puerto Escondido Oaxaca'],
    ['Americas','Nayarit, Mexico — 3 breaks','Nayarit'],
    ['Americas','Tofino, Canada — 3 breaks','Tofino British Columbia'],
    ['Americas','Arequipa, Peru — 2 breaks','Arequipa Peru'],
    ['Americas','El Tunco, El Salvador — 2 breaks','El Tunco La Libertad'],
    ['Americas','Puerto Rico — 2 breaks','Puerto Rico'],
    ['Americas','Kauai, Hawaii — 1 break','Kauai Hawaii'],
    ['Americas','Maui, Hawaii — 1 break','Maui Hawaii'],
    ['Americas','Malibu, California — 1 break','Malibu California'],
    ['Americas','Half Moon Bay, CA — 1 break','Half Moon Bay California'],
    ['Americas','Rockaway Beach, NY — 1 break','Rockaway Beach New York'],
    ['Americas','San Onofre, CA — 1 break','San Onofre California'],
    ['Americas','Baja California, Mexico — 1 break','Baja California'],
    ['Americas','Lobitos, Peru — 1 break','Lobitos Piura'],
    ['Americas','M\u00e1ncora, Peru — 1 break','M\u00e1ncora Piura'],
    ['Americas','Paracas, Peru — 1 break','Paracas Ica'],
    ['Americas','Trujillo, Peru — 1 break','Trujillo Peru'],
    ['Americas','Bocas del Toro, Panama — 1 break','Bocas del Toro'],
    ['Americas','Ped\u00e1s\u00ed, Panama — 1 break','Ped\u00e1s\u00ed Los Santos'],
    ['Americas','El Sunzal, El Salvador — 1 break','El Sunzal La Libertad'],
    ['Americas','Pichilemu, Chile — 1 break','Pichilemu'],
    ['Americas','Florian\u00f3polis, Brazil — 1 break','Florian\u00f3polis'],
    ['Americas','Anguilla — 1 break','Anguilla'],
    ['Americas','Antigua — 1 break','Antigua'],
    ['Americas','Barbados — 1 break','Barbados'],
    ['Americas','Grenada — 1 break','Grenada'],
    ['Americas','Jamaica — 1 break','Jamaica'],
    ['Africa','Jeffreys Bay, South Africa — 10 breaks','Jeffreys Bay'],
    ['Africa','Taghazout, Morocco — 4 breaks','Taghazout'],
    ['Africa','Muizenberg, Cape Town — 1 break','Muizenberg Cape Town'],
    ['Africa','Cape Peninsula — 1 break','Cape Peninsula'],
    ['Africa','Cape St Francis — 1 break','Cape St Francis'],
    ['Africa','Tofo, Mozambique — 1 break','Tofo'],
    ['Pacific','Byron Bay, Australia — 9 breaks','Byron Bay NSW'],
    ['Pacific','Gold Coast, Australia — 9 breaks','Gold Coast Queensland'],
    ['Pacific','Byron Shire, Australia — 9 breaks','Byron Shire NSW'],
    ['Pacific','Tavarua, Fiji — 7 breaks','Tavarua Fiji'],
    ['Pacific','Raglan, New Zealand — 3 breaks','Raglan'],
    ['Pacific','Brunswick Heads, Australia — 2 breaks','Brunswick Heads NSW'],
    ['Pacific','Ballina, Australia — 1 break','Ballina NSW'],
    ['Pacific','Noosa Heads, Australia — 1 break','Noosa Heads Queensland'],
    ['Pacific','Manly, Australia — 1 break','Manly NSW'],
    ['Pacific','Queenstown, New Zealand — 1 break','Queenstown'],
    ['Pacific','Samoa — 1 break','Samoa'],
    ['Pacific','Vanuatu — 1 break','Vanuatu'],
    ['Pacific','Papua New Guinea — 1 break','Papua New Guinea']
  ];

  function buildSurfOpts(region) {
    var opts = '<option value="">Choose a surf spot\u2026</option>';
    var list = region ? SURF_DESTS.filter(function(d){return d[0]===region;}) : SURF_DESTS;
    list.forEach(function(d){ opts += '<option value="'+d[2]+'">'+d[1]+'</option>'; });
    return opts;
  }

  // Colour themes per vertical — deep1/deep2 (header gradient) + bright (focus/btn accent)
  var WIDGET_THEMES = {
    surf:   { d1:'#03224c', d2:'#0a6eaa', br:'#2CA6DF', ca:'#b3d9f0', tx:'#0c2340', ft:'#eef6fc', fc:'#5b8fa8', fb:'#d0e9f5' },
    mtb:    { d1:'#3d1a08', d2:'#B8541E', br:'#E08A3C', ca:'#f5d9c0', tx:'#2a1005', ft:'#fdf3ec', fc:'#7a4020', fb:'#f0cba8' },
    walks:  { d1:'#142b18', d2:'#2F5D3A', br:'#6BA15B', ca:'#c8e0c0', tx:'#142b18', ft:'#f0f7ee', fc:'#3a6040', fb:'#b0d4a8' },
    ski:    { d1:'#0d2238', d2:'#2E6B8A', br:'#7FB8D8', ca:'#bcd8ec', tx:'#0d2238', ft:'#edf5fb', fc:'#2E6B8A', fb:'#a8cce0' },
    pets:   { d1:'#4a2800', d2:'#C2773A', br:'#E0A86B', ca:'#f5dfc0', tx:'#3a1f00', ft:'#fdf5ec', fc:'#8a5020', fb:'#f0cfa0' },
    golf:   { d1:'#0a2e18', d2:'#1F6B3A', br:'#62B36C', ca:'#c0dcc5', tx:'#0a2e18', ft:'#eef7f0', fc:'#1F6B3A', fb:'#a8d0b0' },
    yoga:   { d1:'#253d30', d2:'#5A7D6B', br:'#9DC4B0', ca:'#c8ddd5', tx:'#253d30', ft:'#f0f6f3', fc:'#5A7D6B', fb:'#b0ccc0' },
    lgbtq:  { d1:'#5a0a3f', d2:'#B81C8C', br:'#E84BC0', ca:'#f0b8e0', tx:'#3a0828', ft:'#fdf0f8', fc:'#B81C8C', fb:'#e8a0d0' },
    scuba:  { d1:'#03243a', d2:'#0B5E78', br:'#2FA8C8', ca:'#b0d8e8', tx:'#03243a', ft:'#eaf6fb', fc:'#0B5E78', fb:'#98c8dc' },
    clubs:  { d1:'#0d1e40', d2:'#1B3A6B', br:'#4C7AC0', ca:'#bccce8', tx:'#0d1e40', ft:'#eef2fb', fc:'#1B3A6B', fb:'#a8bcd8' },
    brands: { d1:'#3a2e00', d2:'#9A7B12', br:'#C9A227', ca:'#ecddb0', tx:'#2a2000', ft:'#faf6e8', fc:'#7a6010', fb:'#e0cc90' },
    widget: { d1:'#052e1a', d2:'#0F6B3F', br:'#2FB06A', ca:'#b8dcc8', tx:'#052e1a', ft:'#edf7f2', fc:'#0F6B3F', fb:'#a0ccb4' }
  };

  function loadSurf(rt) {
    try {
      fetch(CONFIG_URL + '?key=' + encodeURIComponent(KEY))
        .then(function(r){ return r.json(); })
        .then(function(cfg) {
          if (!cfg || !cfg.vertical) return;
          var v = cfg.vertical;
          var th = WIDGET_THEMES[v];
          // Apply vertical colour theme to shadow DOM (skip generic 'widget' — uses base CSS default look)
          if (th && v !== 'widget') {
            var vStyle = rt.getElementById('v-css-override');
            if (!vStyle) {
              vStyle = document.createElement('style');
              vStyle.id = 'v-css-override';
              vStyle.textContent =
                '.hd{background:linear-gradient(160deg,'+th.d1+' 0%,'+th.d2+' 100%)!important;box-shadow:0 4px 24px rgba(0,0,0,.28)!important}' +
                '.fab{background:linear-gradient(135deg,'+th.d1+' 0%,'+th.d2+' 100%)!important;box-shadow:0 10px 30px -8px rgba(0,0,0,.4)!important}' +
                '.hd h4{color:#ffffff!important;font-size:17px!important;font-weight:700!important}' +
                '.hd p{color:rgba(255,255,255,.82)!important}' +
                '.card{border-color:'+th.ca+'!important}' +
                'label{color:'+th.d2+'!important;font-weight:700!important;letter-spacing:.16em!important}' +
                'input,select{color:'+th.tx+'!important;border-color:'+th.ca+'!important;background:#fafaf8!important}' +
                'input:focus,select:focus{border-color:'+th.br+'!important;box-shadow:0 0 0 3px rgba(128,128,128,.15)!important;background:#fff!important}' +
                '.btn{background:linear-gradient(135deg,'+th.br+','+th.d2+')!important;color:#ffffff!important;font-weight:700!important;box-shadow:0 4px 18px -4px rgba(0,0,0,.3)!important}' +
                '.btn:hover{filter:brightness(1.08)!important}' +
                '.ft{background:'+th.ft+'!important;color:'+th.fc+'!important;border-top:1px solid '+th.fb+'!important}' +
                '.brand span{color:rgba(255,255,255,.92)!important}' +
                '.x{background:rgba(255,255,255,.18)!important}' +
                '.x:hover{background:rgba(255,255,255,.32)!important}';
              rt.appendChild(vStyle);
            }
          }
          // Surf-only: replace destination input with region + spot dropdowns
          if (v !== 'surf') return;
          var destEl = rt.getElementById('impt-dest');
          if (!destEl) return;
          var wrap = destEl.parentNode;
          wrap.innerHTML =
            '<label>Region</label>'+
            '<select id="impt-region" style="margin-bottom:8px">'+
              '<option value="">All regions</option>'+
              '<option value="Asia">Asia</option>'+
              '<option value="Europe">Europe</option>'+
              '<option value="Americas">Americas</option>'+
              '<option value="Africa">Africa</option>'+
              '<option value="Pacific">Pacific</option>'+
            '</select>'+
            '<label>Surf Spot</label>'+
            '<select id="impt-dest">'+buildSurfOpts('')+'</select>';
          var h4 = rt.querySelector('.hd h4');
          if (h4) h4.textContent = 'Find hotels near surf spots';
          var hdp = rt.querySelector('.hd p');
          if (hdp) hdp.textContent = '161 surf destinations · 5% back · 1t CO₂ offset';
          var btn = rt.getElementById('impt-go');
          if (btn) btn.textContent = 'Find surf hotels →';
          var ft = rt.querySelector('.ft');
          if (ft) ft.textContent = 'Powered by IMPT — 161 surf destinations worldwide';
          rt.getElementById('impt-region').addEventListener('change', function() {
            rt.getElementById('impt-dest').innerHTML = buildSurfOpts(this.value);
          });
        })
        .catch(function(){});
    } catch(e) {}
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
      loadSurf(rt);
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
      loadSurf(rt2);
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
