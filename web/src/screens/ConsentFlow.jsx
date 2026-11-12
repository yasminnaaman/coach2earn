import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { submitConsent } from '../api.js'
import { isLoggedIn } from '../auth.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Icon, PageHeader, Spinner, useToast } from '../components/ui.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export default function ConsentFlow() {
  const navigate = useNavigate()
  const toast = useToast()
  const [under18, setUnder18] = useState(null)
  const [guardianConsent, setGuardianConsent] = useState(false)
  const [dataConsent, setDataConsent] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const loggedIn = USE_MOCK || isLoggedIn()

  async function handleSubmit(e) {
    e.preventDefault()
    if (!loggedIn) {
      navigate('/login', { state: { from: { pathname: '/consent' } } })
      return
    }
    if (!dataConsent) return setError('Data consent is required to continue.')
    if (under18 && !guardianConsent) {
      return setError('A guardian must give consent before you can create a profile. Ask a parent or guardian to complete this step.')
    }
    setSubmitting(true)
    setError('')
    try {
      await submitConsent({ under18: !!under18, guardianConsent: under18 ? guardianConsent : false })
      toast('Your consent preferences are saved.')
      navigate('/coaches')
    } catch (err) {
      setError(err.message || 'Consent could not be saved. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader eyebrow="Privacy" title="Privacy and consent" subtitle="A few confirmations before you book coaching." />

      {!loggedIn && (
        <div className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-violet-400/20 bg-violet-500/[0.07] px-4 py-3 text-sm text-violet-100">
          <span>Log in so we can save your consent to your account.</span>
          <Link to="/login" state={{ from: { pathname: '/consent' } }} className="btn-primary btn-sm">Log in</Link>
        </div>
      )}

      <ErrorMessage message={error} />

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <fieldset className="card">
          <legend className="sr-only">Age</legend>
          <p className="mb-4 font-semibold text-white">Are you 18 or older?</p>
          <div className="grid grid-cols-2 gap-3">
            {[{ label: 'Yes, I am 18+', value: false }, { label: 'No, I am under 18', value: true }].map(({ label, value }) => (
              <label key={label}
                className={`flex cursor-pointer items-center justify-center rounded-xl border p-4 text-sm font-medium transition ${under18 === value ? 'border-violet-400/60 bg-violet-500/10 text-white' : 'border-white/10 text-slate-300 hover:border-white/20'}`}>
                <input type="radio" name="age" className="sr-only" checked={under18 === value} onChange={() => setUnder18(value)} />
                {label}
              </label>
            ))}
          </div>

          {under18 === true && (
            <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/[0.07] p-4">
              <p className="mb-3 text-sm font-medium text-amber-200">A parent or guardian must agree before you can create a profile.</p>
              <label className="flex cursor-pointer items-start gap-3 text-sm text-amber-100">
                <input type="checkbox" checked={guardianConsent} onChange={(e) => setGuardianConsent(e.target.checked)} className="mt-1 h-4 w-4 accent-violet-500" />
                My parent or guardian has given consent for me to create a profile on SightCoach.
              </label>
            </div>
          )}
        </fieldset>

        <div className="card">
          <label className="flex cursor-pointer items-start gap-3 text-sm">
            <input type="checkbox" checked={dataConsent} onChange={(e) => setDataConsent(e.target.checked)} className="mt-1 h-4 w-4 accent-violet-500" />
            <span className="text-slate-300">
              I agree to how my data is collected and used. <Link to="/trust" className="link">View policy</Link>
            </span>
          </label>
        </div>

        <button type="submit" disabled={submitting || under18 === null} className="btn-primary btn-lg">
          {submitting ? <><Spinner /> Saving…</> : <>{loggedIn ? 'Save and continue' : 'Log in to continue'} <Icon name="arrow" /></>}
        </button>
      </form>
    </div>
  )
}
