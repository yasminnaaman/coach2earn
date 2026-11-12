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

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function register(body) {
  // body: { email, password, date_of_birth, guardian_name?, guardian_email? }
  if (USE_MOCK) {
    await delay()
    return { id: 'mock-user-001', email: body.email, role: 'PLAYER', account_status: 'ACTIVE' }
  }
  return request('POST', '/auth/register', body, { auth: false })
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
  const user = await request('GET', '/auth/me')
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
  return request('GET', '/auth/me')
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
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== '')
  ).toString()
  return request('GET', `/coaches${params ? `?${params}` : ''}`)
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
  return request('POST', '/ai/match', body)
}

export async function getCoach(id) {
  if (USE_MOCK) {
    await delay()
    const coach = seed.coaches.find((c) => c.coachId === id)
    if (!coach) throw new Error('Coach not found.')
    return coach
  }
  return request('GET', `/coaches/${id}`)
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
  return request('POST', '/quotes', body)
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
  return request('POST', '/payments/orders', body)
}

export async function captureOrder(orderId) {
  if (USE_MOCK) {
    await delay()
    return seed.orderCapture
  }
  // Brian's response is snake_case — remap to camelCase for all screens
  const raw = await request('POST', `/payments/orders/${orderId}/capture`)
  return {
    orderId: raw.order_id ?? raw.orderId,
    receiptRef: raw.receipt_ref ?? raw.receiptRef,
    coachName: raw.coach_name ?? raw.coachName,
    paidWith: raw.paid_with ?? raw.paidWith,
    packageLabel: raw.package_label ?? raw.packageLabel,
    packageSubtotal: raw.package_subtotal ?? raw.packageSubtotal,
    platformFee: raw.platform_fee ?? raw.platformFee,
    totalPaidKes: raw.total_paid_kes ?? raw.totalPaidKes,
    totalPaidUsd: raw.total_paid_usd ?? raw.totalPaidUsd,
    currency: raw.currency,
    rateUsed: raw.rate_used ?? raw.rateUsed,
    bookedSessions: (raw.booked_sessions ?? raw.bookedSessions ?? []).map((s) => ({
      id: s.id,
      label: s.label,
      startsAt: s.starts_at ?? s.startsAt ?? null,
    })),
  }
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export async function scheduleSession(id, body) {
  if (USE_MOCK) {
    await delay()
    return { id, ...body, status: 'scheduled' }
  }
  return request('POST', `/sessions/${id}/schedule`, body)
}

export async function startSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'started' }
  }
  return request('POST', `/sessions/${id}/start`)
}

export async function endSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'ended' }
  }
  return request('POST', `/sessions/${id}/end`)
}

export async function confirmSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'confirmed' }
  }
  return request('POST', `/sessions/${id}/confirm`)
}

export async function disputeSession(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'disputed' }
  }
  return request('POST', `/sessions/${id}/dispute`)
}

// ─── Coach dashboard ─────────────────────────────────────────────────────────

export async function getCoachDashboard(id) {
  if (USE_MOCK) {
    await delay()
    return seed.coachDashboard
  }
  return request('GET', `/coaches/${id}/dashboard`)
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
  return request('GET', '/verification/queue')
}

export async function approveSubmission(id) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'approved' }
  }
  return request('POST', `/verification/queue/${id}/approve`)
}

export async function rejectSubmission(id, body) {
  if (USE_MOCK) {
    await delay()
    return { id, status: 'rejected' }
  }
  return request('POST', `/verification/queue/${id}/reject`, body)
}

// ─── Consent ──────────────────────────────────────────────────────────────────

export async function submitConsent(body) {
  if (USE_MOCK) {
    await delay()
    return { success: true }
  }
  return request('POST', '/consents', body)
}
