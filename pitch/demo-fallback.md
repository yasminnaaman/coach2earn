# Coach2Earn — Demo Fallback Plan

*Read this before the demo. Know it by heart. A calm fallback is better than a failed live call.*

---

## Deployed URL

Fill in when Hope provides it: `https://_____________________.onrender.com`

Health check: `GET /api/v1/health` — ping this 10 minutes before the demo to wake the free-tier instance.

---

## Fallback sentence (use for any live call that fails)

> "We have a recording of this step — let me show you."

Then switch to the screen recording (see below). Keep talking — narrate over the recording exactly as you would the live demo. Judges cannot tell the difference if you stay calm.

---

## Screen recording

**What to record:** The full demo path from Discover to dashboard update, on the deployed Render URL.  
**When to record:** After the app is deployed and seeded with demo data.  
**Format:** MP4, at least 1080p, no audio needed (you narrate live).  
**Where to save:** `/pitch/recording/demo-full.mp4` (do not commit to GitHub — file is too large. Save locally and to a shared Google Drive link).

**Timestamps to note after recording:**

| Step | Recording timestamp |
|------|-------------------|
| Discover screen loads | |
| Coach Dani K. card visible | |
| Coach page | |
| Checkout with KES 20,898 | |
| PayPal sandbox approval | |
| Confirmation C2E-48213 | |
| Session logged | |
| Dashboard shows 290 points | |
| Skills Passport | |

---

## Step-by-step fallback for each live call

### POST /match (Discover screen)
**Fallback:** Results are pre-loaded from the last successful call. Say:  
*"The AI matching ran when the page loaded — you can see Dani K. is ranked first with a Groq-generated reason."*

### POST /quotes (Checkout)
**Fallback:** Quote is pre-loaded. Say:  
*"The rate is locked — one USD equals one twenty-nine KES, valid for fifteen minutes."*

### POST /orders (Payment)
**Fallback:** Switch to recording at the PayPal sandbox timestamp. Say:  
*"We have a recording of the sandbox payment — the flow is identical."*

### POST /orders/{id}/capture (Capture)
**Fallback:** Continue with recording. Confirmation screen C2E-48213 should appear in the recording.

### Session confirm → dashboard update
**Fallback:** Pre-seed the dashboard with 290 points before the demo. Say:  
*"The team has already confirmed the session — you can see the dashboard has updated to two ninety points."*

### GET /players/{id}/passport (Skills Passport)
**Fallback:** `DEMO_MODE=true` means the cached Ballchasing sample always loads. No live API needed. This step should never fail.

---

## If the whole app is down (Render sleeping or crashed)

1. Switch immediately to the screen recording.
2. Say: *"We have a full recording of the demo path — let me walk you through it."*
3. Play the recording and narrate the demo script over it.
4. At the end, say: *"The app is live at [URL] — we're happy to show you after the session."*

---

## Risk table

| Risk | Fallback |
|------|---------|
| PayPal Payouts not enabled on sandbox | `PAYPAL_MODE=mock` — show "simulated" flag, keep Orders on real sandbox |
| Render free tier sleeping | Ping `/api/v1/health` 10 min before demo |
| Ballchasing key missing or rate-limited | `DEMO_MODE=true` — cached sample always loads |
| Groq LLM call fails | Rule-based scoring and reasons — `reasonSource: "rule"` |
| Groq key missing entirely | Same — deterministic fallback, demo still works |
| Live demo fails entirely | Play screen recording, narrate over it |
| Merge conflict before demo | Each person owns their folder — pull before push |

---

## Pre-demo checklist (run 30 minutes before)

- [ ] Ping deployed URL health check — confirm HTTP 200
- [ ] Log in as `team_admin` persona and confirm Discover screen loads
- [ ] Confirm Dani K. card appears with Verified badge
- [ ] Run `POST /match` manually in Postman — confirm Dani K. is rank 1
- [ ] Confirm screen recording is accessible (local + Google Drive link)
- [ ] Confirm all demo data is seeded (Dani K., Nairobi Drift, C2E-48213, 280 pts)
- [ ] Confirm `GROQ_API_KEY` is set on Render
- [ ] Confirm `DEMO_MODE=true` is set on Render

---

*Fallback plan owner: Yasmin · Update the Render URL and recording timestamps before the demo day*
