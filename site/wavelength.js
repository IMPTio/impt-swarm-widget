/*! IMPT Wavelength — search by signal, not by city. v1.0 (2026-06-12)
 *  Channel adapter № 37 for the IMPT Swarm.
 *  Embed:  <script src="https://swarm.impt.io/wavelength.js" data-key="YOUR_KEY" data-tune="auto" async></script>
 *          <div id="impt-wavelength"></div>
 *  data-tune: auto | mtb | neutral   (surf/walks/yoga land with the vertical rollout)
 *  data-demo="1": beacons log to console, nothing POSTs.
 *  Complements widget.js (classic, destination-known). Never replaces it.
 */
(function () {
  "use strict";
  if (window.__imptWavelength) return; window.__imptWavelength = 1;

  var BASE = "https://swarm.impt.io";
  var script = document.currentScript || (function () { var s = document.querySelectorAll('script[src*="wavelength"]'); return s[s.length - 1]; })();
  var KEY = (script && script.getAttribute("data-key")) || "wl_anon";
  var TUNE = ((script && script.getAttribute("data-tune")) || "auto").toLowerCase();
  var DEMO = !!(script && script.getAttribute("data-demo"));
  var PRESET = (script && script.getAttribute("data-signal")) || (window.__wlSignal || null);

  /* ---------- datasets: one index per world ---------- */
  var DATASETS = { mtb: "/wavelength/data/mtb.json", surf: "/wavelength/data/surf.json", walks: "/wavelength/data/walks.json" };

  /* ---------- auto-tune: sniff the host page ---------- */
  function sniffTune() {
    var txt = (document.title + " " + (function () { var m = document.querySelector('meta[name="description"]'); return m ? m.content : ""; })() + " " +
      Array.prototype.slice.call(document.querySelectorAll("h1,h2"), 0, 12).map(function (h) { return h.textContent; }).join(" ")).toLowerCase();
    if (/mountain.?bik|mtb|enduro|downhill|trail|singletrack|bike.?park/.test(txt)) return "mtb";
    if (/surf|swell|lineup|reef|break/.test(txt)) return "surf";
    if (/hik|walk|trek|camino|rambl/.test(txt)) return "walks";
    return "neutral";
  }
  var tune = TUNE === "auto" ? sniffTune() : TUNE;
  var FALLBACK = false;

  /* ---------- per-world sentence + copy ---------- */
  var WORLDS = {
    mtb: {
      emoji: "🚵", modeLabel: "MTB MODE", verb: "Ride",
      vibe: [
        { t: "lift-laps all day", boost: ["bike_park", "lift_served", "jump_lines"], d: { a: 80, w: 55 } },
        { t: "big-mountain epics", boost: ["big_mountain", "singletrack_epic", "remote"], avoid: ["jump_lines"], d: { a: 75, w: 88 } },
        { t: "flow & jumps", boost: ["flow_trails", "jump_lines", "bike_park"], d: { a: 72, w: 50 } },
        { t: "tech & gnar", boost: ["tech_gnar", "natural_trails"], d: { a: 90, w: 72 } },
        { t: "easy forest miles", boost: ["beginner_friendly", "family_friendly", "forest"], avoid: ["tech_gnar", "big_mountain", "jump_lines"], d: { a: 28, w: 55 } }
      ],
      who: [
        { t: "with the crew", boost: ["nightlife", "bike_park"] },
        { t: "with my dog", need: "dog_friendly" },
        { t: "with the kids", need: "family_friendly", boost: ["beginner_friendly", "pump_track"] },
        { t: "just the two of us", boost: ["village_charm", "luxury"] },
        { t: "flying solo", boost: [] }
      ]
    },
    surf: {
      emoji: "🏄", modeLabel: "SURF MODE", verb: "Surf",
      vibe: [
        { t: "chasing barrels", boost: ["barrel"], avoid: ["beginner_friendly", "surf_school"], d: { a: 88, w: 50 } },
        { t: "mellow longboard days", boost: ["beginner_friendly", "surf_school", "family_friendly"], d: { a: 30, w: 35 } },
        { t: "empty cold-water lineups", boost: ["cold_water", "crowd_free", "remote"], d: { a: 60, w: 75 } },
        { t: "warm water all winter", boost: ["warm_water", "winter_season", "year_round"], d: { a: 55, w: 45 } },
        { t: "surf-town buzz", boost: ["surf_town", "nightlife"], d: { a: 55, w: 25 } }
      ],
      who: [
        { t: "with the crew", boost: ["nightlife", "surf_town"] },
        { t: "with my dog", need: "dog_friendly" },
        { t: "with the kids", need: "family_friendly", boost: ["beginner_friendly", "surf_school"] },
        { t: "just the two of us", boost: ["village_charm", "luxury"] },
        { t: "flying solo", boost: ["surf_school"] }
      ]
    },
    walks: {
      emoji: "🥾", modeLabel: "WALKS MODE", verb: "Walk",
      vibe: [
        { t: "a long-distance epic", boost: ["long_distance", "challenging"], d: { a: 70, w: 75 } },
        { t: "village-to-village rambles", boost: ["village_to_village", "day_walks", "gastro"], d: { a: 35, w: 50 } },
        { t: "coastal cliff paths", boost: ["coastal_path"], d: { a: 45, w: 60 } },
        { t: "pilgrim miles", boost: ["pilgrimage"], bonus: ["long_distance"], d: { a: 40, w: 55 } },
        { t: "easy forest wanders", boost: ["forest", "beginner_friendly", "family_friendly"], avoid: ["long_distance", "challenging"], d: { a: 20, w: 55 } }
      ],
      who: [
        { t: "with the crew", boost: ["village_to_village", "gastro"] },
        { t: "with my dog", need: "dog_friendly" },
        { t: "with the kids", need: "family_friendly", boost: ["beginner_friendly", "day_walks"] },
        { t: "just the two of us", boost: ["village_charm", "luxury", "gastro"] },
        { t: "flying solo", boost: ["pilgrimage", "long_distance"] }
      ]
    },
    neutral: {
      emoji: "🌊", modeLabel: "NEUTRAL", verb: "Wake me up",
      vibe: [], who: []
    }
  };

  /* per-world hub links (mtb has per-resort guide pages; others link the hub) */
  var HUBS = { mtb: "https://impt.io/mountain-bike-trails/", surf: "https://impt.io/surf-hotels/", walks: "https://impt.io/walks" };

  var BUDGETS = [
    { t: "under €80", cap: 80, bands: { 1: 1, 2: 0.72, 3: 0.38 }, d: { l: 12 } },
    { t: "under €150", cap: 150, bands: { 1: 1, 2: 1, 3: 0.68 }, d: { l: 35 } },
    { t: "under €300", cap: 300, bands: { 1: 0.96, 2: 1, 3: 1 }, d: { l: 65 } },
    { t: "whatever it costs", cap: 9999, bands: { 1: 0.85, 2: 0.95, 3: 1 }, d: { l: 92 } }
  ];
  var WHENS = [
    { t: "this weekend", off: 0, d: { p: 78 } },
    { t: "next month", off: 1, d: { p: 35 } },
    { t: "in a few months", off: 3, d: { p: 18 } },
    { t: "someday soon", off: null, d: { p: 12 } }
  ];

  /* ---------- state ---------- */
  var S = { a: 60, w: 60, l: 35, p: 55, vibe: 0, who: 0, budget: 1, when: 0 };
  var RESORTS = [];
  var played = false;

  /* ---------- signal codec: a72.w65.l30.p50.v1.h0.b150.t0.mtb ---------- */
  function sigEncode() {
    return "a" + S.a + ".w" + S.w + ".l" + S.l + ".p" + S.p + ".v" + S.vibe + ".h" + S.who + ".b" + BUDGETS[S.budget].cap + ".t" + S.when + "." + tune;
  }
  function sigDecode(str) {
    try {
      str.split(".").forEach(function (part) {
        var m;
        if ((m = part.match(/^a(\d+)$/))) S.a = clamp(+m[1]);
        else if ((m = part.match(/^w(\d+)$/))) S.w = clamp(+m[1]);
        else if ((m = part.match(/^l(\d+)$/))) S.l = clamp(+m[1]);
        else if ((m = part.match(/^p(\d+)$/))) S.p = clamp(+m[1]);
        else if ((m = part.match(/^v(\d+)$/))) S.vibe = +m[1];
        else if ((m = part.match(/^h(\d+)$/))) S.who = +m[1];
        else if ((m = part.match(/^b(\d+)$/))) { var c = +m[1]; S.budget = BUDGETS.findIndex(function (b) { return b.cap === c; }); if (S.budget < 0) S.budget = 1; }
        else if ((m = part.match(/^t(\d+)$/))) S.when = Math.min(+m[1], WHENS.length - 1);
        else if (DATASETS[part]) tune = part;
      });
    } catch (e) { }
  }
  function clamp(x) { return Math.max(0, Math.min(100, x | 0)); }

  /* ---------- beacons ---------- */
  function beacon(evt, dest) {
    if (DEMO) { console.log("[wavelength beacon]", { key: KEY, evt: evt, dest: dest || sigEncode() }); return; }
    try { new Image().src = BASE + "/api/widget/track?key=" + encodeURIComponent(KEY) + "&evt=" + evt + "&dest=" + encodeURIComponent((dest || sigEncode()).slice(0, 120)); } catch (e) { }
  }

  /* ---------- scoring: the analysis layer ---------- */
  var W = WORLDS[tune] || WORLDS.neutral;
  function monthTarget() {
    var off = WHENS[S.when].off;
    if (off === null) return null;
    var d = new Date(); d.setMonth(d.getMonth() + off);
    return d.getMonth() + 1;
  }
  function score(r) {
    var reasons = [], penal = [];
    // axes proximity (weighted; adrenaline matters most to riders)
    var diff = (Math.abs(r.axes.adrenaline - S.a) * 1.2 + Math.abs(r.axes.wild - S.w) * 1.0 +
      Math.abs(r.axes.splurge - S.l) * 0.8 + Math.abs(r.axes.spontaneous - S.p) * 0.6) / 3.6;
    var m = Math.max(5, 97 - diff * 1.15);

    // vibe slot: tag boosts
    var vibe = W.vibe[S.vibe];
    if (vibe && vibe.boost) {
      var hits = vibe.boost.filter(function (t) { return r.tags.indexOf(t) >= 0; });
      if (hits.length) {
        m += 6 + hits.length * 3; reasons.push(tagLabel(hits[0]));
        if (vibe.bonus) vibe.bonus.forEach(function (t) { if (r.tags.indexOf(t) >= 0) m += 5; });
      }
      else { m *= 0.82; } // the chosen vibe found nothing here — be honest about it
      var av = vibe.avoid ? vibe.avoid.filter(function (t) { return r.tags.indexOf(t) >= 0; }).length : 0;
      if (av) { m *= Math.pow(0.82, av); if (!hits.length) penal.push("different style"); }
    }
    // who slot: hard needs + soft boosts
    var who = W.who[S.who];
    if (who) {
      if (who.need) {
        if (r.tags.indexOf(who.need) >= 0) { m += 4; reasons.push(tagLabel(who.need)); }
        else { m *= 0.45; penal.push("not " + tagLabel(who.need).toLowerCase()); }
      }
      if (who.boost) who.boost.forEach(function (t) { if (r.tags.indexOf(t) >= 0) m += 1.5; });
    }
    // budget: band multiplier
    var bm = BUDGETS[S.budget].bands[r.budget_band] || 1;
    m *= bm;
    if (bm === 1 && r.budget_band === 1 && S.budget <= 1) reasons.push("€ budget-friendly");
    if (bm < 0.7) penal.push("over budget");
    // season
    var mt = monthTarget();
    if (mt !== null) {
      if (r.months.indexOf(mt) >= 0) { m += 3; reasons.push("in season (" + monthName(mt) + ")"); }
      else { m *= 0.30; penal.push("off-season (" + monthName(mt) + ")"); }
    }
    if (m > 88) m = 88 + (m - 88) * 0.45;   // soft-compress the top so leaders differentiate
    m = Math.max(3, Math.min(99, m));
    return { m: m, reasons: reasons.slice(0, 3), penal: penal.slice(0, 2) };
  }
  var TAG_LABELS = {
    bike_park: "Lift-served bike park", lift_served: "Lift-served", uplift_shuttle: "Shuttle uplift",
    natural_trails: "Natural trails", flow_trails: "Flow trails", tech_gnar: "Proper tech",
    jump_lines: "Jump lines", ebike_friendly: "E-bike friendly", family_friendly: "Family-friendly",
    beginner_friendly: "Beginner-friendly", dog_friendly: "Dog-friendly", nightlife: "Real nightlife",
    village_charm: "Village charm", big_mountain: "Big-mountain", desert: "Desert riding",
    forest: "Forest", coastal: "Coastal", year_round: "Rides year-round", summer_only: "Summer season",
    budget_gem: "Budget gem", luxury: "Luxury stays", remote: "Remote", near_city: "Near a city",
    pump_track: "Pump track", race_venue: "Race venue", singletrack_epic: "Singletrack epics", barrel: "Proper barrels", warm_water: "Warm water"
  };
  function tagLabel(t) { return TAG_LABELS[t] || t.replace(/_/g, " "); }
  function monthName(m) { return ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m]; }

  function routeWorlds() {
    var r = [];
    if (tune === "mtb") r.push("MTB");
    if (S.w > 70) r.push("GREEN"); if (S.w < 25) r.push("CITY");
    if (S.l < 30) r.push("CHEAP"); if (S.l > 75) r.push("LUXE");
    if (S.p > 78) r.push("TONIGHT");
    var who = W.who[S.who]; if (who && who.need === "dog_friendly") r.push("PETS");
    if (!r.length) r.push("EVERY WORLD");
    return r.slice(0, 4).join(" / ");
  }
  function band3(x, lo, hi) { return x < 33 ? lo : (x > 66 ? hi : "mid"); }

  /* ---------- urls ---------- */
  function bookURL(r) {
    // attribution-safe: /api/widget/r sets the .impt.io partner cookie then 302s to app.impt.io
    return BASE + "/api/widget/r?key=" + encodeURIComponent(KEY) + "&dest=" + encodeURIComponent(r.city) + "&med=wavelength";
  }
  function guideURL(r) {
    if (tune === "mtb") return "https://impt.io/mountain-bike-trails/" + r.country + "/" + r.slug + "/";
    return HUBS[tune] || "https://impt.io/worlds";
  }
  function shareURL() { return BASE + "/wl?k=" + encodeURIComponent(KEY) + "&s=" + sigEncode(); }

  /* ---------- UI (shadow DOM, scoped) ---------- */
  var mount = document.getElementById("impt-wavelength");
  if (!mount) { mount = document.createElement("div"); mount.id = "impt-wavelength"; (script && script.parentNode ? script.parentNode : document.body).insertBefore(mount, script ? script.nextSibling : null); }
  var root = mount.attachShadow ? mount.attachShadow({ mode: "open" }) : mount;

  var css = '\
:host{all:initial}*{box-sizing:border-box;font-family:Inter,-apple-system,Segoe UI,Arial,sans-serif}\
.wl{background:#fff;border:1px solid #e7e1d4;border-radius:20px;padding:22px 22px 18px;color:#14302a;box-shadow:0 10px 36px rgba(20,48,42,.07);max-width:1060px}\
.hd{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}\
.brand{font-weight:800;font-size:15px}.brand b{color:#0f6b3f}\
.mode{font-size:10.5px;font-weight:800;letter-spacing:.09em;color:#a8861a;background:#fbf6e6;border:1px solid #eee0b4;border-radius:999px;padding:5px 12px}\
.sentence{font-size:clamp(18px,3vw,26px);line-height:1.5;font-weight:600;margin:4px 0 4px}\
.slot{display:inline-block;color:#a8861a;border-bottom:2.5px dashed #c9a227;cursor:pointer;padding:0 3px;border-radius:5px;user-select:none}\
.slot:hover{background:#fbf6e6}.slot.pop{animation:pop .3s}@keyframes pop{40%{transform:scale(1.12)}}\
.hint{font-size:11.5px;color:#7a857e;margin:2px 0 14px}\
.dials{display:grid;grid-template-columns:1fr 210px;gap:22px;align-items:center;margin:4px 0}\
.dial{margin:9px 0}.ends{display:flex;justify-content:space-between;font-size:10.5px;font-weight:800;letter-spacing:.05em;color:#7a857e}.ends .live{color:#0f6b3f}\
input[type=range]{width:100%;-webkit-appearance:none;appearance:none;height:5px;border-radius:3px;background:#dfe8df;outline:none;margin:7px 0 0}\
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:21px;height:21px;border-radius:50%;background:#0f6b3f;border:3px solid #fff;box-shadow:0 1px 6px rgba(20,48,42,.35);cursor:grab}\
input[type=range]::-moz-range-thumb{width:17px;height:17px;border-radius:50%;background:#0f6b3f;border:3px solid #fff;cursor:grab}\
.wavebox{background:#0e2c25;border-radius:14px;padding:12px;display:flex;flex-direction:column;gap:5px}\
.wavebox svg{width:100%;height:84px}.cap{color:#9ec7ae;font-size:10px;font-weight:800;letter-spacing:.14em;text-align:center}\
.read{background:#0e2c25;color:#eaf4ec;border-radius:12px;padding:11px 15px;font-family:Menlo,Consolas,monospace;font-size:11.5px;margin:12px 0 6px;line-height:1.7;overflow-x:auto;white-space:nowrap}\
.read .k{color:#9ec7ae}.read .gold{color:#e7c75f}.read .route{color:#7cc24a;font-weight:700}\
.sigrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 2px}\
.copy{border:1px solid #0f6b3f;color:#0f6b3f;background:#fff;border-radius:999px;font-weight:700;font-size:12px;padding:6px 14px;cursor:pointer}\
.copy:active{background:#0f6b3f;color:#fff}\
h2{font-size:15px;margin:20px 0 10px;font-weight:800}h2 span{color:#7a857e;font-weight:500;font-size:12px}\
.results{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}\
.card{background:#fff;border:1px solid #e7e1d4;border-radius:14px;padding:14px 16px;position:relative;transition:box-shadow .3s}\
.card.top{border-color:#c9a227;box-shadow:0 8px 26px rgba(201,162,39,.18)}\
.nm{font-weight:800;font-size:15px}.nm a{color:inherit;text-decoration:none}.nm a:hover{text-decoration:underline}\
.pl{color:#7a857e;font-size:12px;margin:2px 0 8px}\
.mrow{display:flex;justify-content:space-between;align-items:baseline;font-size:12px}.pct{font-weight:800;color:#0f6b3f;font-size:15px}\
.pr{font-weight:800;color:#46554e}\
.matchbar{height:6px;background:#efece0;border-radius:4px;overflow:hidden;margin:4px 0 7px}\
.matchbar i{display:block;height:100%;background:linear-gradient(90deg,#1f7a4d,#7cc24a);border-radius:4px;transition:width .5s cubic-bezier(.2,.8,.2,1)}\
.why{font-size:12px;color:#46554e;line-height:1.5;margin:0 0 7px}\
.chips{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 9px}\
.tg{font-size:10px;font-weight:700;background:#eef3ee;color:#2c5a45;border-radius:6px;padding:3px 7px}\
.tg.warn{background:#faf0e0;color:#9a6a12}\
.row2{display:flex;gap:8px;align-items:center}\
.book{display:inline-block;background:#0f6b3f;color:#fff;font-weight:800;font-size:12.5px;border-radius:999px;padding:8px 18px;text-decoration:none}\
.guide{font-size:12px;color:#0f6b3f;font-weight:700;text-decoration:none}.guide:hover{text-decoration:underline}\
.more{margin:14px auto 0;display:block;border:1px solid #e7e1d4;background:#fff;color:#14302a;border-radius:999px;font-weight:700;font-size:12.5px;padding:8px 20px;cursor:pointer}\
.cascade{display:flex;flex-wrap:wrap;border:1px solid #e7e1d4;border-radius:12px;overflow:hidden;margin:18px 0 0;background:#fff}\
.cas{flex:1;min-width:104px;text-align:center;padding:11px 6px;border-right:1px solid #e7e1d4}.cas:last-child{border-right:0}\
.cas .v{font-weight:800;color:#0f6b3f;font-size:14px}.cas .l{font-size:10px;color:#7a857e;margin-top:2px}\
.classic{font-size:12px;color:#7a857e;text-align:center;margin:12px 0 0}.classic a{color:#0f6b3f;font-weight:700}\
@media(max-width:680px){.dials{grid-template-columns:1fr}.wl{padding:16px 14px 14px}.read{white-space:normal}}';

  var html = '<div class="wl">\
<div class="hd"><div class="brand">impt<b>/Hotels</b> · Wavelength</div><div class="mode" id="mode"></div></div>\
<div class="sentence" id="sentence"></div>\
<p class="hint">↑ tap any gold phrase to change it — the sentence IS the query</p>\
<div class="dials"><div>\
<div class="dial"><div class="ends"><span>STILLNESS</span><span class="live" id="v_a"></span><span>ADRENALINE</span></div><input type="range" id="d_a" min="0" max="100"></div>\
<div class="dial"><div class="ends"><span>URBAN</span><span class="live" id="v_w"></span><span>WILD</span></div><input type="range" id="d_w" min="0" max="100"></div>\
<div class="dial"><div class="ends"><span>SMART-SPEND</span><span class="live" id="v_l"></span><span>SPLURGE</span></div><input type="range" id="d_l" min="0" max="100"></div>\
<div class="dial"><div class="ends"><span>PLANNED</span><span class="live" id="v_p"></span><span>SPONTANEOUS</span></div><input type="range" id="d_p" min="0" max="100"></div>\
</div><div class="wavebox"><svg viewBox="0 0 220 84" preserveAspectRatio="none"><path id="wave" fill="none" stroke="#7cc24a" stroke-width="2.5" stroke-linecap="round"/></svg><div class="cap">YOUR WAVELENGTH</div></div></div>\
<div class="read" id="read"></div>\
<div class="sigrow"><button class="copy" id="copy">Copy signal link</button><button class="copy" id="wa">WhatsApp</button><button class="copy" id="tg">Telegram</button></div>\
<h2 id="rhead"></h2>\
<div class="results" id="results"></div>\
<button class="more" id="more" style="display:none">Show more resorts ↓</button>\
<div class="cascade">\
<div class="cas"><div class="v">5%</div><div class="l">to the site that sent you</div></div>\
<div class="cas"><div class="v">€5</div><div class="l">guest credit</div></div>\
<div class="cas"><div class="v">3%</div><div class="l">to a cause</div></div>\
<div class="cas"><div class="v">2%</div><div class="l">next-stay back</div></div>\
<div class="cas"><div class="v">1t CO₂</div><div class="l">retired per night ✓</div></div></div>\
<div class="classic">Know exactly where you\'re going? <a id="classiclink" href="#">Use the classic search →</a></div>\
</div>';

  var st = document.createElement("style"); st.textContent = css; root.appendChild(st);
  var box = document.createElement("div"); box.innerHTML = html; root.appendChild(box);
  function $(id) { return root.getElementById ? root.getElementById(id) : box.querySelector("#" + id); }
  function $all(sel) { return box.querySelectorAll(sel); }

  /* ---------- render ---------- */
  var SHOW_N = 9, showAll = false;
  function slotHTML() {
    var vibe = W.vibe[S.vibe] || { t: "anywhere good" };
    var who = W.who[S.who] || { t: "with anyone" };
    return W.verb + ' <span class="slot" data-s="vibe">' + vibe.t + '</span>, <span class="slot" data-s="who">' + who.t +
      '</span>, <span class="slot" data-s="budget">' + BUDGETS[S.budget].t + '</span> a night — <span class="slot" data-s="when">' + WHENS[S.when].t + '</span>.';
  }
  function drawWave() {
    var vals = [S.a, S.w, S.l, S.p], pts = [], N = 44;
    for (var i = 0; i <= N; i++) {
      var x = i / N * 220, y = 42;
      for (var k = 0; k < 4; k++) { var amp = (vals[k] - 50) / 50 * 23; y += Math.sin((i / N) * Math.PI * (k + 1.5) + k * 1.3) * amp / (k * 0.6 + 1); }
      pts.push((i ? "L" : "M") + x.toFixed(1) + "," + Math.max(5, Math.min(79, y)).toFixed(1));
    }
    $("wave").setAttribute("d", pts.join(" "));
  }
  function render() {
    $("mode").textContent = FALLBACK ? "MTB MODE · first world live — more soon" : ((TUNE === "auto" ? "AUTO-TUNED · " : "") + (W.modeLabel || tune.toUpperCase()));
    $("sentence").innerHTML = slotHTML();
    $all(".slot").forEach(function (el) {
      el.addEventListener("click", function () {
        var s = el.getAttribute("data-s");
        var arr = s === "budget" ? BUDGETS : (s === "when" ? WHENS : W[s === "vibe" ? "vibe" : "who"]);
        if (!arr || !arr.length) return;
        S[s] = (S[s] + 1) % arr.length;
        var d = (arr[S[s]] && arr[S[s]].d) || {}; Object.keys(d).forEach(function (k) { S[k] = d[k]; });
        play(); render();
      });
    });
    ["a", "w", "l", "p"].forEach(function (k) { $("d_" + k).value = S[k]; $("v_" + k).textContent = S[k]; });
    drawWave();
    $("read").innerHTML = '<span class="k">SIGNAL READ →</span> <span class="gold">' +
      band3(S.a, "low-key", "high-adrenaline") + " · " + band3(S.w, "urban", "wild") + " · " +
      band3(S.l, "smart-spend", "splurge") + " · " + band3(S.p, "planned", "spontaneous") +
      '</span> — <span class="k">ROUTING TO:</span> <span class="route">' + routeWorlds() + "</span>";

    if (!RESORTS.length) { $("rhead").innerHTML = 'Tuning… <span>loading the resort signal index</span>'; return; }
    var ranked = RESORTS.map(function (r) { var s = score(r); return { r: r, m: s.m, disp: Math.round(s.m), reasons: s.reasons, penal: s.penal }; })
      .sort(function (x, y) { return y.m - x.m; });
    var top = showAll ? ranked : ranked.slice(0, SHOW_N);
    $("rhead").innerHTML = "On your wavelength <span>— " + RESORTS.length + " resorts analysed, ranked live</span>";
    var out = $("results"); out.innerHTML = "";
    var EURO = { 1: "€", 2: "€€", 3: "€€€" };
    top.forEach(function (x, i) {
      var d = document.createElement("div"); d.className = "card" + (i === 0 ? " top" : "");
      var chips = x.reasons.map(function (t) { return '<span class="tg">' + t + "</span>"; }).join("") +
        x.penal.map(function (t) { return '<span class="tg warn">' + t + "</span>"; }).join("");
      d.innerHTML = '<div class="nm">' + (i === 0 ? "⭐ " : "") + '<a href="' + guideURL(x.r) + '" target="_blank" rel="noopener">' + esc(x.r.name) + "</a></div>" +
        '<div class="pl">' + esc(x.r.cname) + " · " + esc(x.r.hook) + "</div>" +
        '<div class="mrow"><span class="pct">' + x.disp + '% match</span><span class="pr">' + EURO[x.r.budget_band] + " stays</span></div>" +
        '<div class="matchbar"><i style="width:0%"></i></div>' +
        '<div class="why">' + esc(x.r.why) + "</div>" +
        '<div class="chips">' + chips + "</div>" +
        '<div class="row2"><a class="book" href="' + bookURL(x.r) + '" target="_blank" rel="noopener" data-slug="' + x.r.slug + '">Book a stay →</a>' +
        '<a class="guide" href="' + guideURL(x.r) + '" target="_blank" rel="noopener">' + ({ mtb: "Trail guide", surf: "Surf guide", walks: "Route guide" }[tune] || "Guide") + '</a></div>';
      out.appendChild(d);
      requestAnimationFrame(function () { requestAnimationFrame(function () { d.querySelector(".matchbar i").style.width = x.disp + "%"; }); });
    });
    $("more").style.display = (!showAll && ranked.length > SHOW_N) ? "block" : "none";
    $all(".book").forEach(function (a) { a.addEventListener("click", function () { beacon("wl_book", a.getAttribute("data-slug")); }); });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[<>&"]/g, function (c) { return { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]; }); }
  function play() { if (!played) { played = true; beacon("wl_play"); } }

  /* ---------- static interactions ---------- */
  ["a", "w", "l", "p"].forEach(function (k) {
    $("d_" + k).addEventListener("input", function () { S[k] = +this.value; render(); });
    $("d_" + k).addEventListener("change", play);
  });
  $("more").addEventListener("click", function () { showAll = true; render(); });
  $("copy").addEventListener("click", function () {
    try { navigator.clipboard.writeText(shareURL()); } catch (e) { }
    this.textContent = "Copied ✓"; var me = this; setTimeout(function () { me.textContent = "Copy signal link"; }, 1400);
    beacon("wl_share", "copy");
  });
  $("wa").addEventListener("click", function () { beacon("wl_share", "wa"); window.open("https://wa.me/?text=" + encodeURIComponent("My travel wavelength 🌊 " + shareURL()), "_blank"); });
  $("tg").addEventListener("click", function () { beacon("wl_share", "tg"); window.open("https://t.me/share/url?url=" + encodeURIComponent(shareURL()) + "&text=" + encodeURIComponent("My travel wavelength 🌊"), "_blank"); });
  $("classiclink").href = BASE + "/api/widget/r?key=" + encodeURIComponent(KEY) + "&med=wavelength-classic";

  /* ---------- boot ---------- */
  if (PRESET) sigDecode(PRESET);
  W = WORLDS[tune] || WORLDS.neutral;   // signal string may carry a tune — recompute world
  if (W.vibe.length) S.vibe = S.vibe % W.vibe.length; else S.vibe = 0;
  if (W.who.length) S.who = S.who % W.who.length; else S.who = 0;
  var dataPath = DATASETS[tune];
  if (!dataPath) {
    // world not tuned yet → boot MTB (only live index) but say so honestly
    tune = "mtb"; W = WORLDS.mtb; dataPath = DATASETS.mtb; FALLBACK = true;
  }
  render();
  beacon("wl_open", tune);
  fetch(BASE + dataPath).then(function (r) { return r.json(); }).then(function (d) {
    RESORTS = d.resorts || d;
    render();
  }).catch(function (e) { $("rhead").innerHTML = 'Index unavailable — <span>try the <a href="' + BASE + '/api/widget/r?key=' + encodeURIComponent(KEY) + '&med=wavelength-classic">classic search</a></span>'; });
})();
