# Coach2Earn — Slide Outline

*8–12 slides · 3–5 minutes · Use demo data exactly*

---

## Slide 1 — Problem

**Title:** Paying a coach from Africa costs too much

- A coach in Kenya earning $30/hr loses a significant share to FX conversion and PayPal fixed fees on every small payment
- Across 40 hours of coaching, those losses add up to real money
- The current system makes cross-border esports coaching commercially unsustainable

---

## Slide 2 — Users

**Title:** Three people, one platform

- **The player / team:** Nairobi Drift wants a Rocket League coach. They need credibility evidence, not just a profile page.
- **The coach:** Dani K., ex-national squad, wants fair pay in USD without losing money to FX on every transaction.
- **The reviewer:** Someone on the platform reads evidence and approves coaches. The AI never does this.

---

## Slide 3 — Demo

**Title:** Watch it work

- Live demo: Discover → Coach Dani K. → Quote → Pay (PayPal Sandbox) → Confirmation
- Receipt ref C2E-48213 · 5 sessions booked · KES 20,898 paid
- Then: coach logs a session, Nairobi Drift confirms it, dashboard updates to 290 points

*[DEMO BEGINS HERE — switch to browser]*

---

## Slide 4 — How it works

**Title:** The full flow

- Team discovers coach via AI matching (`POST /match` — transparent scoring + Groq one-liner)
- Quote locks the rate for 15 minutes (1 USD = 129.00 KES, estimate)
- PayPal Orders API creates and captures the payment
- Platform ledger holds the coach payout
- Session confirmed → payout releases via PayPal Payouts API

---

## Slide 5 — AI features

**Title:** AI that assists, never decides

- **Coach matching:** transparent 100-point scoring (verified, endorsements, price, availability) + Groq one-line reason. Deterministic fallback if LLM is down.
- **Session feedback:** coach writes notes → AI structures them into strengths, focus areas, next goals → appears in player's Skills Passport
- **Evidence organiser:** AI summarises coach evidence for a human reviewer. The human approves. Always.

> "A person reviews every coach before they are verified."

---

## Slide 6 — Trust

**Title:** Built to be trusted

- Verified badge = human-approved, every time
- Endorsements: one per community, public, dated, burst detection
- Service-completion workflow: payout held until session confirmed (not escrow — our own ledger)
- Under-18 consent: parental consent required before any profile or booking
- Records designed to support a later KRA eTIMS integration — no compliance claimed now

---

## Slide 7 — Business model

**Title:** How we make money

- **8% platform fee** on every booking (demo: $12.00 on $150.00 package)
- **Bonus model:** 1 hour = 10 points · bonusPct = min(10, points × 0.025) · paid from prize money only
- Session bundles, monthly programmes, quarterly retainers
- Team and institutional packages (schools, gaming centres, national federations)

*Fee figures: Brian / Postman collection*

---

## Slide 8 — FX story

**Title:** Five ways we reduce FX losses

*(All rates shown are estimates and demo values)*

- Price in USD, show KES estimate locked for 15 min
- Team pays KES via M-Pesa or card — we convert in bulk
- Coaches keep USD in PayPal balance — no round-trip conversion
- Weekly batched payouts via PayPal Payouts API — fewer fixed fees
- Session bundles = fewer transactions = fewer fees
- Demo saving: est. KES 600 vs direct PayPal conversion

---

## Slide 9 — Scale

**Title:** Beyond Rocket League

- **Other games:** scoring and passport are game-agnostic — add a game by adding its evidence types and stat sources
- **Communities:** schools, gaming centres, esports academies, national federations
- **PlayEconomy:** Coach2Earn is one product — the Skills Passport, endorsement graph and verified identity layer become shared infrastructure for other PlayEconomy products
- Starting in Kenya · Built for Africa · Designed to travel

---

## Slide 10 — Why these tools

**Title:** Every tool earns its place

| Tool | Why it's here |
|------|--------------|
| PayPal Sandbox | Orders + Payouts + webhooks — not just a button. Full payment lifecycle. |
| Postman | Documented, reproducible integration tests. Judges can verify independently. |
| Render | Zero-DevOps deploy from GitHub. Live URL ready for judging. |
| Groq (free LLM) | Fast, free, reliable. Deterministic fallback means demo never dies. |
| Ballchasing API | Real Rocket League replay stats as evidence. Cached for offline demo. |

---

## Slide 11 — Call to action

**Title:** Coach2Earn

- Working app on Render · PayPal Sandbox integrated · AI matching live
- Repo: github.com/yasminnaaman/coach2earn
- Built in 48 hours by Hope, Brian, Reberatha and Yasmin · BARBAH PlayEconomy · PayPal AI Hackathon

*Thank you*

---

*Slide notes: keep each slide to one spoken idea. Advance slides during the demo at the transitions marked [DEMO BEGINS HERE] and [DEMO ENDS HERE].*
