import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import './App.css'
import { getUser, isLoggedIn, clearAuth } from './auth.js'

// Screens
import Welcome from './screens/Welcome.jsx'
import Login from './screens/Login.jsx'
import Register from './screens/Register.jsx'
import Discover from './screens/Discover.jsx'
import CoachPage from './screens/CoachPage.jsx'
import Checkout from './screens/Checkout.jsx'
import Confirmation from './screens/Confirmation.jsx'
import CoachDashboard from './screens/CoachDashboard.jsx'
import SessionLogging from './screens/SessionLogging.jsx'
import SkillsPassport from './screens/SkillsPassport.jsx'
import ConsentFlow from './screens/ConsentFlow.jsx'
import ReviewQueue from './screens/ReviewQueue.jsx'
import TrustPage from './screens/TrustPage.jsx'

// ─── Protected route wrapper ──────────────────────────────────────────────────
// Redirects to /login if the user is not logged in.
// In mock mode (VITE_USE_MOCK=true) the gate is skipped so the demo flows freely.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

function RequireAuth({ children }) {
  const location = useLocation()
  if (!USE_MOCK && !isLoggedIn()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}

// ─── Header ───────────────────────────────────────────────────────────────────
function Header({ user, onLogout }) {
  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white px-4 py-3">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
        <Link to={user ? '/coaches' : '/'} className="text-base font-semibold text-gray-900 no-underline">
          SightCoach
        </Link>

        <nav className="flex flex-wrap items-center gap-3 text-sm">
          {user ? (
            <>
              {/* Logged-in nav */}
              <Link to="/coaches" className="text-gray-600 hover:text-gray-900">Find coaches</Link>
              {user.role === 'COACH' && (
                <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">Dashboard</Link>
              )}
              {user.role === 'ADMIN' && (
                <Link to="/review" className="text-gray-600 hover:text-gray-900">Review queue</Link>
              )}
              {/* Use real user ID in live mode, fall back to demo ID in mock mode */}
              <Link
                to={`/passport/${user.id || 'player-001'}`}
                className="text-gray-600 hover:text-gray-900"
              >
                My passport
              </Link>
              <span className="text-gray-400">|</span>
              <span className="text-gray-700">{user.email}</span>
              <button
                onClick={onLogout}
                className="rounded-md border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              {/* Logged-out nav */}
              <Link to="/coaches" className="text-gray-600 hover:text-gray-900">Find coaches</Link>
              <Link to="/login" className="text-gray-600 hover:text-gray-900">Log in</Link>
              <Link
                to="/register"
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700"
              >
                Sign up
              </Link>

              {/* Demo persona switcher — visible only in mock mode */}
              {USE_MOCK && (
                <select
                  defaultValue={localStorage.getItem('c2e_persona') || 'gamer'}
                  onChange={(e) => localStorage.setItem('c2e_persona', e.target.value)}
                  className="rounded-md border border-dashed border-gray-300 bg-white px-2 py-1 text-xs text-gray-500 focus:outline-none"
                  title="Demo persona switcher (mock mode only)"
                >
                  {['gamer', 'coach', 'team_admin', 'reviewer'].map((p) => (
                    <option key={p} value={p}>{p.replace('_', ' ')}</option>
                  ))}
                </select>
              )}
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="mt-16 border-t border-gray-200 px-4 py-6 text-center text-xs text-gray-400">
      Players under 18 require parental or guardian consent. ·{' '}
      <Link to="/consent" className="underline">Consent settings</Link>
      {' · '}
      <Link to="/trust" className="underline">Trust and compliance</Link>
    </footer>
  )
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(() => getUser())

  function handleLogin(u) {
    setUser(u)
  }

  function handleLogout() {
    clearAuth()
    setUser(null)
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-sky-50">
        <Header user={user} onLogout={handleLogout} />
        <main className="mx-auto max-w-5xl px-4 py-8">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Welcome />} />
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="/register" element={<Register onLogin={handleLogin} />} />
            <Route path="/coaches" element={<Discover />} />
            <Route path="/coaches/:id" element={<CoachPage />} />
            <Route path="/consent" element={<ConsentFlow />} />
            <Route path="/trust" element={<TrustPage />} />

            {/* Routes that need auth in production, open in mock */}
            <Route path="/checkout/:packageId" element={
              <RequireAuth><Checkout /></RequireAuth>
            } />
            <Route path="/confirmation" element={
              <RequireAuth><Confirmation /></RequireAuth>
            } />
            <Route path="/dashboard" element={
              <RequireAuth><CoachDashboard /></RequireAuth>
            } />
            <Route path="/sessions/:id" element={
              <RequireAuth><SessionLogging /></RequireAuth>
            } />
            <Route path="/passport/:playerId" element={
              <RequireAuth><SkillsPassport /></RequireAuth>
            } />
            <Route path="/review" element={
              <RequireAuth><ReviewQueue /></RequireAuth>
            } />

            {/* Redirect old / bare path to welcome */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  )
}
