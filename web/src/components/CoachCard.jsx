import { useNavigate } from 'react-router-dom'
import VerifiedBadge from './VerifiedBadge.jsx'
import { Avatar, Icon, money } from './ui.jsx'

export default function CoachCard({ coach, index = 0 }) {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate(`/coaches/${coach.coachId}`)}
      style={{ animationDelay: `${index * 50}ms` }}
      className="card card-hover group flex w-full animate-fade-up flex-col gap-4 p-5 text-left"
    >
      <div className="flex items-start gap-4">
        <Avatar name={coach.name} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-lg font-semibold text-white">{coach.name}</span>
            {coach.verified && <VerifiedBadge />}
            {coach.bestMatch && (
              <span className="chip bg-gradient-to-r from-violet-500/20 to-cyan-500/20 text-violet-200 ring-1 ring-inset ring-violet-400/30">
                <Icon name="sparkles" className="h-3 w-3" /> Best match
              </span>
            )}
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-400">
            {coach.game && (
              <span className="inline-flex items-center gap-1 capitalize">
                <Icon name="gamepad" className="h-3.5 w-3.5" /> {coach.game.replace(/_/g, ' ')}
              </span>
            )}
            {coach.role && <span>{coach.role}</span>}
            {coach.endorsementCount > 0 && <span>{coach.endorsementCount} endorsements</span>}
          </p>
        </div>
        <div className="text-right">
          <p className="font-display text-2xl font-bold text-white">{money(coach.priceUsd, 'USD')}</p>
          <p className="text-xs text-slate-500">per session</p>
        </div>
      </div>
      {coach.reason && <p className="line-clamp-2 text-sm text-slate-300">{coach.reason}</p>}
      <div className="flex items-center justify-between">
        {coach.score != null ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" style={{ width: `${coach.score}%` }} />
            </div>
            Match {coach.score}%
          </div>
        ) : <span />}
        <span className="inline-flex items-center gap-1 text-sm font-semibold text-violet-300 transition group-hover:gap-2">
          View profile <Icon name="arrow" />
        </span>
      </div>
    </button>
  )
}
