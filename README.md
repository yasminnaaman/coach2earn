# Coach2Earn

Part of **BARBAH PlayEconomy** · Built for the PayPal AI Hackathon (Challenge 01, organiser BARBAH Games)

---

## Problem

Paying an experienced international coach from Africa through PayPal is expensive. Converting KES to USD loses money — especially across many small payments. An experienced coach based in Kenya who charges $30/hr loses a meaningful share of every payment to conversion fees and fixed transaction costs. This makes cross-border coaching economically unsustainable at scale.

---

## Users

| Persona | Need |
|---------|------|
| **Gamer / Player** | Find a credible, affordable coach for their game and role. See real performance evidence, not just self-reported claims. |
| **Coach** | Get paid fairly and on time. Build a verifiable reputation across teams and communities. |
| **Team admin** | Book a coach for the squad, pay in KES or USD, track session progress and bonus terms transparently. |
| **Reviewer** | Quickly assess coach evidence submissions and approve or reject with confidence. |

---

## Experience (screens)

1. **Discover** — filter by game, role, budget, goal. Coach cards with Verified badge, endorsement count, price, and an AI "best match" badge with a one-line reason.
2. **Coach page** — profile, evidence of past teams and results with source links, endorsements, packages, USD price with a KES estimate, bonus terms in plain words.
3. **Checkout** — package breakdown ($150 + $12 fee = $162), payment method selector (M-Pesa / Card / PayPal balance), rate lock countdown, FX saving estimate, "Pay and book sessions" button.
4. **Confirmation** — receipt (ref C2E-48213), 5 booked sessions with Dani K., bonus terms badge, payout-on-confirm badge.
5. **Coach dashboard** — USD balance, hours logged, points, bonus share, activity feed.
6. **Session logging** — coach proposes hours, team confirms or disputes, confirmed hours add points.
7. **Skills Passport** — player rank, Ballchasing replay stats, evidence links, coach feedback history.
8. **Verification review queue** — AI-organised evidence summary for a human reviewer to approve or reject.

---

## Technology

### Why PayPal Developer Platform
PayPal is used as a structured payment infrastructure, not just a button. The integration covers:
- **Orders API** — creates and captures the booking payment in sandbox.
- **Payouts API** — batches coach payments weekly; reduces fixed fees per transaction.
- **Webhooks** — listens for `PAYMENT.CAPTURE.COMPLETED` and `PAYMENT.PAYOUTS-ITEM.SUCCEEDED` to trigger ledger updates and session confirmation.

This means the platform controls when a coach payout is released (after session confirmation) through its own ledger — not through PayPal's infrastructure. PayPal handles the movement of money; the platform handles the rules.

### Why Postman
All PayPal sandbox flows are documented and reproducible in a Postman collection under `/docs/`. Each request is annotated with the expected response shape and the business rule it tests. This lets judges and teammates verify the integration independently without running the full app.

### Why Render
Zero-DevOps deployment from the GitHub repo. The working app URL is live and shareable for judging. Environment variables (including API keys) are stored in Render's secret management — never in the repo.

### Why Calendly
Session scheduling is embedded rather than built from scratch. This keeps the hackathon scope focused on the payment and AI flows that differentiate the product. Calendly handles reminders, timezone conversion, and calendar invites.

### Why AG Grid (optional)
Coach discovery and leaderboard tables need sort, filter, and pagination. AG Grid provides this without custom table code. Used in the Discover screen and the coach dashboard activity feed.

---

## Business Model

| Revenue source | Detail |
|---------------|--------|
| Platform fee | 8% on every booking (demo: $12.00 on a $150.00 package = $162.00 total) |
| Session bundles | 5-session packs reduce per-transaction PayPal fees and increase coach commitment |
| Monthly programmes | Fixed monthly retainer between coach and team — predictable revenue |
| Quarterly programmes | Longer commitment, discounted rate, higher lifetime value |
| Team packages | Bulk bookings for squads or organisations |
| Institutional packages | Schools, gaming centres, esports academies |

### Bonus model
- 1 confirmed coaching hour = 10 points
- `bonusPct = min(10, points × 0.025)`
- 280 points → 7%; 400 points → 10% cap
- Bonus is paid only after the team's prize money is actually received, in the prize's own currency
- Example: $2,000 prize at 7% = $140 bonus to the coach

---

## FX Story

*All rates and savings shown are estimates and demo values. No rate is guaranteed beyond the 15-minute lock window.*

| Strategy | How it helps |
|----------|-------------|
| Price in USD, show KES estimate | Team sees a familiar currency; rate is locked for 15 minutes to allow checkout |
| Team pays in KES (M-Pesa or card) and platform converts in bulk | Fewer, larger conversions = better effective rate than many small ones |
| Coaches keep USD in their PayPal balance | Avoids a USD→KES→USD round trip on every payment |
| Weekly batched payouts via PayPal Payouts API | Reduces fixed fees by grouping multiple coach payments into one batch |
| Session bundles | Fewer transactions = fewer fixed fees |
| Team pays from a PayPal USD balance | No conversion needed at all |

Demo rate: **1 USD = 129.00 KES** (demo value, locked for 15 min).  
Estimated saving vs direct PayPal conversion: **about KES 600** (estimate).

---

## Coach Matching — Scoring Algorithm

`POST /match` runs a transparent scoring function before calling the LLM for the one-line reason. If the LLM call fails, a deterministic fallback reason is returned — the endpoint never fails just because the AI is unavailable.

### Scoring table

| Component | Max points | Rule |
|-----------|-----------|------|
| Game match | required | Coach is eliminated if game does not match |
| Role match | required | Coach is eliminated if role does not match |
| Verified | +20 | Binary: verified coach scores 20, unverified scores 0 |
| Endorsement count | 0–20 | `min(endorsementCount, 10) × 2` |
| Price within budget | +20 | `priceUsd ≤ budgetUsd` scores 20, otherwise 0 |
| Availability | +20 | Coach has open slots this week |
| Endorsement spread | 0–20 | Endorsements from distinct communities score higher than clustered ones |
| **Total** | **100** | |

### LLM reason generation
The top 5 coaches by score each receive a one-line reason generated by the LLM using the coach profile and the player's stated goal. The reason is labelled `reasonSource: "ai"` in the response.

### Deterministic fallback
If the LLM call fails or times out, the reason is built from coach fields:  
`"Verified {game} {role} coach, {n} community endorsements, within your ${budget} budget."`  
This is labelled `reasonSource: "rule"`. The UI shows the AI badge only for `"ai"` reasons.

---

## Scale Story

Coach2Earn starts with Rocket League in Kenya. The model scales along three axes:

1. **Games** — the scoring and passport system is game-agnostic. Add a game by adding its evidence types and stat sources (e.g. Valorant tracker, FIFA game reports).
2. **Communities** — schools, gaming centres, esports academies, and national federations can each have their own team and institutional packages.
3. **PlayEconomy products** — Coach2Earn is one product in the BARBAH PlayEconomy suite. The Skills Passport, endorsement graph, and verified identity layer are shared infrastructure that other PlayEconomy products can build on.

---

## Trust and Compliance

### Verification
Every coach profile is reviewed by a person before the Verified badge is shown. Our AI organises submitted evidence and flags gaps — but a human makes the final approve, reject, or "needs more evidence" decision.

> **"A person reviews every coach before they are verified."**

### Endorsements
Each community member may endorse a coach once. All endorsements are public and dated. The platform monitors for unusual bursts of new endorsements and flags them for human investigation. No automated action is taken on endorsements — a human investigates any flagged burst.

### Session-completion workflow
Coach payouts are held in the platform's own ledger until the team confirms the session hours. This is not a third-party financial arrangement — it is the platform's own workflow to ensure coaches are paid only for confirmed work.

### Refunds and disputes
A session must be confirmed before any payout is released. If a team disputes a session, the payout is paused and both parties are notified. The dispute policy is linked on the checkout page.

### Under-18 consent
Players under 18 require verifiable parental or guardian consent before a profile is created or any session is booked. No data about minors is used or displayed in this application. Demo data contains only synthetic adult personas.

### Data protection and consent
Users are shown what data is collected and why at sign-up. Consent is explicit and can be withdrawn. Payment data is processed by PayPal and never stored on the platform's servers.

### Financial records
Transaction records are structured to support a later KRA eTIMS integration through a certified provider. **No eTIMS compliance is claimed at this stage.**

---

## Repository Structure

```
/docs         OpenAPI contract (Hope), seed data (Hope), shapes (Yasmin), QA checklist (Yasmin), Postman collection (Brian)
/server       FastAPI backend (Hope)
  /ai         Coach matching, feedback structuring, evidence organiser (Yasmin)
  /passport   Skills Passport, Ballchasing integration (Yasmin)
  /payments   PayPal Orders, Payouts, webhooks (Brian)
/web          React + Vite + Tailwind frontend (Reberatha)
/pitch        Demo script, slide outline, fallback plan (Yasmin)
```

---

## Team

| Person | Role | Owns |
|--------|------|------|
| Hope | Backend, data and deployment lead | `/server` (everything except ai/passport/payments), `/docs`, Render |
| Brian | PayPal and payments engineer | `/server/payments`, Postman collection |
| Reberatha | Frontend and UX lead | `/web` |
| Yasmin | AI, data, trust and demo lead | `/server/ai`, `/server/passport`, `/pitch`, `README` |

---

*Built at the PayPal AI Hackathon · BARBAH Games · Challenge 01*
