// src/api.js — the ONLY file that talks to the backend.
// When VITE_USE_MOCK=true (default) every function returns shaped seed data.
// When false it calls VITE_API_URL with the X-Demo-User header.

import * as seed from './mock/seed.js'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getPersona() {
  return localStorage.getItem('c2e_persona') || 'gamer'
}

async function request(method, path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Demo-User': getPersona(),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return res.json()
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
    return seed.coaches
      .filter((c) => c.game === body.game && c.role === body.role)
      .filter((c) => !body.budgetUsd || c.priceUsd <= body.budgetUsd)
      .sort((a, b) => b.score - a.score)
  }
  return request('POST', '/match', body)
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
  return request('POST', `/payments/orders/${orderId}/capture`)
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
  return request('POST', `/sessions/${sessionId}/feedback`, body)
}

// ─── Verification ─────────────────────────────────────────────────────────────

export async function submitVerification(body) {
  if (USE_MOCK) {
    await delay()
    return seed.reviewQueue[0]
  }
  return request('POST', '/verification/submissions', body)
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
