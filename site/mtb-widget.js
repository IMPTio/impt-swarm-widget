/*!
 * IMPT MTB Widget — sector widget v3 (2026-06-08)
 * A thin MTB-branded launcher partners embed. It DOES NOT recreate anything —
 * it opens the existing IMPT MTB site (impt.io/mountain-bike-trails/) carrying the
 * partner key, so the site's own guides + booking earn the partner 5% (gear 10%).
 * Embed: <script src="https://swarm.impt.io/mtb-widget.js" data-key="YOUR_KEY" async></script>
 */
(function(){
 'use strict';
 if(window.__imptMTB) return; window.__imptMTB=1;
 var SITE='https://impt.io/mountain-bike-trails/', SHOP='https://shop.impt.io', TRACK='https://swarm.impt.io/api/widget/track';
 var me=document.currentScript||document.querySelector('script[src*="mtb-widget.js"]');
 var KEY=(me&&me.getAttribute('data-key'))||'swarm-public';
 var POS=(me&&me.getAttribute('data-position'))||'auto', HOST=location.host;
 function track(evt,dest){try{new Image().src=TRACK+'?key='+encodeURIComponent(KEY)+'&evt='+encodeURIComponent(evt)+'&ref='+encodeURIComponent(HOST)+'&dest='+encodeURIComponent('mtb:'+(dest||''));}catch(e){}}
 var R='https://swarm.impt.io/api/widget/r';
 // Route through /api/widget/r so the first-party impt_partner cookie is set on .impt.io
 // (this is what makes the partner actually get credited for stays + gear).
 function siteURL(path){return R+'?key='+encodeURIComponent(KEY)+'&med=mtb-widget&to='+encodeURIComponent(SITE+(path?path+'/':''));}
 function shopURL(q){return R+'?key='+encodeURIComponent(KEY)+'&med=mtb-gear&to='+encodeURIComponent(SHOP+'/search?q='+encodeURIComponent(q));}
 var COUNTRIES=[['france','France'],['austria','Austria'],['italy','Italy'],['switzerland','Switzerland'],['canada','Canada'],['united-states','United States'],['united-kingdom','United Kingdom'],['germany','Germany'],['spain','Spain'],['portugal','Portugal'],['slovenia','Slovenia'],['new-zealand','New Zealand']];

 var host=document.createElement('div'); host.setAttribute('aria-label','IMPT MTB'); document.body.appendChild(host);
 var root=host.attachShadow?host.attachShadow({mode:'open'}):host;
 var CSS='\
 :host{all:initial}*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}\
 .wrap{position:fixed;right:20px;bottom:20px;z-index:2147483000}.wrap.left{right:auto;left:20px}.wrap.left .panel{right:auto;left:0}\
 .fab{display:inline-flex;align-items:center;gap:9px;cursor:pointer;border:0;background:linear-gradient(135deg,#1a1d1a,#2b2017);color:#fff;font-size:14px;font-weight:700;padding:13px 18px;border-radius:999px;box-shadow:0 10px 30px -8px rgba(0,0,0,.55);transition:transform .18s}\
 .fab:hover{transform:translateY(-2px)}.fab small{font-weight:500;font-size:11px;color:#C8FF7E}\
 .panel{position:absolute;right:0;bottom:0;width:340px;max-width:calc(100vw - 24px);background:#14160f;color:#eef2e6;border:1px solid #2c3326;border-radius:20px;overflow:hidden;box-shadow:0 28px 64px -16px rgba(0,0,0,.6);opacity:0;transform:translateY(12px) scale(.98);pointer-events:none;transition:opacity .2s,transform .2s}\
 .open .panel{opacity:1;transform:none;pointer-events:auto}.open .fab{display:none}\
 .hd{position:relative;padding:18px 20px;background:linear-gradient(135deg,#243017,#3a2a14);color:#fff}\
 .hd h4{margin:0;font-size:17px;font-weight:800}.hd p{margin:4px 0 0;font-size:11.5px;color:#C8FF7E;font-weight:600}\
 .x{position:absolute;top:14px;right:14px;width:28px;height:28px;border:0;border-radius:50%;cursor:pointer;background:rgba(255,255,255,.14);color:#fff;font-size:16px;display:flex;align-items:center;justify-content:center}\
 .bd{padding:16px}\
 .cta{display:block;text-align:center;text-decoration:none;background:#C8FF7E;color:#14160f;font-weight:800;font-size:15px;padding:13px;border-radius:12px;margin-bottom:12px}\
 .lbl{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:#9fb08c;font-weight:700;margin:6px 0}\
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}\
 .c{display:block;text-decoration:none;background:#1d211a;border:1px solid #2c3326;border-radius:10px;padding:9px 11px;color:#eef2e6;font-size:12.5px;font-weight:600}\
 .c:hover{border-color:#C8FF7E}\
 .gear{display:block;text-align:center;text-decoration:none;margin-top:12px;background:#20251a;border:1px solid #2c3326;color:#C8FF7E;font-weight:700;font-size:13px;padding:11px;border-radius:11px}\
 .gear:hover{border-color:#C8FF7E}\
 .ft{padding:10px 16px;background:#0e100a;font-size:10.5px;color:#7e8c6e;text-align:center}\
 @media(max-width:480px){.panel{width:calc(100vw - 24px)}.wrap{right:12px;bottom:12px}.wrap.left{right:auto;left:12px}}';
 root.innerHTML='<style>'+CSS+'</style><div class="wrap" id="w">'+
   '<button class="fab" id="fab"><span style="font-size:18px">🚵</span><span>MTB trips &amp; gear<br><small>5% on stays · 10% on gear</small></span></button>'+
   '<div class="panel" role="dialog"><div class="hd"><h4>🚵 Ride. Stay. Earn.</h4><p>117 bike-resort guides — book a stay, earn 5% (gear 10%)</p><button class="x" id="x">&times;</button></div>'+
   '<div class="bd">'+
     '<a class="cta" id="all" href="'+siteURL('')+'" target="_blank" rel="noopener">Explore 117 MTB destinations →</a>'+
     '<div class="lbl">Browse by country</div>'+
     '<div class="grid">'+COUNTRIES.map(function(c){return '<a class="c" data-d="'+c[0]+'" href="'+siteURL(c[0])+'" target="_blank" rel="noopener">'+c[1]+'</a>';}).join('')+'</div>'+
     '<a class="gear" id="gear" href="'+shopURL('mountain bike')+'" target="_blank" rel="noopener">🛒 Shop MTB gear — 10% back</a>'+
   '</div>'+
   '<div class="ft">Powered by IMPT — mountain-bike trips &amp; gear that pay you back</div></div></div>';
 var wrap=root.getElementById('w');
 root.getElementById('fab').addEventListener('click',function(){wrap.classList.add('open');track('view','open');});
 root.getElementById('x').addEventListener('click',function(){wrap.classList.remove('open');});
 root.getElementById('all').addEventListener('click',function(){track('click','all');});
 root.getElementById('gear').addEventListener('click',function(){track('click','gear');});
 root.querySelectorAll('.c').forEach(function(c){c.addEventListener('click',function(){track('click','country:'+c.getAttribute('data-d'));});});
 function flip(l){wrap.classList.toggle('left',l);}
 function place(){try{if(POS==='left'){flip(true);return;}if(POS==='right'){flip(false);return;}var vw=innerWidth,vh=innerHeight,all=document.body.getElementsByTagName('*'),taken=false;for(var i=0;i<all.length;i++){var e=all[i];if(e===host||(host.contains&&host.contains(e)))continue;var s;try{s=getComputedStyle(e);}catch(_){continue;}if(s.position!=='fixed'&&s.position!=='sticky')continue;if(s.display==='none'||s.visibility==='hidden')continue;var r=e.getBoundingClientRect();if(r.width<8||r.height<8||r.width>vw*0.85)continue;if(r.left>vw*0.5&&r.right>vw-180&&r.bottom>vh*0.5){taken=true;break;}}flip(taken);}catch(e){}}
 place();[800,2000,4000].forEach(function(t){setTimeout(place,t);});addEventListener('resize',place);
 track('load','mtb');
})();
