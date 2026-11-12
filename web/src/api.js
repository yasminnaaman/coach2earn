// src/api.js — the ONLY file that talks to the backend.
// When VITE_USE_MOCK=true (default) every function returns shaped seed data.
// When false it calls VITE_API_URL with real JWT auth against Hope's FastAPI backend.

import * as seed from './mock/seed.js'
import { getToken, setToken, setUser, clearAuth } from './auth.js'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// Hope's backend mounts all routes under /api/v1
const API = `${BASE_URL}/api/v1`

async function request(method, path, body, { auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = `Request failed: ${res.status}`
    try {
      const json = await res.json()
      detail = json?.detail || JSON.stringify(json) || detail
    } catch {
      detail = (await res.text()) || detail
    }
    throw new Error(detail)
  }
  // 204 No Content — return null
  if (res.status === 204) return null
  return res.json()
}

// ─── Live-mode shape adapters ────────────────────────────────────────────────
// The FastAPI backend returns snake_case resources; the screens were built
// against the camelCase contract in docs/shapes.md. These helpers translate.

const KES_PER_USD = 129
// Rough USD value of other package currencies — display estimates only.
const USD_PER_UNIT = { USD: 1, GBP: 1.27, EUR: 1.08, KES: 1 / KES_PER_USD }

const num = (v) => (v === null || v === undefined || v === '' ? 0 : Number(v))
const round2 = (v) => Math.round(v * 100) / 100
const toUsd = (amount, currency) => round2(num(amount) * (USD_PER_UNIT[currency] ?? 1))

function mapPackage(p) {
  const total = num(p.price_amount)
  const sessions = p.session_limit || 1
  return {
    id: p.id,
    coachId: p.coach_profile_id,
    label: p.title,
    description: p.description,
    sessions,
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

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function register(body) {
  // body: { email, password, date_of_birth, guardian_name?, guardian_email? }
  if (USE_MOCK) {
    await delay()
    return { id: 'mock-user-001', email: body.email, role: 'PLAYER', account_status: 'ACTIVE' }
  }
  return normalizeUser(await request('POST', '/auth/register', body, { auth: false }))
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
  // Fetch the real user profile immediately after login
  const user = normalizeUser(await request('GET', '/auth/me'))
  setUser(user)
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

// Simulate async delay in mock mode so loading states are visible
function delay(ms = 400) {
  return new Promise((r) => setTimeout(r, ms))
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
    // Only filter by game if one was selected
    if (body.game) list = list.filter((c) => c.game === body.game)
    // Only filter by role if one was selected
    if (body.role) list = list.filter((c) => c.role === body.role)
    // Only filter by budget if one was provided and is meaningful
    if (body.budgetUsd && body.budgetUsd < 999) {
      list = list.filter((c) => c.priceUsd <= body.budgetUsd)
    }
    // If nothing matches, return all coaches rather than an empty list
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
  if (USE_MOCK) return getCoach('coach-001')
  const pkg = await request('GET', `/packages/${packageId}`, undefined, { auth: false })
  return getCoach(pkg.coach_profile_id)
}

// ─── Quotes ──────────────────────────────────────────────────────────────────

export async function createQuote(body) {
  // body: { packageId, paymentMethod }
  if (USE_MOCK) {
    await delay()
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString()
    const isKes = body.paymentMethod !== 'paypal_balance'
    return {
      ...seed.quote,
      expiresAt,
      paymentMethod: body.paymentMethod,
      amountDisplay: isKes
        ? { currency: 'KES', amount: seed.quote.amountKes, label: `KES ${seed.quote.amountKes.toLocaleString()}` }
        : { currency: 'USD', amount: seed.quote.amountUsd, label: `USD ${seed.quote.amountUsd.toFixed(2)}` },
    }
  }
  // Brian's payments module mounts the quote endpoint under /payments/quotes
  const q = await request('POST', '/payments/quotes', body)
  const amountUsd = toUsd(q.total_usd, 'USD')
  const amountKes = Math.round(amountUsd * KES_PER_USD)
  const isKes = body.paymentMethod !== 'paypal_balance'
  return {
    id: q.quote_id,
    packageId: q.package_id,
    amountUsd,
    amountKes,
    rate: KES_PER_USD,
    rateLabel: `1 USD = ${KES_PER_USD.toFixed(2)} KES (est.)`,
    expiresAt: q.expires_at && !/[zZ]|[+-]\d\d:?\d\d$/.test(q.expires_at) ? `${q.expires_at}Z` : q.expires_at,
    paymentMethod: body.paymentMethod,
    amountDisplay: isKes
      ? { currency: 'KES', amount: amountKes, label: `KES ${amountKes.toLocaleString()}` }
      : { currency: 'USD', amount: amountUsd, label: `USD ${amountUsd.toFixed(2)}` },
  }
}

// ─── Orders / payment ────────────────────────────────────────────────────────

export async function createOrder(body) {
  // body: { quoteId }
  if (USE_MOCK) {
    await delay()
    return {
      orderId: 'MOCK-ORDER-001',
      approvalUrl: `${window.location.origin}/confirmation?mock=1`,
    }
  }
  // body: { quoteId, paymentMethod }
  // There is no payment provider wired into the API yet: accepting the quote
  // creates the order (status pending_payment), then we return to checkout
  // with ?orderId=… which loads the receipt via captureOrder().
  const order = await request('POST', '/orders', { quotation_id: body.quoteId })
  if (body.paymentMethod) sessionStorage.setItem(`c2e_paid_with_${order.id}`, body.paymentMethod)
  return {
    orderId: order.id,
    approvalUrl: `${window.location.pathname}?orderId=${order.id}`,
  }
}

export async function captureOrder(orderId) {
  if (USE_MOCK) {
    await delay()
    return seed.orderCapture
  }
  const order = await request('GET', `/orders/${orderId}`)
  let coachName = 'your coach'
  try {
    const coach = await request('GET', `/coaches/${order.coach_profile_id}`, undefined, { auth: false })
    coachName = coach.name || coachName
  } catch {
    // coach no longer public — keep the generic label
  }
  const paidWith = sessionStorage.getItem(`c2e_paid_with_${order.id}`) || 'mpesa_sim'
  const totalUsd = toUsd(order.price_amount, order.currency)
  return {
    orderId: order.id,
    receiptRef: order.order_reference,
    coachName,
    paidWith,
    packageLabel: order.package_title,
    packageSubtotal: num(order.price_amount),
    platformFee: 0,
    totalPaidKes: Math.round(totalUsd * KES_PER_USD),
    totalPaidUsd: totalUsd,
    currency: paidWith === 'paypal_balance' ? 'USD' : 'KES',
    rateUsed: `1 USD = ${KES_PER_USD.toFixed(2)} KES (est.)`,
    // Sessions are created when the booking is made — until then show slots.
    bookedSessions: Array.from({ length: order.session_limit || 0 }, (_, i) => ({
      id: `${order.id}-${i + 1}`,
      label: `Session ${i + 1}`,
      startsAt: null,
    })),
  }
}

// ─── Sessions ────────────────────────────────────────────────────────────────

// Live sessions are addressed as /bookings/{bookingId}/sessions/{sessionId};
// the screens only know the session id, so look the booking up first.
const SESSION_STATUS_LABEL = {
  scheduled: 'Scheduled',
  confirmed: 'started', // confirmed = in progress (SessionLogging state)
  completed: 'Confirmed',
  cancelled: 'Cancelled',
  disputed: 'Disputed',
}

async function findSession(id) {
  const bookings = await request('GET', '/bookings')
  for (const b of bookings) {
    const s = b.sessions?.find((x) => x.id === id)
    if (s) return { booking: b, session: s }
  }
  throw new Error('Session not found.')
}

async function setSessionStatus(id, status) {
  const { booking } = await findSession(id)
  return request('PATCH', `/bookings/${booking.id}/sessions/${id}/status`, { status })
}

// Returns null in mock mode — SessionLogging falls back to its demo sessions.
export async function getSession(id) {
  if (USE_MOCK) return null
  const { booking, session } = await findSession(id)
  return {
    id: session.id,
    bookingId: booking.id,
    label: `Session ${session.sequence_number}`,
    status: SESSION_STATUS_LABEL[session.status] || session.status,
    date: session.starts_at ? session.starts_at.slice(0, 10) : null,
    proposedHours: null,
  }
}

export async function scheduleSession(id, body) {
  if (USE_MOCK) {
    await delay()
    return { id, ...body, status: 'scheduled' }
  }
  // Sessions only exist once a paid order has been booked (POST /bookings).
  throw new Error('Sessions can be scheduled once payment is confirmed.')
}

export async function startSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'started' }
  }
  return setSessionStatus(id, 'confirmed')
}

export async function endSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'ended' }
  }
  return setSessionStatus(id, 'completed')
}

export async function confirmSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'confirmed' }
  }
  const { session } = await findSession(id)
  if (session.status === 'scheduled') await setSessionStatus(id, 'confirmed')
  return setSessionStatus(id, 'completed')
}

export async function disputeSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'disputed' }
  }
  // The API has no dispute transition yet.
  throw new Error('Disputes are not supported by the API yet.')
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
    return seed.passport
  }
  return request('GET', `/players/${playerId}/passport`)
}

export async function addEvidence(playerId, body) {
  if (USE_MOCK) {
    await delay()
    const newItem = {
      id: `ev-${Date.now()}`,
      type: body.type,
      url: body.url,
      addedAt: new Date().toISOString(),
    }
    return [...seed.passport.evidence, newItem]
  }
  return request('POST', `/players/${playerId}/evidence`, body)
}

export async function submitFeedback(sessionId, body) {
  if (USE_MOCK) {
    await delay()
    return {
      strengths: ['Solid aerial control', 'Improving boost management'],
      focusAreas: ['Shadow defence positioning'],
      nextGoals: ['Practice 50/50 challenges in freeplay', 'Review shadow defence replay clips'],
    }
  }
  return request('POST', `/ai/sessions/${sessionId}/feedback`, body)
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
    return seed.reviewQueue
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
    submittedAt: q.created_at,
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

export async function approveSubmission(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'approved' }
  }
  return request('POST', `/admin/qualifications/${id}/review`, { status: 'approved' })
}

export async function rejectSubmission(id, body) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'rejected' }
  }
  return request('POST', `/admin/qualifications/${id}/review`, {
    status: 'rejected',
    review_notes: body?.reason || null,
  })
}

// ─── Consent ──────────────────────────────────────────────────────────────────

export async function submitConsent(body) {
  if (USE_MOCK) {
    await delay()
    return { success: true }
  }
  return request('POST', '/auth/consents', body)
}
