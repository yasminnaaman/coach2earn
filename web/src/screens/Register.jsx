import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register, login } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Icon, Spinner, useToast } from '../components/ui.jsx'
import { AuthShell } from './Login.jsx'

function ageFrom(dob) {
  if (!dob) return null
  const d = new Date(dob)
  const t = new Date()
  let age = t.getFullYear() - d.getFullYear()
  const m = t.getMonth() - d.getMonth()
  if (m < 0 || (m === 0 && t.getDate() < d.getDate())) age--
  return age
}

export default function Register({ onLogin }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [form, setForm] = useState({
    email: '', password: '', confirmPassword: '', date_of_birth: '', guardian_name: '', guardian_email: '',
  })
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  const age = ageFrom(form.date_of_birth)
  const under18 = age !== null && age < 18
  const strength = Math.min(4, [/.{12,}/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((r) => r.test(form.password)).length)

  async function handleSubmit(e) {
    e.preventDefault()
    if (form.password !== form.confirmPassword) return setError('Passwords do not match. Re-enter your password.')
    if (form.password.length < 12) return setError('Password must be at least 12 characters long.')
    if (!agreed) return setError('Please agree to the data policy to continue.')
    setLoading(true)
    setError('')
    const payload = { email: form.email.trim(), password: form.password, date_of_birth: form.date_of_birth }
    if (under18) {
      payload.guardian_name = form.guardian_name
      payload.guardian_email = form.guardian_email
    }
    try {
      await register(payload)
      const user = await login({ email: payload.email, password: form.password })
      onLogin?.(user)
      toast('Account created — welcome to SightCoach!')
      navigate('/coaches')
    } catch (err) {
      setError(err.message || 'Account could not be created. Check your details and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle={<>Already have an account? <Link to="/login" className="link">Log in</Link></>}
      aside={
        <div className="relative flex h-full flex-col justify-between">
          <div>
            <p className="eyebrow text-cyan-200">Why SightCoach</p>
            <h2 className="mt-2 text-2xl font-bold">Coaching you can trust</h2>
          </div>
          <ul className="mt-6 flex flex-col gap-4">
            {[
              ['shield', 'Every coach is reviewed by a person'],
              ['wallet', 'Pay in KES or USD with a locked rate'],
              ['check', 'Coaches get paid only after you confirm'],
              ['trophy', 'Build a Skills Passport as you improve'],
            ].map(([icon, text]) => (
              <li key={text} className="flex items-center gap-3 text-sm text-slate-200">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10"><Icon name={icon} /></span>
                {text}
              </li>
            ))}
          </ul>
        </div>
      }
    >
      <ErrorMessage message={error} />
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <div>
          <label className="label" htmlFor="r-email">Email</label>
          <input id="r-email" type="email" required autoComplete="email" value={form.email} onChange={set('email')} className="input" placeholder="you@example.com" />
        </div>
        <div>
          <label className="label" htmlFor="r-dob">Date of birth</label>
          <input id="r-dob" type="date" required value={form.date_of_birth} onChange={set('date_of_birth')}
            max={new Date().toISOString().split('T')[0]} className="input" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="r-pw">Password</label>
            <input id="r-pw" type="password" required autoComplete="new-password" value={form.password} onChange={set('password')} className="input" placeholder="12+ characters" />
          </div>
          <div>
            <label className="label" htmlFor="r-pw2">Confirm</label>
            <input id="r-pw2" type="password" required autoComplete="new-password" value={form.confirmPassword} onChange={set('confirmPassword')} className="input" />
          </div>
        </div>
        {form.password && (
          <div className="flex items-center gap-2">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={`h-1 flex-1 rounded-full ${i < strength ? ['bg-rose-400', 'bg-amber-400', 'bg-cyan-400', 'bg-emerald-400'][strength - 1] : 'bg-white/10'}`} />
            ))}
            <span className="w-14 text-right text-xs text-slate-400">{['Weak', 'Weak', 'Fair', 'Good', 'Strong'][strength]}</span>
          </div>
        )}

        {under18 && (
          <div className="rounded-xl border border-amber-400/30 bg-amber-400/[0.07] p-4">
            <p className="mb-3 text-sm font-medium text-amber-200">Players under 18 need a parent or guardian to complete registration.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <input type="text" required value={form.guardian_name} onChange={set('guardian_name')} className="input" placeholder="Guardian full name" />
              <input type="email" required value={form.guardian_email} onChange={set('guardian_email')} className="input" placeholder="Guardian email" />
            </div>
          </div>
        )}

        <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-300">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-1 h-4 w-4 accent-violet-500" />
          <span>I agree to how my data is collected and used. <Link to="/trust" className="link">View policy</Link></span>
        </label>

        <button type="submit" disabled={loading} className="btn-primary btn-lg mt-1 w-full">
          {loading ? <><Spinner /> Creating account…</> : <>Create account <Icon name="arrow" /></>}
        </button>
      </form>
    </AuthShell>
  )
}
