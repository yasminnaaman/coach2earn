import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, NavLink, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getUser, isLoggedIn, clearAuth, currentRole, getPersona, setPersona } from './auth.js'
import { Avatar, Icon, ToastProvider, useToast } from './components/ui.jsx'

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
import MySessions from './screens/MySessions.jsx'
import Messages from './screens/Messages.jsx'
import SkillsPassport from './screens/SkillsPassport.jsx'
import ConsentFlow from './screens/ConsentFlow.jsx'
import ReviewQueue from './screens/ReviewQueue.jsx'
import TrustPage from './screens/TrustPage.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// ─── Protected route wrapper ──────────────────────────────────────────────────
// Redirects to /login if the user is not logged in (skipped in mock mode).
function RequireAuth({ children }) {
  const location = useLocation()
  if (!USE_MOCK && !isLoggedIn()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function Logo() {
  return (
    <Link to="/" className="group flex items-center gap-2.5 no-underline">
      <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 shadow-lg shadow-violet-900/40">
        <span className="h-3.5 w-3.5 rounded-full border-2 border-white" />
        <span className="absolute h-1.5 w-1.5 rounded-full bg-white" />
      </span>
      <span className="font-display text-lg font-bold tracking-tight text-white">
        Sight<span className="gradient-text">Coach</span>
      </span>
    </Link>
  )
}

function navLinksFor(role, user) {
  const links = [{ to: '/coaches', label: 'Find coaches', icon: 'search' }]
  if (role === 'COACH') {
    links.push({ to: '/dashboard', label: 'Dashboard', icon: 'bolt' })
    links.push({ to: '/my-sessions', label: 'Sessions', icon: 'calendar' })
  }
  if (role === 'PLAYER') {
    links.push({ to: '/my-sessions', label: 'My sessions', icon: 'calendar' })
    links.push({ to: `/passport/${user?.id || 'player-001'}`, label: 'Passport', icon: 'trophy' })
  }
  if (role === 'ADMIN') links.push({ to: '/review', label: 'Review queue', icon: 'shield' })
  if (role) links.push({ to: '/messages', label: 'Messages', icon: 'chat' })
  return links
}

// ─── Header ───────────────────────────────────────────────────────────────────
function Header({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const [persona, setPersonaState] = useState(getPersona())
  const location = useLocation()
  useEffect(() => { setOpen(false) }, [location.pathname])

  // Mock mode shows the persona's links even when logged out (demo flows freely).
  const role = user || USE_MOCK ? currentRole() : null
  const links = navLinksFor(role, user)
  const linkCls = ({ isActive }) =>
    `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`

  function changePersona(p) {
    setPersona(p)
    setPersonaState(p)
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-ink/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Logo />

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkCls}>
              <Icon name={l.icon} /> {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {USE_MOCK && (
            <select value={persona} onChange={(e) => changePersona(e.target.value)}
              className="input w-auto py-1.5 text-xs" title="Demo persona (mock mode only)">
              {['gamer', 'coach', 'team_admin', 'reviewer'].map((p) => (
                <option key={p} value={p}>Demo: {p.replace('_', ' ')}</option>
              ))}
            </select>
          )}
          {user ? (
            <>
              <div className="flex items-center gap-2">
                <Avatar name={user.email} size="sm" />
                <div className="leading-tight">
                  <p className="max-w-[160px] truncate text-xs font-medium text-white">{user.email}</p>
                  <p className="text-[11px] capitalize text-slate-500">{(role || '').toLowerCase()}</p>
                </div>
              </div>
              <button onClick={onLogout} className="btn-ghost btn-sm" title="Log out">
                <Icon name="logout" /> Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost btn-sm">Log in</Link>
              <Link to="/register" className="btn-primary btn-sm">Get started</Link>
            </>
          )}
        </div>

        <button className="btn-ghost btn-sm md:hidden" onClick={() => setOpen((o) => !o)} aria-label="Menu">
          <Icon name={open ? 'x' : 'menu'} className="h-5 w-5" />
        </button>
      </div>

      {open && (
        <div className="border-t border-white/[0.06] bg-panel px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={linkCls}>
                <Icon name={l.icon} /> {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="divider my-3" />
          {USE_MOCK && (
            <select value={persona} onChange={(e) => changePersona(e.target.value)} className="input mb-3 text-xs">
              {['gamer', 'coach', 'team_admin', 'reviewer'].map((p) => (
                <option key={p} value={p}>Demo: {p.replace('_', ' ')}</option>
              ))}
            </select>
          )}
          {user ? (
            <button onClick={onLogout} className="btn-secondary w-full"><Icon name="logout" /> Log out ({user.email})</button>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <Link to="/login" className="btn-secondary">Log in</Link>
              <Link to="/register" className="btn-primary">Get started</Link>
            </div>
          )}
        </div>
      )}
    </header>
  )
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="mt-24 border-t border-white/[0.06]">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Logo />
          <p className="mt-3 max-w-sm text-sm text-slate-500">
            Verified esports coaching for players and teams across Africa. Part of BARBAH PlayEconomy.
          </p>
        </div>
        <div className="flex flex-col gap-2 text-sm sm:items-end">
          <div className="flex gap-4">
            <Link to="/coaches" className="text-slate-400 hover:text-white">Find coaches</Link>
            <Link to="/consent" className="text-slate-400 hover:text-white">Consent settings</Link>
            <Link to="/trust" className="text-slate-400 hover:text-white">Trust &amp; compliance</Link>
          </div>
          <p className="text-xs text-slate-600">Players under 18 require parental or guardian consent.</p>
        </div>
      </div>
    </footer>
  )
}

// ─── Shell (inside the router so it can navigate) ───────────────────────────
function Shell() {
  const [user, setUser] = useState(() => getUser())
  const [, forceRender] = useState(0)
  const navigate = useNavigate()
  const toast = useToast()

  useEffect(() => {
    const onExpired = () => {
      setUser(null)
      toast('Your session expired — please log in again.', 'info')
      navigate('/login')
    }
    const onPersona = () => forceRender((n) => n + 1)
    window.addEventListener('c2e-auth-expired', onExpired)
    window.addEventListener('c2e-persona', onPersona)
    return () => {
      window.removeEventListener('c2e-auth-expired', onExpired)
      window.removeEventListener('c2e-persona', onPersona)
    }
  }, [navigate, toast])

  function handleLogout() {
    // A full page load to "/" avoids RequireAuth bouncing a protected page to
    // /login, and drops any in-memory data from the previous account.
    clearAuth()
    sessionStorage.setItem('c2e_flash', 'You have been logged out.')
    window.location.assign('/')
  }

  useEffect(() => {
    const flash = sessionStorage.getItem('c2e_flash')
    if (flash) {
      sessionStorage.removeItem('c2e_flash')
      toast(flash, 'info')
    }
  }, [toast])

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-violet-700/20 blur-[120px]" />
        <div className="absolute right-[-200px] top-[30%] h-[400px] w-[400px] rounded-full bg-cyan-500/10 blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" />
      </div>

      <Header user={user} onLogout={handleLogout} />
      <main className="mx-auto max-w-6xl px-4 py-10">
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Welcome user={user} />} />
          <Route path="/login" element={<Login onLogin={setUser} />} />
          <Route path="/register" element={<Register onLogin={setUser} />} />
          <Route path="/coaches" element={<Discover />} />
          <Route path="/coaches/:id" element={<CoachPage />} />
          <Route path="/consent" element={<ConsentFlow />} />
          <Route path="/trust" element={<TrustPage />} />

          {/* Routes that need auth in production, open in mock */}
          <Route path="/checkout/:packageId" element={<RequireAuth><Checkout /></RequireAuth>} />
          <Route path="/confirmation" element={<RequireAuth><Confirmation /></RequireAuth>} />
          <Route path="/confirmation/:orderId" element={<RequireAuth><Confirmation /></RequireAuth>} />
          <Route path="/dashboard" element={<RequireAuth><CoachDashboard /></RequireAuth>} />
          <Route path="/my-sessions" element={<RequireAuth><MySessions /></RequireAuth>} />
          <Route path="/sessions/:id" element={<RequireAuth><SessionLogging /></RequireAuth>} />
          <Route path="/messages" element={<RequireAuth><Messages /></RequireAuth>} />
          <Route path="/messages/:userId" element={<RequireAuth><Messages /></RequireAuth>} />
          <Route path="/passport/:playerId" element={<RequireAuth><SkillsPassport /></RequireAuth>} />
          <Route path="/review" element={<RequireAuth><ReviewQueue /></RequireAuth>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <ScrollToTop />
        <Shell />
      </ToastProvider>
    </BrowserRouter>
  )
}
