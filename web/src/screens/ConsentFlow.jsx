import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitConsent } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'

export default function ConsentFlow() {
  const navigate = useNavigate()
  const [under18, setUnder18] = useState(null)
  const [guardianConsent, setGuardianConsent] = useState(false)
  const [dataConsent, setDataConsent] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!dataConsent) { setError('Data consent is required to continue.'); return }
    if (under18 && !guardianConsent) {
      setError('A guardian must give consent before you can create a profile. Ask a parent or guardian to complete this step.')
      return
    }
    setSubmitting(true); setError('')
    try {
      await submitConsent({ under18: !!under18, guardianConsent: under18 ? guardianConsent : false })
      navigate('/')
    } catch {
      setError('Consent could not be saved. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-2 text-2xl font-semibold text-gray-900">Privacy and consent</h1>
      <p className="mb-6 text-sm text-gray-500">We need a few confirmations before creating your profile.</p>

      <ErrorMessage message={error} />

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-6">
        {/* Age step */}
        <fieldset className="rounded-xl border border-gray-200 bg-white p-5">
          <legend className="mb-3 text-sm font-medium text-gray-800">Are you 18 or older?</legend>
          <div className="flex gap-4">
            {[{ label: 'Yes', value: false }, { label: 'No', value: true }].map(({ label, value }) => (
              <label key={label} className="flex items-center gap-2 cursor-pointer text-sm">
                <input type="radio" name="age" checked={under18 === value}
                  onChange={() => setUnder18(value)} />
                {label}
              </label>
            ))}
          </div>

          {under18 === true && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="mb-3 text-sm font-medium text-amber-800">
                A parent or guardian must agree before you can create a profile.
              </p>
              <label className="flex items-start gap-2 cursor-pointer text-sm text-amber-900">
                <input type="checkbox" checked={guardianConsent}
                  onChange={(e) => setGuardianConsent(e.target.checked)} className="mt-0.5" />
                My parent or guardian has given consent for me to create a profile on Coach2Earn.
              </label>
            </div>
          )}
        </fieldset>

        {/* Data consent */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <label className="flex items-start gap-3 cursor-pointer text-sm">
            <input type="checkbox" required checked={dataConsent}
              onChange={(e) => setDataConsent(e.target.checked)} className="mt-0.5" />
            <span className="text-gray-700">
              I agree to how my data is collected and used.{' '}
              <a href="#" className="text-indigo-600 underline">View policy</a>
            </span>
          </label>
        </div>

        <button type="submit" disabled={submitting || under18 === null}
          className="rounded-lg bg-indigo-600 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-indigo-300">
          {submitting ? 'Saving…' : 'Continue'}
        </button>
      </form>
    </div>
  )
}
