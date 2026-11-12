// src/auth.js — single place for JWT token storage and user state.
// All api.js live-mode requests read getToken() for the Authorization header.

const TOKEN_KEY = 'c2e_token'
const USER_KEY = 'c2e_user'
const PERSONA_KEY = 'c2e_persona'
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    const user = raw ? JSON.parse(raw) : null
    // The API sends lowercase roles ("coach"); the UI compares "COACH".
    return user ? { ...user, role: String(user.role || '').toUpperCase() } : null
  } catch {
    return null
  }
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return !!getToken()
}

// ─── Roles ────────────────────────────────────────────────────────────────────
// Live mode: the logged-in user's role. Mock mode: the demo persona switcher.
const PERSONA_ROLE = { gamer: 'PLAYER', coach: 'COACH', team_admin: 'PLAYER', reviewer: 'ADMIN' }

export function getPersona() {
  return localStorage.getItem(PERSONA_KEY) || 'gamer'
}

export function setPersona(persona) {
  localStorage.setItem(PERSONA_KEY, persona)
  window.dispatchEvent(new Event('c2e-persona'))
}

export function currentRole() {
  if (USE_MOCK) return PERSONA_ROLE[getPersona()] || 'PLAYER'
  return getUser()?.role || null
}
