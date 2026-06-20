"""Designed widget welcome email (hosted hero + live HTML + plain-text alt).
Self-contained builder used by swarm_widget_api.send_welcome_email so every NEW
signup gets the new designed email. Heroes hosted at swarm.impt.io/email-assets.
"""
import html as _html

HERO_BASE = "https://swarm.impt.io/email-assets"
INK="#0B0B0E"; ORANGE="#FF6B1A"; GREEN="#1f6f54"; CREAM="#F4EFE6"; MUTE="#86868B"

V = {
 "mtb":   {"sfx":"MTB","label":"MTB Network","hero":"hero-mtb.jpg",
           "subject":"Your MTB widget is ready 🚵 — earn 5% of every booking",
           "h1":"Welcome to the trailhead.",
           "join":"You just joined the IMPT mountain bike network — a small group of bike shops, schools, trail builders and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your visitors book hotels right by the trails at 117 bike resorts — and 8M hotels worldwide.",
           "script":"mtb-widget.js","signup":"impt.io/mountain-bike-trails"},
 "surf":  {"sfx":"Surf","label":"Surf Network","hero":"hero-surf.jpg",
           "subject":"Your surf widget is ready 🏄 — earn 5% of every booking",
           "h1":"Welcome to the lineup.",
           "join":"You just joined the IMPT surf network — a small group of surf shops, schools, shapers and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your visitors book the bed next to the break at every world-class surf spot — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/surf-hotels"},
 "walks": {"sfx":"Walks","label":"Walks Network","hero":"hero-walks.jpg",
           "subject":"Your walks widget is ready 🥾 — earn 5% of every booking",
           "h1":"Welcome to the trail.",
           "join":"You just joined the IMPT walks network — a small group of guides, gear shops, route makers and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your visitors book hotels right along the world's great walking trails — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/walks"},
 "lgbtq": {"sfx":"Pride","label":"Pride Network","hero":"hero-pride.jpg",
           "subject":"Your Pride widget is ready 🏳️‍🌈 — earn 5% of every booking",
           "h1":"Welcome — everyone's welcome.",
           "join":"You just joined the IMPT Pride network — a community of creators, venues and organisers turning their audience into a global hotel-booking flow.",
           "niche":"Your community books welcoming, verified-friendly stays in 135+ countries — 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/worlds"},
 "scuba": {"sfx":"Scuba","label":"Scuba Network","hero":"hero-scuba.jpg",
           "subject":"Your scuba widget is ready 🤿 — earn 5% of every booking",
           "h1":"Welcome below the surface.",
           "join":"You just joined the IMPT scuba network — a small group of dive schools, liveaboards, shops and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your divers book stays right by the world's best dive sites — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/worlds"},
 "golf":  {"sfx":"Golf","label":"Golf Network","hero":"hero-walks.jpg",
           "subject":"Your golf widget is ready ⛳ — earn 5% of every booking",
           "h1":"Welcome to the clubhouse.",
           "join":"You just joined the IMPT golf network — a small group of clubs, coaches, golf-travel pros and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your golfers book the stay next to the course at the world's best resorts — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/worlds"},
 "yoga":  {"sfx":"Yoga","label":"Yoga & Wellness Network","hero":"hero-sunset.jpg",
           "subject":"Your yoga widget is ready 🧘 — earn 5% of every booking",
           "h1":"Welcome — breathe in.",
           "join":"You just joined the IMPT yoga & wellness network — a small group of studios, teachers, retreat hosts and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your community books retreats and stays near the world's calmest places — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/worlds"},
 "ski":   {"sfx":"Ski","label":"Ski & Snow Network","hero":"hero-travel.jpg",
           "subject":"Your ski widget is ready 🎿 — earn 5% of every booking",
           "h1":"Welcome to the slopes.",
           "join":"You just joined the IMPT ski network — a small group of schools, shops, snow guides and content creators turning their audience into a global hotel-booking flow.",
           "niche":"Your visitors book ski-in/ski-out stays at the world's best resorts — and 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/ski-resorts"},
 "pets":  {"sfx":"Pets","label":"Pet-Friendly Network","hero":"hero-hotels.jpg",
           "subject":"Your pet-friendly widget is ready 🐾 — earn 5% of every booking",
           "h1":"Welcome — paws and all.",
           "join":"You just joined the IMPT pet-friendly network — a small group of groomers, vets, pet creators and communities turning their audience into a global hotel-booking flow.",
           "niche":"Your audience books verified pet-friendly stays in 135+ countries — 8M hotels worldwide.",
           "script":"widget.js","signup":"impt.io/pet-friendly-hotels"},
 "hotels":{"sfx":"Hotels","label":"Partner Network","hero":"hero-hotels.jpg",
           "subject":"Your IMPT widget is ready 🌍 — earn 5% of every booking",
           "h1":"Welcome aboard.",
           "join":"You just joined the IMPT partner network — creators, communities and small businesses turning their audience into a global hotel-booking flow.",
           "niche":"Your audience books any of 8M hotels and apartments in 135+ countries — same prices as the big sites.",
           "script":"widget.js","signup":"impt.io"},
}

def _first(n):
    n=(n or "").strip(); return n.split()[0] if n else "there"

def build_designed(vertical, name, h1, body_html, cta_text, cta_url):
    """Reusable Lovable-style shell (hero + branded header + footer) for ANY widget email
    (install push, nurture, fomo) so the whole workflow uses the designed format, not plain text.
    body_html = the middle content (greeting + paragraphs/boxes); CTA rendered as the orange button."""
    v=(vertical or "").strip().lower(); c=V.get(v, V["hotels"])
    hero=f'{HERO_BASE}/{c["hero"]}'; n=_first(name)
    cta=(f'<a href="{cta_url}" style="display:inline-block;background:{ORANGE};color:#fff;font-weight:700;'
         f'font-size:16px;text-decoration:none;padding:15px 28px;border-radius:999px;">{cta_text} →</a>') if cta_text and cta_url else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#ffffff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:28px 14px;font-family:Helvetica,Arial,sans-serif;">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:{CREAM};border-radius:16px;overflow:hidden;">
  <tr><td><img src="{hero}" width="640" alt="" style="display:block;width:100%;max-width:640px;height:auto;"></td></tr>
  <tr><td style="background:{INK};padding:22px 32px;">
     <span style="font-weight:900;font-size:24px;color:#fff;">impt</span>
     <span style="font-weight:400;font-size:18px;color:#D2D2D7;"> / {c['sfx']}</span>
     <span style="float:right;font-size:11px;color:#fff;letter-spacing:.16em;background:rgba(255,107,26,.18);border:1px solid rgba(255,107,26,.5);border-radius:999px;padding:6px 12px;">{c['label'].upper()}</span>
  </td></tr>
  <tr><td style="padding:40px 40px 30px;color:{INK};">
     <h1 style="font-family:Georgia,serif;font-size:30px;line-height:1.1;margin:0 0 18px;color:{INK};">{h1}</h1>
     {body_html}
     <div style="margin:24px 0 0;">{cta}</div>
     <p style="font-size:15px;color:{INK};line-height:1.5;margin:30px 0 0;">Laura<br><span style="color:{MUTE};">IMPT Partner Team</span></p>
  </td></tr>
  <tr><td style="padding:18px 40px 30px;border-top:1px solid rgba(11,11,14,.08);">
     <p style="font-size:12px;color:{MUTE};line-height:1.6;margin:0;">IMPT Hotels · {c['label']} · 8M hotels, 135+ countries, every booking funds verified climate action.<br>Reply STOP to unsubscribe.</p>
  </td></tr>
</table></td></tr></table></body></html>"""

def build_welcome(name, key, vertical=None, api_token=None):
    v=(vertical or "").strip().lower()
    c=V.get(v, V["hotels"]); vk=v if v in V else "hotels"
    install_url=f"https://swarm.impt.io/widget-install?{'v='+vk+'&' if vk!='hotels' else ''}k={key}"
    share_url=f"https://swarm.impt.io/go?k={key}"
    dash_url=f"https://swarm.impt.io/dashboard?k={key}&t={api_token}" if api_token else None
    snippet_raw=f'<script src="https://swarm.impt.io/{c["script"]}" data-key="{key}" async></script>\n<div id="impt-swarm"></div>'
    snippet_html=_html.escape(snippet_raw).replace("\n","<br>")
    hero=f'{HERO_BASE}/{c["hero"]}'; n=_first(name); subj=c["subject"]
    dash_block = (f'<p style="margin-top:16px;"><a href="{dash_url}" style="display:inline-block;background:{GREEN};color:#fff;font-weight:700;font-size:15px;text-decoration:none;padding:12px 24px;border-radius:999px;">Open my dashboard →</a></p>') if dash_url else ""
    html=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#ffffff;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your IMPT {c['sfx']} widget is live — earn 5% on every booking.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:28px 14px;font-family:Helvetica,Arial,sans-serif;">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:{CREAM};border-radius:16px;overflow:hidden;">
  <tr><td><img src="{hero}" width="640" alt="" style="display:block;width:100%;max-width:640px;height:auto;"></td></tr>
  <tr><td style="background:{INK};padding:22px 32px;">
     <span style="font-weight:900;font-size:24px;color:#fff;">impt</span>
     <span style="font-weight:400;font-size:18px;color:#D2D2D7;"> / {c['sfx']}</span>
     <span style="float:right;font-size:11px;color:#fff;letter-spacing:.16em;background:rgba(255,107,26,.18);border:1px solid rgba(255,107,26,.5);border-radius:999px;padding:6px 12px;">{c['label'].upper()}</span>
  </td></tr>
  <tr><td style="padding:40px 40px 30px;color:{INK};">
     <h1 style="font-family:Georgia,serif;font-size:32px;line-height:1.08;margin:0 0 18px;color:{INK};">{c['h1']}</h1>
     <p style="font-size:16px;line-height:1.6;margin:0 0 16px;color:{INK};">Hi {n}, {c['join']}</p>
     <p style="font-size:16px;line-height:1.6;margin:0 0 8px;color:{INK};">Here's how it works:</p>
     <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 22px;"><tr><td style="font-size:16px;line-height:1.7;color:{INK};">• {c['niche']}<br>• Same rooms, same prices as the big travel sites.<br>• You earn <b>5% of every booking</b>, paid gross.<br>• Every stay funds verified climate action.</td></tr></table>
     <p style="font-size:16px;line-height:1.6;margin:0 0 12px;color:{INK};"><b>Paste this one line before &lt;/body&gt;</b> — your booking widget then appears on every page.</p>
     <div style="background:{INK};color:{CREAM};font-family:Consolas,Menlo,monospace;font-size:13px;line-height:1.6;padding:18px 20px;border-radius:12px;margin:0 0 22px;word-break:break-all;">{snippet_html}</div>
     <a href="{install_url}" style="display:inline-block;background:{ORANGE};color:#fff;font-weight:700;font-size:16px;text-decoration:none;padding:15px 28px;border-radius:999px;">Get my widget code →</a>
     {dash_block}
     <p style="font-size:13px;color:{MUTE};letter-spacing:.06em;margin:26px 0 6px;">NO WEBSITE? SHARE YOUR PERSONAL LINK</p>
     <div style="display:inline-block;background:rgba(31,111,84,.10);border:1px solid rgba(31,111,84,.28);color:{GREEN};font-family:Consolas,Menlo,monospace;font-size:13px;padding:10px 16px;border-radius:999px;">{share_url}</div>
     <p style="font-size:15px;color:{INK};line-height:1.5;margin:30px 0 0;">Laura<br><span style="color:{MUTE};">IMPT Partner Team</span></p>
  </td></tr>
  <tr><td style="padding:18px 40px 30px;border-top:1px solid rgba(11,11,14,.08);">
     <p style="font-size:12px;color:{MUTE};line-height:1.6;margin:0;">IMPT Hotels · {c['label']} · 8M hotels, 135+ countries, every booking funds verified climate action.<br>You're receiving this because you signed up at {c['signup']}. Reply STOP to unsubscribe.</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    text=(f"{c['h1']}\n\nHi {n}, {c['join']}\n\n- {c['niche']}\n- Same rooms, same prices as the big travel sites.\n- You earn 5% of every booking, paid gross.\n- Every stay funds verified climate action.\n\n"
          f"Paste this one line before </body>:\n{snippet_raw}\n\nGet your widget code: {install_url}\nYour dashboard: {dash_url}\nNo website? Share your link: {share_url}\n\nLaura — IMPT Partner Team\nYou signed up at {c['signup']}. Reply STOP to unsubscribe.")
    return subj, html, text
