# Privacy Notice

**Effective:** 2026-05-05  ·  **Version:** 0.1.0  ·  **Controller:** IMPT Systems Limited (Ireland)

This notice covers data collected by the **IMPT Swarm Widget** (the JavaScript widget, the hosted endpoints under `swarm.impt.io/api/widget/*`, and the partner programme).

It is layered on top of, not in place of, the main IMPT privacy policy at https://impt.io/privacy.

## What we collect

### From end-users (people using the widget on a partner site)

When the widget loads on a partner page, we receive:
- A **first-party cookie** `impt_partner` on `*.impt.io` (only after the user clicks the widget — not on page load).
- Pixel pings to `swarm.impt.io/api/widget/track` recording: partner key, event type (`view` / `click`), approximate timestamp, referrer hostname (e.g. `your-blog.com`), SHA-256-hashed IP, SHA-256-hashed user-agent.
- We **do not** retain raw IP or raw user-agent. We **do not** receive personally identifying information about end-users from the widget — name, email, address, etc. all happen later inside `app.impt.io`'s checkout, governed by IMPT's main privacy policy.

### From partners (people who sign up at partners.impt.io/widget)

- Email, optional display name, payout method, payout destination (email or address).
- Hashed IP at signup (anti-fraud).
- Audit log of state changes (signup, verification, suspension, termination).

## Why we collect it

- **Attribution**: to credit your partner key with the right commission for the right booking.
- **Anti-fraud**: to detect cookie stuffing, click farms, self-bookings.
- **Legal**: to evidence transactions, comply with tax-reporting and audit obligations.
- **Service**: to operate the widget and the partner dashboard.

## Lawful basis

- For partners: contractual necessity (the partner programme).
- For end-users: legitimate interest in operating an affiliate attribution system, balanced against the modest, hashed nature of the data collected.
- Where your jurisdiction requires opt-in consent for affiliate cookies (EU/UK ePrivacy), the partner who embeds the widget is responsible for obtaining that consent before loading the script.

## Retention

- **Click / view events**: 24 months, then deleted.
- **Booking-attribution records**: 7 years (tax + audit).
- **Partner accounts**: while active + 7 years after closure (tax + audit).
- **Audit log**: 7 years.

## Sharing

We share data with:
- **Payment providers** (Wise, PayPal, etc.) — only what is needed to pay you.
- **Tax authorities** — only as required by law.
- **Hosting providers** (Google Cloud, Cloudflare) — as data processors, under DPAs.

We do not sell partner or end-user data.

## Your rights

If you are an EU/UK individual you have the right to access, correct, erase, restrict, or port your personal data, and to object to processing. Email swarm-widget@impt.io. We respond within 30 days.

If you are an end-user who clicked a widget and want your `impt_partner` cookie removed: clear your `*.impt.io` cookies in your browser, or visit `https://app.impt.io/privacy/clear-cookies` (self-service tool, available in v0.2).

## Cookies summary

| Name | Domain | Lifetime | Purpose |
|---|---|---|---|
| `impt_partner` | `.impt.io` | 90 days | Affiliate attribution last-touch |

The widget does not set any other cookies.

## Contact

- swarm-widget@impt.io (programme questions)
- privacy@impt.io (data-rights requests)
- IMPT Systems Limited, Ireland
- DPO: Mike English, mike@impt.io

## Changes

Material changes are announced via email to active partners 14 days in advance. The current version is always at the top of this document.
