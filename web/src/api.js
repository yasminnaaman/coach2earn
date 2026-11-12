// src/api.js — the ONLY file that talks to the backend.
// When VITE_USE_MOCK=true every function works against an in-memory demo store.
// When false it calls VITE_API_URL with real JWT auth against the FastAPI backend.

import * as seed from './mock/seed.js'
import { getToken, setToken, setUser, clearAuth, getUser } from './auth.js'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// The backend mounts all routes under /api/v1
const API = `${BASE_URL}/api/v1`

function formatDetail(detail, status) {
  if (!detail) return `Request failed (${status})`
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => d?.msg || JSON.stringify(d)).join('; ')
  }
  return JSON.stringify(detail)
}

async function request(method, path, body, { auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = auth ? getToken() : null
  if (token) headers['Authorization'] = `Bearer ${token}`
  let res
  try {
    res = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Cannot reach the server. Check your connection — the API may be waking up, try again in a moment.')
  }
  const text = await res.text()
  let json = null
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    json = null
  }
  if (!res.ok) {
    // Expired or invalid login — clear it so the app sends the user to log in.
    if (res.status === 401 && token) {
      clearAuth()
      window.dispatchEvent(new Event('c2e-auth-expired'))
      throw new Error('Your session has expired. Please log in again.')
    }
    throw new Error(formatDetail(json?.detail ?? (text || null), res.status))
  }
  return json
}

// Simulate async delay in mock mode so loading states are visible
function delay(ms = 350) {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── Live-mode shape adapters ────────────────────────────────────────────────
// The FastAPI backend returns snake_case resources; the screens use camelCase.

const KES_PER_USD = 129
// Rough USD value of other package currencies — display estimates only.
const USD_PER_UNIT = { USD: 1, GBP: 1.27, EUR: 1.08, KES: 1 / KES_PER_USD }

const num = (v) => (v === null || v === undefined || v === '' ? 0 : Number(v))
const round2 = (v) => Math.round(v * 100) / 100
const toUsd = (amount, currency) => round2(num(amount) * (USD_PER_UNIT[currency] ?? 1))
const asUtc = (iso) => (iso && !/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? `${iso}Z` : iso)

function mapPackage(p) {
  const total = num(p.price_amount)
  const sessions = p.session_limit || 1
  return {
    id: p.id,
    coachId: p.coach_profile_id,
    label: p.title,
    description: p.description,
    sessions,
    durationDays: p.duration_days,
    pricePerSession: round2(total / sessions),
    subtotal: total,
    // The backend charges the package price as-is (no separate platform fee).
    platformFeePct: 0,
    platformFee: 0,
    total,
    currency: p.currency,
  }
}

function mapCoach(c, rawPackages = []) {
  const packages = rawPackages
    .filter((p) => p.is_active !== false)
    .map(mapPackage)
    .sort((a, b) => a.pricePerSession - b.pricePerSession)
  const cheapest = packages.find((p) => p.currency === 'USD') || packages[0]
  const game = c.specialisations?.find((s) => s.category === 'game')
  return {
    coachId: c.id,
    name: c.name || 'Coach',
    verified: !!c.verified,
    endorsementCount: 0, // endorsements are not modelled in the API yet
    priceUsd: cheapest ? toUsd(cheapest.pricePerSession, cheapest.currency) : 0,
    game: game ? game.slug.replace(/-/g, '_') : '',
    // No role field in the API yet — show experience in the role slot instead.
    role: `${c.experience_years ?? 0} yrs coaching`,
    experienceYears: c.experience_years ?? 0,
    goals: c.coaching_goals || '',
    score: null,
    reason: c.coaching_goals || '',
    reasonSource: 'rule',
    bestMatch: false,
    bio: c.professional_bio,
    endorsements: [],
    evidence: [],
    packages,
  }
}

async function packagesByCoach() {
  const all = await request('GET', '/packages', undefined, { auth: false })
  const byCoach = {}
  for (const p of all) (byCoach[p.coach_profile_id] ||= []).push(p)
  return byCoach
}

function normalizeUser(user) {
  // Backend roles are lowercase ("coach"); the UI compares against "COACH".
  return user ? { ...user, role: String(user.role || '').toUpperCase() } : user
}

function mapPerson(p) {
  return p ? { userId: p.user_id, name: p.name, coachId: p.coach_profile_id || null } : null
}

function mapSession(s) {
  return {
    id: s.id,
    bookingId: s.booking_id,
    orderId: s.order_id,
    orderRef: s.order_reference,
    packageTitle: s.package_title,
    seq: s.sequence_number,
    label: s.label,
    startsAt: asUtc(s.starts_at),
    endsAt: asUtc(s.ends_at),
    status: s.status, // scheduled | confirmed (in progress) | completed | disputed | cancelled
    notes: s.coach_notes,
    playerConfirmed: !!s.player_confirmed,
    coach: mapPerson(s.coach),
    player: mapPerson(s.player),
  }
}

function mapOrder(o) {
  return {
    orderId: o.order_id,
    orderRef: o.order_reference,
    status: o.status,
    packageTitle: o.package_title,
    price: num(o.price_amount),
    currency: o.currency,
    sessionLimit: o.session_limit,
    remaining: o.remaining_to_schedule,
    createdAt: asUtc(o.created_at),
    coach: mapPerson(o.coach),
    player: mapPerson(o.player),
    sessions: (o.sessions || []).map(mapSession),
  }
}

// ─── Mock store (VITE_USE_MOCK=true) ─────────────────────────────────────────
// A tiny in-memory backend so every button works in the offline demo.

const inDays = (d, h = 18) => {
  const t = new Date()
  t.setDate(t.getDate() + d)
  t.setHours(h, 0, 0, 0)
  return t.toISOString()
}
const MOCK_COACH = { userId: 'coach-user-001', name: 'Dani K.', coachId: 'coach-001' }
const MOCK_PLAYER = { userId: 'mock-user-001', name: 'Demo Player', coachId: null }

function mockSession(orderId, seq, status, startsAt, extra = {}) {
  return {
    id: `s-${orderId}-${seq}`, bookingId: `b-${orderId}`, orderId, orderRef: 'C2E-48213',
    packageTitle: '5-session pack', seq, label: `Session ${seq}`, startsAt,
    endsAt: startsAt ? new Date(new Date(startsAt).getTime() + 3600e3).toISOString() : null,
    status, notes: null, playerConfirmed: false, coach: MOCK_COACH, player: MOCK_PLAYER, ...extra,
  }
}

const mockStore = {
  orders: [
    {
      orderId: 'MOCK-ORDER-001', orderRef: 'C2E-48213', status: 'confirmed', packageTitle: '5-session pack',
      price: 162, currency: 'USD', sessionLimit: 5, remaining: 2, createdAt: inDays(-4),
      coach: MOCK_COACH, player: MOCK_PLAYER,
      sessions: [
        mockSession('MOCK-ORDER-001', 1, 'completed', inDays(-1), {
          notes: '+ Solid aerial control\n+ Improving boost management\n- Shadow defence positioning\n> Practice 50/50 challenges in freeplay',
        }),
        mockSession('MOCK-ORDER-001', 2, 'scheduled', inDays(2)),
        mockSession('MOCK-ORDER-001', 3, 'scheduled', inDays(5)),
      ],
    },
  ],
  messages: [
    { id: 'm1', from: MOCK_PLAYER.userId, to: MOCK_COACH.userId, body: 'Hi Dani! Looking forward to our sessions.', createdAt: inDays(-3, 10) },
    { id: 'm2', from: MOCK_COACH.userId, to: MOCK_PLAYER.userId, body: 'Welcome! Upload a couple of replays to your passport before we start.', createdAt: inDays(-3, 12) },
  ],
  evidence: [...seed.passport.evidence],
  reviewQueue: seed.reviewQueue.map((q) => ({ ...q })),
}

function mockFindSession(id) {
  for (const o of mockStore.orders) {
    const s = o.sessions.find((x) => x.id === id)
    if (s) return { order: o, session: s }
  }
  throw new Error('Session not found.')
}

function mockRecount(order) {
  const live = order.sessions.filter((s) => s.status !== 'cancelled')
  order.remaining = Math.max(0, order.sessionLimit - live.length)
}

function mockMe() {
  const role = getUser()?.role
  const persona = localStorage.getItem('c2e_persona')
  return persona === 'coach' || role === 'COACH' ? MOCK_COACH : MOCK_PLAYER
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function register(body) {
  // body: { email, password, date_of_birth, guardian_name?, guardian_email? }
  if (USE_MOCK) {
    await delay()
    return { id: 'mock-user-001', email: body.email, role: 'PLAYER', account_status: 'ACTIVE' }
  }
  return normalizeUser(await request('POST', '/auth/register', body, { auth: false }))
}

// Players need a profile before they can request quotes — create an empty one.
async function ensurePlayerProfile() {
  try {
    await request('GET', '/profiles/player')
  } catch {
    try {
      await request('POST', '/profiles/player', {})
    } catch {
      // profile may already exist or the user is not a player — ignore
    }
  }
}

export async function login(body) {
  // body: { email, password }
  if (USE_MOCK) {
    await delay()
    const mockUser = { id: 'mock-user-001', email: body.email, role: 'PLAYER', account_status: 'ACTIVE' }
    setToken('mock-token')
    setUser(mockUser)
    return mockUser
  }
  const token = await request('POST', '/auth/login', body, { auth: false })
  setToken(token.access_token)
  const user = normalizeUser(await request('GET', '/auth/me'))
  setUser(user)
  if (user.role === 'PLAYER') await ensurePlayerProfile()
  return user
}

export async function logout() {
  clearAuth()
}

export async function getCurrentUser() {
  if (USE_MOCK) {
    await delay(100)
    return { id: 'mock-user-001', email: 'demo@SightCoach.com', role: 'PLAYER', account_status: 'ACTIVE' }
  }
  return normalizeUser(await request('GET', '/auth/me'))
}

// ─── Coach matching & discovery ──────────────────────────────────────────────

export async function getCoaches(filters = {}) {
  if (USE_MOCK) {
    await delay()
    let list = seed.coaches
    if (filters.game) list = list.filter((c) => c.game === filters.game)
    if (filters.role) list = list.filter((c) => c.role === filters.role)
    if (filters.budgetUsd) list = list.filter((c) => c.priceUsd <= Number(filters.budgetUsd))
    return list
  }
  // GET /coaches only understands goal + budget; game/role go through /ai/match.
  const query = {}
  if (filters.goal) query.goal = filters.goal
  if (filters.budgetUsd) {
    query.budget_amount = filters.budgetUsd
    query.budget_currency = 'USD'
  }
  const params = new URLSearchParams(query).toString()
  const [list, byCoach] = await Promise.all([
    request('GET', `/coaches${params ? `?${params}` : ''}`, undefined, { auth: false }),
    packagesByCoach(),
  ])
  return list.map((c) => mapCoach(c, byCoach[c.id]))
}

export async function matchCoaches(body) {
  if (USE_MOCK) {
    await delay()
    let list = [...seed.coaches]
    if (body.game) list = list.filter((c) => c.game === body.game)
    if (body.role) list = list.filter((c) => c.role === body.role)
    if (body.budgetUsd && body.budgetUsd < 999) {
      list = list.filter((c) => c.priceUsd <= body.budgetUsd)
    }
    if (list.length === 0) list = [...seed.coaches]
    return list.sort((a, b) => b.score - a.score)
  }
  return request('POST', '/ai/match', body, { auth: false })
}

export async function getCoach(id) {
  if (USE_MOCK) {
    await delay()
    const coach = seed.coaches.find((c) => c.coachId === id)
    if (!coach) throw new Error('Coach not found.')
    return coach
  }
  const [coach, byCoach] = await Promise.all([
    request('GET', `/coaches/${id}`, undefined, { auth: false }),
    packagesByCoach(),
  ])
  return mapCoach(coach, byCoach[coach.id])
}

// Checkout only knows the package id — resolve the coach who owns it.
export async function getCoachForPackage(packageId) {
  if (USE_MOCK) {
    const owner = seed.coaches.find((c) => c.packages.some((p) => p.id === packageId))
    return getCoach(owner?.coachId || 'coach-001')
  }
  const pkg = await request('GET', `/packages/${packageId}`, undefined, { auth: false })
  return getCoach(pkg.coach_profile_id)
}

// ─── Quotes ──────────────────────────────────────────────────────────────────

export async function createQuote(body) {
  // body: { packageId, paymentMethod }
  const isKes = body.paymentMethod !== 'paypal_balance'
  if (USE_MOCK) {
    await delay()
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString()
    return {
      ...seed.quote,
      packageId: body.packageId,
      expiresAt,
      paymentMethod: body.paymentMethod,
      amountDisplay: isKes
        ? { currency: 'KES', amount: seed.quote.amountKes, label: `KES ${seed.quote.amountKes.toLocaleString()}` }
        : { currency: 'USD', amount: seed.quote.amountUsd, label: `USD ${seed.quote.amountUsd.toFixed(2)}` },
    }
  }
  let q
  try {
    q = await request('POST', '/quotes', body)
  } catch (e) {
    // Accounts created before profiles were automatic — create one and retry.
    if (!/player profile/i.test(e.message)) throw e
    await ensurePlayerProfile()
    q = await request('POST', '/quotes', body)
  }
  const amountUsd = toUsd(q.price_amount, q.currency)
  const amountKes = Math.round(amountUsd * KES_PER_USD)
  return {
    // Core quotation (POST /quotes) — its id is what POST /orders accepts.
    id: q.id,
    packageId: q.package_id,
    amountUsd,
    amountKes,
    rate: KES_PER_USD,
    rateLabel: `1 USD = ${KES_PER_USD.toFixed(2)} KES (est.)`,
    expiresAt: asUtc(q.expires_at),
    paymentMethod: body.paymentMethod,
    amountDisplay: isKes
      ? { currency: 'KES', amount: amountKes, label: `KES ${amountKes.toLocaleString()}` }
      : { currency: 'USD', amount: amountUsd, label: `USD ${amountUsd.toFixed(2)}` },
  }
}

// ─── Orders / payment (payments are simulated — no money moves) ─────────────

export async function createOrder(body) {
  // body: { quoteId, paymentMethod }
  if (USE_MOCK) {
    await delay()
    const orderId = `MOCK-ORDER-${Date.now()}`
    mockStore.orders.unshift({
      orderId, orderRef: `C2E-${String(Date.now()).slice(-5)}`, status: 'pending_payment',
      packageTitle: '5-session pack', price: 162, currency: 'USD', sessionLimit: 5, remaining: 5,
      createdAt: new Date().toISOString(), coach: MOCK_COACH, player: MOCK_PLAYER, sessions: [],
    })
    if (body.paymentMethod) sessionStorage.setItem(`c2e_paid_with_${orderId}`, body.paymentMethod)
    return { orderId }
  }
  const order = await request('POST', '/orders', { quotation_id: body.quoteId })
  if (body.paymentMethod) sessionStorage.setItem(`c2e_paid_with_${order.id}`, body.paymentMethod)
  return { orderId: order.id }
}

export async function payOrder(orderId, { paymentMethod, phone } = {}) {
  if (USE_MOCK) {
    await delay(1200)
    const order = mockStore.orders.find((o) => o.orderId === orderId)
    if (order) order.status = 'confirmed'
    return order
  }
  const order = await request('POST', `/orders/${orderId}/pay`, {
    payment_method: paymentMethod || 'mpesa_sim',
    phone: phone || null,
  })
  return mapOrder(order)
}

export async function getMyOrders() {
  if (USE_MOCK) {
    await delay()
    return mockStore.orders.filter((o) => o.status !== 'pending_payment').map((o) => ({ ...o, sessions: [...o.sessions] }))
  }
  return (await request('GET', '/me/orders')).map(mapOrder)
}

export async function getOrder(orderId) {
  if (USE_MOCK) {
    await delay()
    const order = mockStore.orders.find((o) => o.orderId === orderId) || mockStore.orders[0]
    return { ...order, sessions: [...order.sessions] }
  }
  return mapOrder(await request('GET', `/me/orders/${orderId}`))
}

export async function scheduleOrderSessions(orderId, startsAtList) {
  if (USE_MOCK) {
    await delay()
    const order = mockStore.orders.find((o) => o.orderId === orderId)
    if (!order) throw new Error('Order not found.')
    if (startsAtList.length > order.remaining) throw new Error(`Only ${order.remaining} session(s) left to schedule.`)
    let seq = Math.max(0, ...order.sessions.map((s) => s.seq))
    for (const iso of startsAtList) order.sessions.push(mockSession(order.orderId, ++seq, 'scheduled', iso))
    mockRecount(order)
    return { ...order, sessions: [...order.sessions] }
  }
  return mapOrder(await request('POST', `/orders/${orderId}/sessions`, { starts_at: startsAtList }))
}

// Receipt shown on the confirmation screen.
export async function captureOrder(orderId) {
  const order = await getOrder(orderId)
  const paidWith = sessionStorage.getItem(`c2e_paid_with_${order.orderId}`) || 'mpesa_sim'
  const totalUsd = toUsd(order.price, order.currency)
  return {
    ...order,
    receiptRef: order.orderRef,
    coachName: order.coach?.name || 'your coach',
    paidWith,
    packageLabel: order.packageTitle,
    totalPaidKes: Math.round(totalUsd * KES_PER_USD),
    totalPaidUsd: totalUsd,
    currencyPaid: paidWith === 'paypal_balance' ? 'USD' : 'KES',
    rateUsed: `1 USD = ${KES_PER_USD.toFixed(2)} KES (est.)`,
  }
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export async function getSession(id) {
  if (USE_MOCK) {
    await delay()
    try {
      return { ...mockFindSession(id).session }
    } catch {
      // Demo links such as /sessions/s-3 fall back to the first demo session.
      return { ...mockStore.orders[0].sessions[1] }
    }
  }
  return mapSession(await request('GET', `/sessions/${id}`))
}

async function mockTransition(id, from, to, extra = {}) {
  await delay()
  const { order, session } = mockFindSession(id)
  if (!from.includes(session.status)) throw new Error(`Session is ${session.status}.`)
  Object.assign(session, { status: to }, extra)
  mockRecount(order)
  return { ...session }
}

export async function startSession(id) {
  if (USE_MOCK) return mockTransition(id, ['scheduled'], 'confirmed')
  return mapSession(await request('POST', `/sessions/${id}/start`))
}

export async function endSession(id, notes = '') {
  if (USE_MOCK) return mockTransition(id, ['scheduled', 'confirmed'], 'completed', notes ? { notes } : {})
  return mapSession(await request('POST', `/sessions/${id}/complete`, { coach_notes: notes || null }))
}

export async function confirmSession(id) {
  if (USE_MOCK) return mockTransition(id, ['completed', 'disputed'], 'completed', { playerConfirmed: true })
  return mapSession(await request('POST', `/sessions/${id}/confirm`))
}

export async function disputeSession(id, reason = 'No reason given') {
  if (USE_MOCK) return mockTransition(id, ['completed'], 'disputed')
  return mapSession(await request('POST', `/sessions/${id}/dispute`, { reason }))
}

export async function cancelSession(id) {
  if (USE_MOCK) return mockTransition(id, ['scheduled'], 'cancelled')
  return mapSession(await request('POST', `/sessions/${id}/cancel`))
}

// ─── Coach dashboard ─────────────────────────────────────────────────────────

export async function getCoachDashboard() {
  if (USE_MOCK) {
    await delay()
    return seed.coachDashboard
  }
  // JWT token identifies the coach — no ID needed
  return request('GET', '/coaches/me/dashboard')
}

// ─── Skills Passport ─────────────────────────────────────────────────────────

export async function getPassport(playerId) {
  if (USE_MOCK) {
    await delay()
    return { ...seed.passport, evidence: [...mockStore.evidence] }
  }
  return request('GET', `/players/${playerId}/passport`, undefined, { auth: false })
}

export async function addEvidence(playerId, body) {
  if (USE_MOCK) {
    await delay()
    mockStore.evidence.push({ id: `ev-${Date.now()}`, type: body.type, url: body.url, addedAt: new Date().toISOString() })
    return [...mockStore.evidence]
  }
  return request('POST', `/players/${playerId}/evidence`, body)
}

// Structure a completed session's coach notes into strengths / focus / goals.
export async function submitFeedback(sessionId) {
  if (USE_MOCK) {
    await delay()
    return {
      strengths: ['Solid aerial control', 'Improving boost management'],
      focusAreas: ['Shadow defence positioning'],
      nextGoals: ['Practice 50/50 challenges in freeplay', 'Review shadow defence replay clips'],
    }
  }
  return request('POST', `/ai/sessions/${sessionId}/feedback`, {})
}

// ─── Verification ─────────────────────────────────────────────────────────────

export async function submitVerification(body) {
  if (USE_MOCK) {
    await delay()
    return seed.reviewQueue[0]
  }
  return request('POST', '/ai/verification/submissions', body)
}

export async function getReviewQueue() {
  if (USE_MOCK) {
    await delay()
    return mockStore.reviewQueue.filter((q) => q.status === 'pending')
  }
  const quals = await request('GET', '/admin/qualifications?status=pending')
  const names = {}
  await Promise.all(
    [...new Set(quals.map((q) => q.coach_profile_id))].map(async (coachId) => {
      try {
        const c = await request('GET', `/coaches/${coachId}`, undefined, { auth: false })
        names[coachId] = c.name
      } catch {
        names[coachId] = 'Coach (not yet public)'
      }
    })
  )
  return quals.map((q) => ({
    id: q.id,
    coachId: q.coach_profile_id,
    coachName: names[q.coach_profile_id] || 'Coach',
    submittedAt: asUtc(q.created_at),
    status: q.verification_status,
    claims: [q.issuing_organisation ? `${q.title} — ${q.issuing_organisation}` : q.title],
    sources: q.evidence_url
      ? [{ type: 'link', url: q.evidence_url, description: q.issuing_organisation || '' }]
      : [],
    gaps: [
      ...(q.evidence_url ? [] : ['No evidence link supplied']),
      ...(q.credential_reference ? [] : ['No credential reference supplied']),
    ],
    redFlags: [],
    summary: '',
  }))
}

async function reviewSubmission(id, status, notes) {
  if (USE_MOCK) {
    await delay()
    const item = mockStore.reviewQueue.find((q) => q.id === id)
    if (item) item.status = status
    return { id, status }
  }
  return request('POST', `/admin/qualifications/${id}/review`, { status, review_notes: notes || null })
}

export const approveSubmission = (id, body) => reviewSubmission(id, 'approved', body?.notes)
export const rejectSubmission = (id, body) => reviewSubmission(id, 'rejected', body?.reason)
export const requestMoreEvidence = (id, body) => reviewSubmission(id, 'needs_more_evidence', body?.notes)

// ─── Consent ──────────────────────────────────────────────────────────────────

export async function submitConsent(body) {
  if (USE_MOCK) {
    await delay()
    return { success: true }
  }
  return request('POST', '/auth/consents', body)
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export async function getThreads() {
  if (USE_MOCK) {
    await delay()
    const me = mockMe()
    const other = me.userId === MOCK_COACH.userId ? MOCK_PLAYER : MOCK_COACH
    const mine = mockStore.messages.filter((m) => [m.from, m.to].includes(me.userId))
    if (!mine.length) return []
    const last = mine[mine.length - 1]
    return [{ counterpart: other, role: other === MOCK_COACH ? 'coach' : 'player', lastMessage: last.body, lastAt: last.createdAt, unread: 0 }]
  }
  return (await request('GET', '/messages/threads')).map((t) => ({
    counterpart: mapPerson(t.counterpart),
    role: t.counterpart_role,
    lastMessage: t.last_message,
    lastAt: asUtc(t.last_at),
    unread: t.unread,
  }))
}

export async function getThread(userId) {
  if (USE_MOCK) {
    await delay(200)
    const me = mockMe()
    return mockStore.messages
      .filter((m) => [m.from, m.to].includes(me.userId) && [m.from, m.to].includes(userId))
      .map((m) => ({ id: m.id, body: m.body, createdAt: m.createdAt, mine: m.from === me.userId }))
  }
  return (await request('GET', `/messages/with/${userId}`)).map((m) => ({
    id: m.id, body: m.body, createdAt: asUtc(m.created_at), mine: m.mine,
  }))
}

export async function getPerson(userId) {
  if (USE_MOCK) return [MOCK_COACH, MOCK_PLAYER].find((p) => p.userId === userId) || MOCK_COACH
  return mapPerson(await request('GET', `/users/${userId}/card`))
}

// body: { userId } or { coachId }, plus text and optional orderId
export async function sendMessage({ userId, coachId, body, orderId }) {
  if (USE_MOCK) {
    await delay(200)
    const me = mockMe()
    const to = userId || (coachId ? MOCK_COACH.userId : MOCK_COACH.userId)
    const msg = { id: `m-${Date.now()}`, from: me.userId, to, body, createdAt: new Date().toISOString() }
    mockStore.messages.push(msg)
    return { id: msg.id, body, createdAt: msg.createdAt, mine: true, recipientUserId: to }
  }
  const m = await request('POST', '/messages', {
    recipient_user_id: userId || null,
    coach_profile_id: coachId || null,
    order_id: orderId || null,
    body,
  })
  return { id: m.id, body: m.body, createdAt: asUtc(m.created_at), mine: true, recipientUserId: m.recipient_user_id }
}
