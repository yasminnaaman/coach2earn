# Coach2Earn — API Response Shapes

> **Contributor:** Yasmin  
> **Purpose:** Agrees the exact JSON field names and structures, so Hope can merge them into the OpenAPI contract and Reberatha can build the UI against them.  
> **Source of truth:** Once Hope merges these into `coach2earn-openapi.yaml`, that file takes precedence. Raise any change request with Hope.

---

## `POST /match`

Finds and ranks coaches based on game, role, goal and budget.

### Request body

```json
{
  "game": "rocket_league",
  "role": "forward",
  "goal": "improve rotations and boost management",
  "budgetUsd": 200
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `game` | string | yes | e.g. `rocket_league`, `fifa`, `valorant` |
| `role` | string | yes | e.g. `forward`, `goalkeeper`, `duelist` |
| `goal` | string | yes | Free text, passed to AI for reason generation |
| `budgetUsd` | number | yes | Maximum price per session in USD |

### Response — `200 OK`

Array of matched coaches, ordered by score descending.

```json
[
  {
    "coachId": "coach-001",
    "name": "Dani K.",
    "verified": true,
    "endorsementCount": 6,
    "priceUsd": 30,
    "game": "rocket_league",
    "role": "forward",
    "score": 92,
    "reason": "Verified Rocket League coach with 6 community endorsements, within your $200 budget and available this week.",
    "reasonSource": "ai",
    "bestMatch": true
  },
  {
    "coachId": "coach-002",
    "name": "Alex M.",
    "verified": false,
    "endorsementCount": 2,
    "priceUsd": 25,
    "game": "rocket_league",
    "role": "forward",
    "score": 54,
    "reason": "Rocket League forward coach within budget, not yet verified.",
    "reasonSource": "rule",
    "bestMatch": false
  }
]
```

| Field | Type | Notes |
|-------|------|-------|
| `coachId` | string | Unique coach identifier |
| `name` | string | Display name |
| `verified` | boolean | `true` only after a human reviewer has approved |
| `endorsementCount` | number | Total community endorsements |
| `priceUsd` | number | Price per session in USD |
| `game` | string | Matched game |
| `role` | string | Matched role |
| `score` | number | 0–100 scoring function result (see README for formula) |
| `reason` | string | One-line match explanation |
| `reasonSource` | `"ai"` \| `"rule"` | `"ai"` = LLM generated; `"rule"` = deterministic fallback. UI shows AI badge only when `"ai"` |
| `bestMatch` | boolean | `true` on the rank-1 result only |

---

## `GET /players/{id}/passport`

Returns a player's Skills Passport: rank, replay stats, evidence links, and coach feedback history.

### Path parameter

| Param | Type | Notes |
|-------|------|-------|
| `id` | string | Player identifier |

### Response — `200 OK`

```json
{
  "player": {
    "id": "player-001",
    "name": "Demo Player",
    "game": "rocket_league"
  },
  "rank": "Diamond II",
  "replayStats": {
    "matches": 42,
    "goals": 87,
    "saves": 61,
    "shots": 204,
    "boostPerMinute": 312.4
  },
  "evidence": [
    {
      "id": "ev-001",
      "type": "ballchasing_replay",
      "url": "https://ballchasing.com/replay/abc123",
      "addedAt": "2026-10-15T10:00:00Z"
    },
    {
      "id": "ev-002",
      "type": "tournament",
      "url": "https://start.gg/tournament/nairobi-rl-open",
      "addedAt": "2026-10-20T09:30:00Z"
    }
  ],
  "feedback": [
    {
      "sessionId": "session-001",
      "coachName": "Dani K.",
      "date": "2026-11-12T14:00:00Z",
      "strengths": ["Strong aerial control", "Good boost awareness"],
      "focusAreas": ["Shadow defence positioning", "Rotation recovery after boost pad"],
      "nextGoals": ["Practice 50/50 challenges in freeplay", "Review shadow defence replay clips"]
    }
  ]
}
```

| Field | Type | Notes |
|-------|------|-------|
| `player` | object | Basic player info |
| `rank` | string | Current in-game rank |
| `replayStats` | object | Aggregated from Ballchasing API (cached; see README) |
| `replayStats.matches` | number | Total matches in sample |
| `replayStats.goals` | number | Total goals |
| `replayStats.saves` | number | Total saves |
| `replayStats.shots` | number | Total shots |
| `replayStats.boostPerMinute` | number | Average boost collected per minute |
| `evidence` | array | Source-linked evidence items |
| `evidence[].type` | `"ballchasing_replay"` \| `"video"` \| `"tournament"` | |
| `feedback` | array | Structured feedback from past sessions |
| `feedback[].strengths` | string[] | What the player does well |
| `feedback[].focusAreas` | string[] | What to improve |
| `feedback[].nextGoals` | string[] | Concrete next actions |

---

## `POST /players/{id}/evidence`

Adds a new evidence link to a player's passport.

### Request body

```json
{
  "type": "tournament",
  "url": "https://start.gg/tournament/nairobi-rl-open"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | string | yes | One of: `ballchasing_replay`, `video`, `tournament` |
| `url` | string | yes | Publicly accessible URL |

### Response — `201 Created`

Returns the updated evidence array (same shape as `evidence[]` in the passport above).

```json
[
  {
    "id": "ev-001",
    "type": "ballchasing_replay",
    "url": "https://ballchasing.com/replay/abc123",
    "addedAt": "2026-10-15T10:00:00Z"
  },
  {
    "id": "ev-003",
    "type": "tournament",
    "url": "https://start.gg/tournament/nairobi-rl-open",
    "addedAt": "2026-11-09T20:00:00Z"
  }
]
```

---

## `POST /sessions/{id}/feedback`

Turns a coach's raw post-session notes into structured feedback for the player's passport.

### Request body

```json
{
  "notes": "Really solid aerial control today. Boost management is improving but shadow defence positioning needs work. Next session: focus on 50/50 challenges and review shadow defence clips."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `notes` | string | yes | Coach's free-text notes from the session |

### Response — `200 OK`

```json
{
  "strengths": [
    "Solid aerial control",
    "Improving boost management"
  ],
  "focusAreas": [
    "Shadow defence positioning"
  ],
  "nextGoals": [
    "Practice 50/50 challenges in freeplay",
    "Review shadow defence replay clips"
  ]
}
```

| Field | Type | Notes |
|-------|------|-------|
| `strengths` | string[] | What the player did well this session |
| `focusAreas` | string[] | What needs improvement |
| `nextGoals` | string[] | Concrete actions for the player before next session |

> **Note for Hope:** the `notes` field name must match whatever the session record stores. Confirm before implementing.

---

## `POST /verification/submissions`

Submits a coach's evidence links for AI-organised review. Returns a structured summary for a **human reviewer** to act on. The AI never marks anyone Verified.

### Request body

```json
{
  "coachId": "coach-001",
  "links": [
    {
      "type": "tournament",
      "url": "https://start.gg/tournament/ke-nationals-2025",
      "description": "Kenya national Rocket League championship, 2025 — finalist"
    },
    {
      "type": "video",
      "url": "https://youtube.com/watch?v=abc123",
      "description": "Coaching session highlight reel"
    }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `coachId` | string | yes | Coach being reviewed |
| `links` | array | yes | Evidence links with type, url, description |
| `links[].type` | `"ballchasing_replay"` \| `"video"` \| `"tournament"` | yes | |
| `links[].url` | string | yes | Publicly accessible URL |
| `links[].description` | string | yes | What the coach says this link proves |

### Response — `200 OK`

```json
{
  "claims": [
    "Ex-national squad, Rocket League",
    "6 community endorsements"
  ],
  "sources": [
    {
      "type": "tournament",
      "url": "https://start.gg/tournament/ke-nationals-2025",
      "description": "Kenya national Rocket League championship, 2025 — finalist"
    }
  ],
  "gaps": [],
  "redFlags": [],
  "summary": "Coach Dani K. has submitted verifiable evidence of national-level play and community endorsements. No gaps or red flags identified. Ready for human review."
}
```

| Field | Type | Notes |
|-------|------|-------|
| `claims` | string[] | What the evidence claims to prove |
| `sources` | array | Evidence items that support the claims |
| `gaps` | string[] | Missing evidence a reviewer should ask for |
| `redFlags` | string[] | Anything suspicious flagged for human attention |
| `summary` | string | 2–3 sentence paragraph for the reviewer |

> **UI copy requirement for Reberatha:** The verification review queue screen must include the text: **"A person reviews every coach before they are verified."** This must be visible before the reviewer sees the AI summary.

---

## Demo auth header

All endpoints read the header `X-Demo-User` to identify the persona. No real login is needed for the demo.

| Value | Persona |
|-------|---------|
| `gamer` | Player browsing coaches |
| `coach` | Coach viewing their dashboard |
| `team_admin` | Team admin booking and confirming sessions |
| `reviewer` | Human reviewer on the verification queue |
