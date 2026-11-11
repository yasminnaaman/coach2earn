import { useNavigate } from 'react-router-dom'
import VerifiedBadge from './VerifiedBadge.jsx'

function CoachAvatar({ name }) {
  const initials = name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sm font-bold text-sky-700">
      {initials}
    </div>
  )
}

export default function CoachCard({ coach }) {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate(`/coaches/${coach.coachId}`)}
      className="w-full rounded-xl border border-gray-200 bg-white p-5 text-left transition hover:border-sky-300 hover:shadow-sm"
    >
      <div className="flex items-start gap-4">
        <CoachAvatar name={coach.name} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-gray-900">{coach.name}</span>
            {coach.verified && <VerifiedBadge />}
            {coach.bestMatch && coach.reasonSource === 'ai' && (
              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
                AI best match
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-gray-500">
            {coach.endorsementCount} endorsement{coach.endorsementCount !== 1 ? 's' : ''} ·{' '}
            ${coach.priceUsd}/session
          </p>
          {coach.reason && (
            <p className="mt-2 text-sm text-gray-600">{coach.reason}</p>
          )}
        </div>
      </div>
    </button>
  )
}
