// All demo data from the SightCoach build-pack.
// Shaped exactly like the API contract (docs/shapes.md).
// Used by src/api.js when VITE_USE_MOCK=true.

const NOW = new Date()
const EXPIRES_AT = new Date(NOW.getTime() + 15 * 60 * 1000).toISOString()

export const coaches = [
  {
    coachId: 'coach-001',
    name: 'Dani K.',
    verified: true,
    endorsementCount: 6,
    priceUsd: 30,
    game: 'rocket_league',
    role: 'forward',
    score: 92,
    reason:
      'Verified Rocket League coach with 6 community endorsements, within your $200 budget and available this week.',
    reasonSource: 'ai',
    bestMatch: true,
    bio: 'Ex-national squad Rocket League player turned full-time coach. Specialises in rotation mechanics, boost management and team comms.',
    paypalEmail: 'dani.k@sandbox.example',
    endorsements: [
      { community: 'Nairobi RL Community', date: '2026-09-10' },
      { community: 'East Africa Esports', date: '2026-09-22' },
      { community: 'BARBAH Games', date: '2026-10-01' },
      { community: 'KE Nationals Circuit', date: '2026-10-05' },
      { community: 'Rocket League Africa', date: '2026-10-14' },
      { community: 'PlayEconomy Hub', date: '2026-11-01' },
    ],
    evidence: [
      {
        id: 'ce-001',
        type: 'tournament',
        url: 'https://start.gg/tournament/ke-nationals-2025',
        description: 'Kenya national Rocket League championship, 2025 — finalist',
      },
      {
        id: 'ce-002',
        type: 'video',
        url: 'https://youtube.com/watch?v=demo123',
        description: 'Coaching session highlight reel',
      },
    ],
    packages: [
      {
        id: 'pkg-001',
        label: '5-session pack',
        sessions: 5,
        pricePerSession: 30,
        subtotal: 150.0,
        platformFeePct: 8,
        platformFee: 12.0,
        total: 162.0,
        currency: 'USD',
      },
    ],
    hoursLogged: 28,
    totalHours: 40,
    points: 280,
    bonusPct: 7,
    balance: 420.0,
  },
  {
    coachId: 'coach-002',
    name: 'Alex M.',
    verified: false,
    endorsementCount: 2,
    priceUsd: 25,
    game: 'rocket_league',
    role: 'forward',
    score: 54,
    reason: 'Rocket League forward coach within budget, not yet verified.',
    reasonSource: 'rule',
    bestMatch: false,
    bio: 'Competitive Rocket League player with experience in Diamond–Champ lobbies. Focuses on mechanical improvement.',
    paypalEmail: 'alex.m@sandbox.example',
    endorsements: [
      { community: 'Nairobi RL Community', date: '2026-10-20' },
      { community: 'PlayEconomy Hub', date: '2026-11-02' },
    ],
    evidence: [],
    packages: [
      {
        id: 'pkg-002',
        label: '5-session pack',
        sessions: 5,
        pricePerSession: 25,
        subtotal: 125.0,
        platformFeePct: 8,
        platformFee: 10.0,
        total: 135.0,
        currency: 'USD',
      },
    ],
    hoursLogged: 0,
    totalHours: 0,
    points: 0,
    bonusPct: 0,
    balance: 0,
  },
]

export const quote = {
  id: 'quote-001',
  packageId: 'pkg-001',
  amountUsd: 162.0,
  amountKes: 20898,
  rate: 129.0,
  rateLabel: '1 USD = 129.00 KES (est.)',
  fxSavingNote: 'Est. saving vs direct PayPal conversion: about KES 600 (estimate)',
  expiresAt: EXPIRES_AT,
}

// orderCapture — shaped exactly like POST /payments/orders/{id}/capture response.
// snake_case keys match the backend; camelCase aliases are added for the mock
// Confirmation screen until Reberatha remaps them.
export const orderCapture = {
  // ── Backend field names (snake_case) ──────────────────────────────────────
  receipt_ref:     'C2E-48213',
  coach_name:      'Dani K.',
  paid_with:       'mpesa_sim',
  package_label:   '5-session pack',
  platform_fee:    '12.00',
  total_paid_kes:  '20898',
  total_paid_usd:  '162.00',
  currency:        'KES',
  rate_used:       '1 USD = 129.00 KES (est.)',
  booked_sessions: [
    { id: 's-1', label: 'Session 1 of 5', starts_at: '2026-11-12T14:00:00Z' },
    { id: 's-2', label: 'Session 2 of 5', starts_at: '2026-11-14T14:00:00Z' },
    { id: 's-3', label: 'Session 3 of 5', starts_at: '2026-11-19T14:00:00Z' },
    { id: 's-4', label: 'Session 4 of 5', starts_at: null },
    { id: 's-5', label: 'Session 5 of 5', starts_at: null },
  ],
  order_id:  'MOCK-ORDER-001',
  status:    'COMPLETED (simulated M-Pesa demo)',
  simulated: true,
  // ── camelCase aliases — remove once Reberatha remaps in Confirmation.jsx ──
  receiptRef:    'C2E-48213',
  coachName:     'Dani K.',
  paidWith:      'mpesa_sim',
  packageLabel:  '5-session pack',
  platformFee:   12.0,
  totalPaidKes:  20898,
  totalPaidUsd:  162.0,
  rateUsed:      '1 USD = 129.00 KES (est.)',
  bookedSessions: [
    { id: 's-1', label: 'Session 1 of 5', startsAt: '2026-11-12T14:00:00Z' },
    { id: 's-2', label: 'Session 2 of 5', startsAt: '2026-11-14T14:00:00Z' },
    { id: 's-3', label: 'Session 3 of 5', startsAt: '2026-11-19T14:00:00Z' },
    { id: 's-4', label: 'Session 4 of 5', startsAt: null },
    { id: 's-5', label: 'Session 5 of 5', startsAt: null },
  ],
}

export const coachDashboard = {
  coachId: 'coach-001',
  teamName: 'Nairobi Drift',
  balance: 420.0,
  hoursLogged: 28,
  totalHours: 40,
  points: 280,
  bonusPct: 7,
  activityFeed: [
    { sessionId: 's-1', label: 'Gameplay assessment', status: 'Confirmed', date: '2026-11-12' },
    { sessionId: 's-2', label: 'Rotations and positioning', status: 'Paid', date: '2026-11-14' },
    { sessionId: 's-3', label: 'Team comms review', status: 'Scheduled', date: '2026-11-19' },
    { sessionId: 's-4', label: 'TBD', status: 'Pending win', date: null },
  ],
}

export const passport = {
  player: { id: 'player-001', name: 'Demo Player', game: 'rocket_league' },
  rank: 'Diamond II',
  replayStats: {
    matches: 42,
    goals: 87,
    saves: 61,
    shots: 204,
    boostPerMinute: 312.4,
  },
  evidence: [
    {
      id: 'ev-001',
      type: 'ballchasing_replay',
      url: 'https://ballchasing.com/replay/abc123',
      addedAt: '2026-10-15T10:00:00Z',
    },
    {
      id: 'ev-002',
      type: 'tournament',
      url: 'https://start.gg/tournament/nairobi-rl-open',
      addedAt: '2026-10-20T09:30:00Z',
    },
  ],
  feedback: [
    {
      sessionId: 'session-001',
      coachName: 'Dani K.',
      date: '2026-11-12T14:00:00Z',
      strengths: ['Strong aerial control', 'Good boost awareness'],
      focusAreas: ['Shadow defence positioning', 'Rotation recovery after boost pad'],
      nextGoals: [
        'Practice 50/50 challenges in freeplay',
        'Review shadow defence replay clips',
      ],
    },
  ],
}

export const reviewQueue = [
  {
    id: 'sub-001',
    coachId: 'coach-001',
    coachName: 'Dani K.',
    submittedAt: '2026-11-05T08:00:00Z',
    status: 'pending',
    claims: ['Ex-national squad, Rocket League', '6 community endorsements'],
    sources: [
      {
        type: 'tournament',
        url: 'https://start.gg/tournament/ke-nationals-2025',
        description: 'Kenya national Rocket League championship, 2025 — finalist',
      },
    ],
    gaps: [],
    redFlags: [],
    summary:
      'Coach Dani K. has submitted verifiable evidence of national-level play and community endorsements. No gaps or red flags identified. Ready for human review.',
  },
]
