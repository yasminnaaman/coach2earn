import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCoach } from '../api.js'
import VerifiedBadge from '../components/VerifiedBadge.jsx'
import SectionCard from '../components/SectionCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const TYPE_LABELS = {
  ballchasing_replay: 'Replay',
  tournament: 'Tournament',
  video: 'Video',
}

const TYPE_COLOURS = {
  ballchasing_replay: 'bg-blue-100 text-blue-700',
  tournament: 'bg-green-100 text-green-700',
  video: 'bg-amber-100 text-amber-700',
}

// "$12.00" for USD, "GBP 12.00" otherwise
function money(amount, currency = 'USD') {
  const prefix = !currency || currency === 'USD' ? '$' : `${currency} `
  return `${prefix}${Number(amount || 0).toFixed(2)}`
}

function CoachAvatar({ name }) {
  const initials = name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-sky-100 text-lg font-bold text-sky-700">
      {initials}
    </div>
  )
}

export default function CoachPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [coach, setCoach] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getCoach(id)
      .then(setCoach)
      .catch(() => setError('Could not load coach profile. Go back and try another coach.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <LoadingSpinner />
  if (error) return <div className="mt-8"><ErrorMessage message={error} /></div>
  if (!coach) return null

  const pkg = coach.packages?.[0]

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <CoachAvatar name={coach.name} />
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-gray-900">{coach.name}</h1>
            {coach.verified && <VerifiedBadge />}
          </div>
          <p className="text-sm text-gray-500">
            {coach.game?.replace('_', ' ')} · {coach.role} · {coach.endorsementCount} endorsements
          </p>
          {coach.bio && <p className="mt-1 text-sm text-gray-700">{coach.bio}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Evidence */}
        <SectionCard title="Evidence">
          {coach.evidence?.length === 0 ? (
            <p className="text-sm text-gray-400">No evidence submitted yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {coach.evidence?.map((ev) => (
                <li key={ev.id} className="flex items-start gap-3">
                  <span className={`mt-0.5 rounded px-2 py-0.5 text-xs font-medium ${TYPE_COLOURS[ev.type] || 'bg-gray-100 text-gray-600'}`}>
                    {TYPE_LABELS[ev.type] || ev.type}
                  </span>
                  <div className="min-w-0">
                    <a href={ev.url} target="_blank" rel="noopener noreferrer"
                      className="break-all text-sm text-sky-600 hover:underline">{ev.url}</a>
                    {ev.description && <p className="mt-0.5 text-xs text-gray-500">{ev.description}</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        {/* Endorsements */}
        <SectionCard title="Endorsements">
          {coach.endorsements?.length === 0 ? (
            <p className="text-sm text-gray-400">No endorsements yet.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {coach.endorsements?.map((e, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{e.community}</span>
                  <span className="text-gray-400">{e.date}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      {/* Package */}
      {pkg && (
        <SectionCard title="Package">
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">{pkg.sessions} sessions × {money(pkg.pricePerSession, pkg.currency)}</span>
              <span className="font-medium">{money(pkg.subtotal, pkg.currency)}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Platform fee ({pkg.platformFeePct}%)</span>
              <span>{money(pkg.platformFee, pkg.currency)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-100 pt-2 font-semibold">
              <span>Total</span>
              <span>{money(pkg.total, pkg.currency)} {pkg.currency || 'USD'}</span>
            </div>
            {(!pkg.currency || pkg.currency === 'USD') && (
              <p className="mt-1 text-xs text-gray-400">
                ≈ KES {(pkg.total * 129).toLocaleString()} at 1 USD = 129.00 KES (est.)
              </p>
            )}
          </div>
          {/* Bonus terms */}
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            Coach earns up to 10% of prize money, based on confirmed hours. Paid only after prize is received.
          </div>
          <button
            onClick={() => navigate(`/checkout/${pkg.id}`)}
            className="mt-4 w-full rounded-lg bg-sky-600 py-2.5 text-sm font-medium text-white hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-300"
          >
            Book this coach
          </button>
        </SectionCard>
      )}
    </div>
  )
}
