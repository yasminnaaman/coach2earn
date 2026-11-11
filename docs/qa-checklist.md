# Coach2Earn — QA Checklist

**Owner:** Yasmin (QA lead for the whole project)  
**Run at:** 80% mark and again immediately before submission  
**Demo data:** Coach Dani K. · Nairobi Drift · $162.00 · KES 20,898 · C2E-48213 · 280 pts · 7% · $420 balance

Mark each item **PASS**, **FAIL**, or **SKIP** (with reason). Any FAIL must have an owner and a workaround before submission.

---

## Pass 1 — 80% mark

Date: ___________  Run by: ___________

## Pass 2 — before submission

Date: ___________  Run by: ___________

---

## 1. Discover screen

| # | Test | P1 | P2 |
|---|------|----|----|
| 1.1 | Discover screen loads with no console errors | | |
| 1.2 | Coach Dani K. card is visible with Verified badge | | |
| 1.3 | Dani K. card shows "Best match" AI badge | | |
| 1.4 | Dani K. card shows 6 endorsements | | |
| 1.5 | Filter by game = Rocket League shows only Rocket League coaches | | |
| 1.6 | Filter by budget removes coaches above the budget | | |

---

## 2. POST /match endpoint

| # | Test | P1 | P2 |
|---|------|----|----|
| 2.1 | `POST /api/v1/ai/match` with `{ "game": "rocket_league", "role": "forward", "goal": "improve rotations", "budgetUsd": 200 }` returns HTTP 200 | | |
| 2.2 | Dani K. is rank 1 in the response (`bestMatch: true`) | | |
| 2.3 | Response includes `score`, `reason`, `reasonSource` fields | | |
| 2.4 | With valid `GROQ_API_KEY`: at least one result has `reasonSource: "ai"` | | |
| 2.5 | With no `GROQ_API_KEY`: endpoint still returns results with `reasonSource: "rule"` | | |

---

## 3. Coach page

| # | Test | P1 | P2 |
|---|------|----|----|
| 3.1 | Coach page for Dani K. loads with Verified badge | | |
| 3.2 | Evidence links are shown with source URLs | | |
| 3.3 | 6 endorsements are displayed with community and date | | |
| 3.4 | USD price shown as $30.00/session | | |
| 3.5 | KES estimate shown and labelled "estimate" | | |
| 3.6 | Bonus terms shown in plain words | | |

---

## 4. Checkout screen

| # | Test | P1 | P2 |
|---|------|----|----|
| 4.1 | Checkout shows package $150.00, platform fee $12.00, total $162.00 | | |
| 4.2 | M-Pesa / Card option shows KES 20,898 at rate 1 USD = 129.00 KES | | |
| 4.3 | PayPal balance option shows USD 162.00, no conversion | | |
| 4.4 | Switching payment method updates the "You pay" amount live | | |
| 4.5 | Rate lock countdown starts at 14:59 and decrements | | |
| 4.6 | FX saving note says "about KES 600" and is labelled "estimate" | | |
| 4.7 | Bonus terms box is shown: "Coach earns up to 10% of prize money…" | | |
| 4.8 | Footer shows refund/dispute policy link | | |
| 4.9 | Word "escrow" does not appear anywhere on the page | | |
| 4.10 | When rate lock expires: "Rate expired. Refresh the quote" message appears | | |

---

## 5. Payment and confirmation

| # | Test | P1 | P2 |
|---|------|----|----|
| 5.1 | "Pay and book sessions" button initiates PayPal sandbox flow | | |
| 5.2 | Sandbox payment completes without error | | |
| 5.3 | Confirmation screen shows green check and "Payment received" | | |
| 5.4 | Confirmation shows receipt ref C2E-48213 | | |
| 5.5 | Confirmation shows "Your 5 sessions with Coach Dani K. are booked" | | |
| 5.6 | Green badge "Bonus terms signed by both parties" is visible | | |
| 5.7 | Blue badge "Coach payout releases after each confirmed session" is visible | | |
| 5.8 | Total paid shows KES 20,898 and rate 1 USD = 129.00 KES | | |
| 5.9 | "Add to calendar" button works (downloads .ics or opens calendar) | | |

---

## 6. Coach dashboard

| # | Test | P1 | P2 |
|---|------|----|----|
| 6.1 | Dashboard loads for Dani K. with no console errors | | |
| 6.2 | USD balance shows $420.00 | | |
| 6.3 | Hours logged shows 28 / 40 | | |
| 6.4 | Points shows 280 | | |
| 6.5 | Bonus share shows 7% | | |
| 6.6 | Bonus progress bar is at 70% (280 / 400) | | |
| 6.7 | "Cap 10% at 400 points" label is shown | | |
| 6.8 | "If the team wins a $2,000 prize, projected bonus is $140" is shown | | |
| 6.9 | Activity list shows session status pills (Confirmed, Paid, Scheduled, Pending win) | | |

---

## 7. Session logging

| # | Test | P1 | P2 |
|---|------|----|----|
| 7.1 | Coach can start a session | | |
| 7.2 | Coach can end the session and propose 1 hour | | |
| 7.3 | Team admin receives notification / can see the pending session | | |
| 7.4 | Team confirms the session | | |
| 7.5 | After confirmation: points update from 280 → 290 | | |
| 7.6 | Dashboard refreshes to show 290 points | | |
| 7.7 | Bonus share remains 7% at 290 points (cap not reached) | | |

---

## 8. Skills Passport

| # | Test | P1 | P2 |
|---|------|----|----|
| 8.1 | `GET /api/v1/players/{id}/passport` returns HTTP 200 | | |
| 8.2 | `replayStats` fields are populated: matches, goals, saves, shots, boostPerMinute | | |
| 8.3 | With no `BALLCHASING_API_KEY`: endpoint still returns stats from cached sample | | |
| 8.4 | `evidence[]` array contains at least one item with a source URL | | |
| 8.5 | `feedback[]` array contains at least one entry from Dani K. | | |
| 8.6 | Skills Passport screen loads and displays all sections | | |
| 8.7 | `POST /api/v1/players/{id}/evidence` with `{ "type": "tournament", "url": "https://start.gg/test" }` returns HTTP 201 and updated evidence list | | |
| 8.8 | Invalid evidence type returns HTTP 422 | | |

---

## 9. Session feedback

| # | Test | P1 | P2 |
|---|------|----|----|
| 9.1 | `POST /api/v1/ai/sessions/{id}/feedback` returns HTTP 200 | | |
| 9.2 | Response has non-empty `strengths[]`, `focusAreas[]`, `nextGoals[]` | | |
| 9.3 | With no `GROQ_API_KEY`: endpoint still returns fallback structured output | | |
| 9.4 | Session with no coach notes returns HTTP 422 | | |

---

## 10. Verification evidence organiser

| # | Test | P1 | P2 |
|---|------|----|----|
| 10.1 | `POST /api/v1/ai/verification/submissions` returns HTTP 200 | | |
| 10.2 | Response for Dani K. includes `claims`, `sources`, `gaps: []`, `redFlags: []` | | |
| 10.3 | `summary` field is a non-empty string | | |
| 10.4 | With no `GROQ_API_KEY`: fallback returns safe default with "Manual review required" | | |
| 10.5 | Verification review queue screen shows "A person reviews every coach before they are verified." | | |
| 10.6 | AI does not mark anyone as Verified in any response | | |

---

## 11. Trust, compliance and copy

| # | Test | P1 | P2 |
|---|------|----|----|
| 11.1 | Word "escrow" does not appear on any screen or in any API response | | |
| 11.2 | Every FX rate on screen is labelled "estimate" or "demo value" | | |
| 11.3 | README Trust and Compliance section covers all six topics | | |
| 11.4 | Under-18 consent requirement is documented in README or shown in app | | |
| 11.5 | eTIMS statement says "No compliance is claimed at this stage" | | |

---

## 12. Deployment

| # | Test | P1 | P2 |
|---|------|----|----|
| 12.1 | Deployed Render URL responds to `GET /api/v1/health` with HTTP 200 | | |
| 12.2 | Frontend loads on the deployed URL (not localhost) | | |
| 12.3 | Full demo path works on the deployed URL end-to-end | | |
| 12.4 | Render URL is confirmed live at least 30 minutes before submission | | |
| 12.5 | Health route is pinged 10 minutes before demo to wake free-tier instance | | |

---

## 13. Demo readiness

| # | Test | P1 | P2 |
|---|------|----|----|
| 13.1 | Demo script exists at `/pitch/demo-script.md` | | |
| 13.2 | Script has been rehearsed at least twice against the deployed URL | | |
| 13.3 | Screen recording fallback exists and covers the full demo path | | |
| 13.4 | Recording was made from the deployed URL (not localhost) | | |
| 13.5 | All demo data values in the script match exactly: $162, KES 20,898, C2E-48213, 280 pts, 7%, $420 | | |

---

## Failure log

Use this table to track any failures found during either pass.

| # | Test ref | Failure description | Owner | Workaround | Resolved in Pass |
|---|----------|--------------------|----|------------|-----------------|
| | | | | | |
| | | | | | |
| | | | | | |

---

*QA owner: Yasmin · Two passes required: 80% mark and before submission*
