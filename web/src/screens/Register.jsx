import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register, login } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'

export default function Register({ onLogin }) {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    date_of_birth: '',
    guardian_name: '',
    guardian_email: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  // Determine if the entered date of birth makes the user under 18
  function isUnder18() {
    if (!form.date_of_birth) return false
    const dob = new Date(form.date_of_birth)
    const today = new Date()
    const age = today.getFullYear() - dob.getFullYear()
    const m = today.getMonth() - dob.getMonth()
    return age < 18 || (age === 18 && m < 0) || (age === 18 && m === 0 && today.getDate() < dob.getDate())
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match. Re-enter your password.')
      return
    }
    if (form.password.length < 12) {
      setError('Password must be at least 12 characters long.')
      return
    }
    setLoading(true)
    setError('')

    const payload = {
      email: form.email,
      password: form.password,
      date_of_birth: form.date_of_birth,
    }
    if (isUnder18()) {
      payload.guardian_name = form.guardian_name
      payload.guardian_email = form.guardian_email
    }

    try {
      await register(payload)
      // Auto-login after successful registration
      const user = await login({ email: form.email, password: form.password })
      onLogin?.(user)
      navigate('/coaches')
    } catch (e) {
      setError(e.message || 'Account could not be created. Check your details and try again.')
    } finally {
      setLoading(false)
    }
  }

  const under18 = isUnder18()

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-1 text-2xl font-semibold text-gray-900">Create an account</h1>
      <p className="mb-6 text-sm text-gray-500">
        Already have an account?{' '}
        <Link to="/login" className="text-sky-600 hover:underline">Log in</Link>
      </p>

      <ErrorMessage message={error} />

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            required
            autoComplete="email"
            value={form.email}
            onChange={set('email')}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Date of birth</label>
          <input
            type="date"
            required
            value={form.date_of_birth}
            onChange={set('date_of_birth')}
            max={new Date().toISOString().split('T')[0]}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Password <span className="font-normal text-gray-400">(min. 12 characters)</span>
          </label>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Confirm password</label>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={set('confirmPassword')}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
          />
        </div>

        {/* Guardian fields — shown only when under 18 */}
        {under18 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="mb-3 text-sm font-medium text-amber-800">
              Players under 18 need a parent or guardian to complete registration.
            </p>
            <div className="flex flex-col gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Guardian full name</label>
                <input
                  type="text"
                  required={under18}
                  value={form.guardian_name}
                  onChange={set('guardian_name')}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Guardian email</label>
                <input
                  type="email"
                  required={under18}
                  value={form.guardian_email}
                  onChange={set('guardian_email')}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
                />
              </div>
            </div>
          </div>
        )}

        {/* Data consent */}
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" required className="mt-0.5" />
          <span className="text-gray-700">
            I agree to how my data is collected and used.{' '}
            <Link to="/trust" className="text-sky-600 underline">View policy</Link>
          </span>
        </label>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 rounded-lg bg-sky-600 py-2.5 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-sky-300"
        >
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </div>
  )
}
