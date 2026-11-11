# Coach2Earn — Demo Script

*3–5 minutes · Rehearse twice against the deployed URL · Every number must match demo data exactly*

**Demo data quick reference:**
Coach Dani K. · Nairobi Drift · $30/session · 5 sessions · $150 + $12 fee = $162 · KES 20,898 · 1 USD = 129 KES · C2E-48213 · 28/40 hrs · 280 pts · 7% bonus · $420 balance

Mark every live API call: `[LIVE]` — if it fails, say "We have a recording of this step" and switch to the fallback recording.

---

## Opening (on slide 1 — Problem)

*[Advance to Slide 1]*

"Esports coaching is growing fast in Africa. But paying a coach from Kenya through PayPal is expensive — every small payment loses money to FX conversion and fixed fees. Coach Dani K. charges thirty dollars an hour. Across forty hours, those losses add up. We built Coach2Earn to fix that."

*[Advance to Slide 2 — Users]*

"Three people use this platform. Nairobi Drift, a Rocket League team looking for a credible coach. Coach Dani K., ex-national squad, who wants to be paid fairly and on time. And a reviewer on our team, who reads every coach's evidence before the Verified badge appears."

*[Advance to Slide 3 — Demo]*

"Let me show you how it works."

---

## Screen 1 — Discover (30 seconds)

*[Switch to browser — Discover screen]*

"This is the Discover screen. I'm browsing as a team admin for Nairobi Drift."

*[LIVE — POST /api/v1/ai/match called when filters applied. Fallback: "The AI matching is running in the background — you can see the results are already loaded."]*

"I filter by game — Rocket League — and my budget. The AI scores every coach and puts the best match at the top. Dani K. is ranked first. Verified badge, six community endorsements, and a one-line reason the AI generated: [read the reason on screen]. That reason comes from Groq — and if Groq is down, we have a rule-based fallback so the demo never fails."

*[Click on Dani K.'s card]*

---

## Screen 2 — Coach page (30 seconds)

*[Coach page loads]*

"Dani K.'s profile. Evidence links to real sources — tournament results and replay data from Ballchasing. Six endorsements, each from a different community, each dated. The USD price is thirty dollars per session. The KES estimate updates based on today's locked rate — and it's always labelled an estimate."

"Scroll down — bonus terms in plain words. The coach earns up to ten percent of the team's prize money, based on confirmed hours. Paid only after the prize is received."

*[Click the package — 5 sessions]*

---

## Screen 3 — Checkout (45 seconds)

*[LIVE — POST /api/v1/quotes creates the quote. Fallback: "The quote is pre-loaded — the rate is locked for fifteen minutes."]*

"Checkout. Left side: the package breakdown. Five sessions, one fifty. Platform fee eight percent, twelve dollars. Total one sixty-two. Bonus terms box — signed by both parties at checkout."

"Right side: payment method. I'll select M-Pesa. The rate updates — one USD equals one hundred and twenty-nine KES, so Nairobi Drift pays twenty thousand, eight hundred and ninety-eight shillings. That's an estimated saving of about six hundred KES versus a direct PayPal conversion — and it's labelled an estimate."

"Rate lock countdown — fourteen fifty-nine. That gives the team time to pay without worrying about the rate moving."

*[Click 'Pay and book sessions']*

---

## Screen 4 — Payment (30 seconds)

*[PayPal Sandbox loads]*

*[LIVE — POST /api/v1/orders creates the PayPal order. Fallback: "The PayPal sandbox is pre-authorised — let me show you the confirmation."]*

"PayPal Sandbox. I approve the payment."

*[Approve in sandbox]*

*[LIVE — POST /api/v1/orders/{id}/capture captures the payment. Fallback: switch to recording.]*

---

## Screen 5 — Confirmation (30 seconds)

*[Confirmation screen]*

"Payment received. Five sessions with Coach Dani K. are booked. Receipt reference C2E-48213. Total paid KES twenty thousand, eight hundred and ninety-eight. Rate used: one USD equals one twenty-nine."

"Two badges: green — bonus terms signed by both parties. Blue — coach payout releases after each confirmed session. That's our service-completion workflow. The payout sits in our ledger until the session is confirmed. Not escrow — our own rules."

---

## Screen 6 — Session logging (30 seconds)

*[Switch to coach persona — Dani K.]*

*[LIVE — coach starts and ends session via session logging screen. Fallback: "Here's the session logging screen — the coach proposes one hour."]*

"Dani K. logs a session — one hour. Nairobi Drift confirms it."

*[LIVE — team confirms session. Fallback: "The team has confirmed — let's see the dashboard update."]*

---

## Screen 7 — Coach dashboard (30 seconds)

*[LIVE — GET /coaches/{id}/dashboard. Fallback: "Dashboard is pre-loaded."]*

"Dashboard. USD balance four twenty. Hours logged — was twenty-eight of forty, now twenty-nine. Points — was two eighty, now two ninety. Bonus share stays at seven percent — we haven't hit the cap yet. The cap is ten percent at four hundred points."

"If Nairobi Drift wins a two thousand dollar prize, projected bonus is one forty. Paid after the prize is received, in the prize's own currency."

---

## Screen 8 — Skills Passport (20 seconds)

*[LIVE — GET /api/v1/players/{id}/passport. Fallback: "Passport is pre-loaded from our Ballchasing cache."]*

"Player Skills Passport. Replay stats from Ballchasing — matches, goals, saves, shots, boost per minute. Evidence links back to original sources. Coach feedback from Dani K. — structured by AI from her session notes into strengths, focus areas, and next goals."

"The passport is evidence, not a certificate. It doesn't make anyone verified. It just makes the evidence visible and traceable."

---

## Closing (on slide 10 — Call to action)

*[Advance to slide 10]*

"Working app on Render. PayPal Sandbox integrated — Orders, Payouts, webhooks. AI matching live with a deterministic fallback. Skills Passport pulling real data from Ballchasing. Human verification flow built in."

"Coach2Earn. Part of BARBAH PlayEconomy. Thank you."

---

## Timing guide

| Section | Target time |
|---------|------------|
| Opening (slides 1–3) | 30 sec |
| Discover + Coach page | 60 sec |
| Checkout | 45 sec |
| Payment + Confirmation | 60 sec |
| Session log + Dashboard | 60 sec |
| Skills Passport | 20 sec |
| Closing | 20 sec |
| **Total** | **~5 min** |

---

*Rehearse twice. Time yourself. Cut the Skills Passport section if running long.*
