# IMPT Swarm Widget — Open-Source Spec

**Date:** 2026-05-05
**Status:** Spec for tonight's launch
**Repo (proposed):** `github.com/impt/swarm-widget`
**License:** MIT
**Commission:** 5% of confirmed booking revenue, paid to partner per booking
**Checkout:** IMPT (`app.impt.io/find-hotel-input`)

---

## 1. What we're shipping tonight

A free, open-source, MIT-licensed JavaScript widget that any developer, hotel, blogger or affiliate can drop on their site to earn **5% commission** on every IMPT hotel booking they drive.

```html
<script src="https://swarm.impt.io/widget.js"
        data-key="YOUR_PARTNER_KEY"
        data-cause="trees"
        async></script>
<div id="impt-swarm"></div>
```

That's it. Renders a cream-skin search box. Guest searches → lands on `app.impt.io/find-hotel-input` → books → partner earns 5% + Goodness mechanic gives 3% to cause + 2% to next-stay.

Built in public on GitHub. Stars, PRs, forks all welcome.

---

## 2. Why open source + 5% is the right move

| Argument | Detail |
|---|---|
| **Distribution** | Stripe got into millions of sites by being open + good docs. Calendly/Tally same. We need to be the default hotel widget — being closed-source kills that |
| **Trust** | Hotels and developers will only embed code they can read. Closed widget = no installs from anyone serious |
| **Backlinks** | Every install is a JS request to swarm.impt.io with the partner key — implicit backlink, partner page boost |
| **Affiliate gravity** | 5% on a €200 booking = €10 earned. Higher than Booking.com's affiliate rate (4%). Travel bloggers will flip to us |
| **Network effect** | Each install widens the funnel. PRs from the community improve the widget for free |
| **Anti-Booking moat** | Booking.com would never open-source their search box. We can. That's the moat |

---

## 3. The repo (`github.com/impt/swarm-widget`)

```
impt-swarm-widget/
├── README.md                  # Hero pitch + 60-second integration + live demo gif
├── LICENSE                    # MIT
├── CONTRIBUTING.md            # PR guidelines
├── CODE_OF_CONDUCT.md         # Contributor Covenant 2.1
├── package.json               # ESM + CJS + UMD bundles
├── tsconfig.json
├── src/
│   ├── widget.ts              # Main entry — shadow DOM custom element
│   ├── search-box.ts          # Cream-skin search UI
│   ├── city-picker.ts         # Static city list (no Maps quota — per memory)
│   ├── tracking.ts            # UTM + partner-key cookie + GA4
│   ├── styles.css             # Cream skin, Inter font
│   └── index.ts
├── examples/
│   ├── basic.html             # Plain HTML embed
│   ├── react.jsx              # React component wrapper
│   ├── nextjs.tsx             # Next.js (App Router)
│   ├── wordpress.php          # WP shortcode
│   └── shopify.liquid         # Shopify block
├── docs/
│   ├── integration.md         # Step-by-step
│   ├── commission.md          # How 5% works
│   ├── attribution.md         # UTM + cookie window + edge cases
│   ├── theming.md             # CSS variable overrides
│   └── faq.md
├── .github/
│   ├── workflows/
│   │   ├── ci.yml             # Lint + build + size budget
│   │   └── publish.yml        # npm publish on tag
│   └── ISSUE_TEMPLATE/
└── dist/                      # Built bundles (gitignored, served via CDN)
```

**Hosted CDN:** `https://swarm.impt.io/widget.js` (one-line embed) — and `npm i @impt/swarm-widget` for bundlers.

---

## 4. Commission mechanic — exactly how 5% works

### 4.1 The numbers

- **Base booking value** = nightly rate × nights × rooms (tax + fees excluded)
- **Partner commission** = 5% of base booking value
- **Goodness** = unchanged: €5 free signup + 5% per-booking split (3% cause, 2% next-stay credit) — paid by IMPT, not deducted from partner
- **Currency** = destination currency (per memory rule 2026-05-03 PM); partner payout in EUR by default, USD/GBP optional

### 4.2 Attribution flow

1. Guest visits partner site, clicks widget → request to `swarm.impt.io/widget/r?key=<partner>&dest=<city>`
2. Backend sets first-party cookie `impt_partner=<key>` for `*.impt.io` (90-day window) + 302 redirects to `app.impt.io/find-hotel-input?destination=<CITY>&utm_source=swarm-<key>&utm_medium=widget&utm_campaign=oss`
3. Guest searches → views hotel → checks out on `app.impt.io`
4. Booking confirmation triggers webhook `swarm.impt.io/api/booking` with booking_id, partner_key, base_value
5. Backend records accrual row in `partner_accruals` table

### 4.3 Attribution window

- **Last-touch wins** — if guest clicks two different partner widgets, the most recent wins (industry standard, matches Booking affiliate)
- **Cookie window** — 90 days (Booking is 30, Expedia is 7 — we beat both)
- **Cross-device** — if guest signs in to existing IMPT account on another device within window, attribution carries on the user record
- **Cancellations** — accruals reverse on cancellation; payouts only on **non-refundable + checked-in** bookings

### 4.4 Payout

- **Threshold** — €50 minimum
- **Cadence** — monthly, on the 5th, for bookings checked-in 30+ days prior (refund window)
- **Method** — Wise / PayPal / IMPT card / IMPT token (partner choice)
- **Statement** — automated monthly email + dashboard at `partners.impt.io/widget`
- **Tax** — partner is responsible for declaring own income; IMPT issues annual statement

### 4.5 Anti-fraud

- Self-bookings on same partner key flagged (IP + email match)
- VPN / TOR detection on widget click
- Hotel-employee email domains denied (no "self-affiliate" loop)
- Click-to-conversion ratio anomaly alerts
- Reuses fraud-defence-2026-05-02 stack (CF WAF + ASN block + invalid-click pause)

---

## 5. Backend (built tonight)

### 5.1 Service

- **Host:** this server (35.214.111.96), behind nginx at `swarm.impt.io/api/widget/*`
- **Stack:** FastAPI + SQLite (move to Postgres on day 30)
- **Systemd unit:** `impt-swarm-widget.service` on port 2027 (2025=AJ, 2026=swarm-chat, 2027=widget)

### 5.2 Endpoints

```
POST   /api/widget/partners/signup       { email, name, payout_method }
GET    /api/widget/r                     ?key=&dest= → 302 + cookie
POST   /api/widget/booking               { booking_id, partner_key, base_value, currency }  ← webhook from app.impt.io
GET    /api/widget/partners/me           Bearer auth → balance, history
GET    /api/widget/health                liveness
```

### 5.3 Tables

```
partners(id, key, email, name, payout_method, payout_target, created_at, status)
partner_clicks(id, key, ts, ip_hash, ua_hash, dest)
partner_bookings(id, partner_key, booking_id, base_value, currency, accrual_eur, status, booked_at, check_in_at)
partner_payouts(id, partner_key, amount_eur, period_start, period_end, paid_at, method, ref)
```

### 5.4 IMPT-side hook (to coordinate with Henry)

`app.impt.io` checkout already reads UTM. Need to add:
- On booking confirmation, if `utm_source` starts with `swarm-`, POST to `https://swarm.impt.io/api/widget/booking` with `{booking_id, partner_key=utm_source[6:], base_value, currency}`
- 5-line patch — Henry can do during the morning standup

For tonight: I'll mock the webhook with a Mongo-tail script that watches `bookings` collection and posts to the swarm endpoint. **Reversible**, no Henry blocker.

---

## 6. Widget tech (built tonight)

- **Bundle size budget** — < 12KB gzipped (CI fails the build above)
- **Shadow DOM custom element** `<impt-swarm>` — zero CSS collision
- **Cream skin** — matches find-hotel-input redesign (per memory 2026-05-03 PM)
- **Static city list** — `city-defaults.ts` from memory rule (no Maps quota)
- **Date defaults** — none in URL (per memory 2026-05-04); user picks on lander
- **Currency** — destination-driven (per memory 2026-05-03)
- **Tracking** — UTM + partner cookie + page-view ping to swarm.impt.io
- **Accessibility** — WCAG AA, keyboard-only navigable, screen-reader tested
- **i18n** — English only at launch; PRs welcome

---

## 7. README hero pitch (front of repo)

> # 🌍 IMPT Swarm Widget
> The open-source hotel-search widget that pays you 5%.
>
> One line. Drop it anywhere. Earn 5% on every booking. Plant a tree per stay in your name.
>
> ```html
> <script src="https://swarm.impt.io/widget.js" data-key="YOUR_KEY" async></script>
> <div id="impt-swarm"></div>
> ```
>
> [Get a key](https://partners.impt.io/widget) · [Live demo](https://swarm.impt.io/widget) · [Docs](./docs/integration.md)

---

## 8. Launch checklist (tonight)

- [ ] Spec emailed to Mike ← **doing now**
- [ ] Local repo built with full file tree
- [ ] widget.js working (cream skin, shadow DOM, < 12KB)
- [ ] Backend running on :2027 with all 5 endpoints
- [ ] nginx proxy `swarm.impt.io/widget.js` + `/api/widget/*` + `/widget` (demo)
- [ ] Demo page live at `swarm.impt.io/widget`
- [ ] Partner signup form live
- [ ] Mongo-tail mock webhook running (until Henry wires real hook)
- [ ] README with live demo gif + hero pitch
- [ ] LICENSE + CONTRIBUTING + COC files
- [ ] CI green
- [ ] **HOLD: `git push` to public github.com/impt/swarm-widget — awaits Mike's explicit go on final eyeballed contents (per memory rule 2026-05-05)**
- [ ] Per memory rule: nothing tweeted/posted/announced until Mike's eyes-on. Repo can go live tonight; **announcement waits for separate green light**

---

## 9. Decisions needed from Mike (before push)

1. **Org:** push under `IMPTSystem` GitHub org (existing) or a new `impt-oss` org?
2. **Repo name:** `impt-swarm-widget` or `swarm` (cleaner) or `impt`?
3. **Commission:** 5% confirmed? Booking.com's IPP affiliate is 4%, Expedia 4%. We beat both at 5%. Could go 6% to dominate; could go 4% to protect margin. **Recommend 5%**.
4. **Cookie window:** 90 days (industry-leading) or 30 days (industry-standard)? Recommend 90.
5. **Announcement:** tonight or hold for a Tuesday product-hunt-style launch with prepared assets? Recommend hold for proper launch — repo live silently tonight, announcement Tuesday.

---

## 10. Risk + reversibility

| Risk | Mitigation |
|---|---|
| Bad actors mass-spam fake partner keys | Email-verify on signup + ASN/IP fraud filters from existing stack |
| Self-bookings to game 5% | IP + email match block, hotel-employee domain block |
| Widget bundles get heavy over time | CI size budget + Lighthouse perf gate |
| IMPT-side webhook delay → late accruals | Mongo-tail mock for first 2 weeks, then Henry's real hook |
| Cancellation refunds | Accruals reverse automatically on cancel webhook |
| Public repo exposes secrets | Hardcoded test keys only; real backend separate; backend code stays private |
| Push happens before Mike eyes-on | Per memory rule, push command staged but **NOT executed** until Mike's explicit go |

**Everything tonight is reversible.** Local repo, dry-run github creation, and unannounced public repo can all be torn down or hidden in seconds.

---

## 11. After launch (week 2-4)

- npm publish `@impt/swarm-widget`
- React + Vue + WordPress plugin packages
- White-label theme support (per-partner accent + logo)
- Push notifications via service worker
- Per-partner Goodness cause customisation (their charity)
- Apple Wallet / Google Wallet booking pass
- App Store wrapper via Capacitor
- Affiliate leaderboard (top 100 earning partners get bonus)

---

*Drafted by Claude on 2026-05-05. Spec → email → tech build starts immediately. Public push waits for Mike's eyes-on per memory.*
