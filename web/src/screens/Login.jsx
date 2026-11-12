import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { login } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Icon, Spinner, useToast } from '../components/ui.jsx'

const DEMO_ACCOUNTS = [
  { label: 'Player', email: 'liam.foster@coach2earn.io', password: 'LiamF!player24', icon: 'gamepad' },
  { label: 'Coach', email: 'coach.test@coach2earn.io', password: 'TestCoach123!', icon: 'bolt' },
  { label: 'Admin', email: 'admin.review@coach2earn.io', password: 'AdminReview!2024', icon: 'shield' },
]

export function AuthShell({ title, subtitle, children, aside }) {
  return (
    <div className="mx-auto grid max-w-5xl items-stretch gap-8 lg:grid-cols-2">
      <div className="card animate-fade-up p-8">
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>
      <div className="relative hidden overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-violet-700/40 via-indigo-800/30 to-cyan-700/30 p-8 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-cyan-400/20 blur-3xl" />
        {aside}
      </div>
    </div>
  )
}

export default function Login({ onLogin }) {
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()
  const [form, setForm] = useState({ email: '', password: '' })
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const user = await login({ email: form.email.trim(), password: form.password })
      onLogin?.(user)
      toast(`Welcome back, ${user.email.split('@')[0]}!`)
      const from = location.state?.from?.pathname
      if (from && from !== '/login') navigate(from)
      else if (user.role === 'COACH') navigate('/dashboard')
      else if (user.role === 'ADMIN') navigate('/review')
      else navigate('/coaches')
    } catch (err) {
      setError(/password|credential/i.test(err.message)
        ? 'Email or password is incorrect. Check your details and try again.'
        : err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle={<>New to SightCoach? <Link to="/register" className="link">Create an account</Link></>}
      aside={
        <>
          <div className="relative">
            <p className="eyebrow text-cyan-200">Demo accounts</p>
            <h2 className="mt-2 text-2xl font-bold">Try every role in one click</h2>
            <p className="mt-2 text-sm text-slate-300">Pick an account to fill in the form, then log in.</p>
          </div>
          <div className="relative mt-6 flex flex-col gap-3">
            {DEMO_ACCOUNTS.map((a) => (
              <button key={a.email} type="button"
                onClick={() => { setForm({ email: a.email, password: a.password }); setError('') }}
                className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 p-3 text-left transition hover:border-white/30 hover:bg-black/30">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10"><Icon name={a.icon} /></span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-white">{a.label}</span>
                  <span className="block truncate text-xs text-slate-300">{a.email}</span>
                </span>
              </button>
            ))}
          </div>
        </>
      }
    >
      <ErrorMessage message={error} />
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-5">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" value={form.email}
            onChange={set('email')} className="input" placeholder="you@example.com" />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <div className="relative">
            <input id="password" type={show ? 'text' : 'password'} required autoComplete="current-password"
              value={form.password} onChange={set('password')} className="input pr-16" placeholder="••••••••••••" />
            <button type="button" onClick={() => setShow((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-slate-400 hover:text-white">
              {show ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading} className="btn-primary btn-lg mt-2 w-full">
          {loading ? <><Spinner /> Logging in…</> : <>Log in <Icon name="arrow" /></>}
        </button>
        {/* Demo accounts on small screens (the side panel is hidden) */}
        <div className="flex flex-wrap gap-2 lg:hidden">
          {DEMO_ACCOUNTS.map((a) => (
            <button key={a.email} type="button" className="btn-secondary btn-sm"
              onClick={() => setForm({ email: a.email, password: a.password })}>
              Use demo {a.label.toLowerCase()}
            </button>
          ))}
        </div>
      </form>
    </AuthShell>
  )
}
