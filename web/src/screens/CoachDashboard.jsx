import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getCoachDashboard } from '../api.js'
import SectionCard from '../components/SectionCard.jsx'
import StatusPill from '../components/StatusPill.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

export default function CoachDashboard() {
  const persona = localStorage.getItem('c2e_persona') || 'gamer'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (persona !== 'coach') { setLoading(false); return }
    load()
  }, [])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const d = await getCoachDashboard('coach-001')
      setData(d)
    } catch {
      setError('Could not load dashboard. Try refreshing the page.')
    } finally {
      setLoading(false)
    }
  }

  if (persona !== 'coach') {
    return (
      <EmptyState
        heading="Switch to the coach persona to view this dashboard."
        subtext="Use the demo persona switcher in the header."
      />
    )
  }

  if (loading) return <LoadingSpinner />
  if (error) return <div className="mt-4"><ErrorMessage message={error} /></div>
  if (!data) return null

  const bonusPct = data.bonusPct || 0
  const progressPct = Math.min((data.points / 400) * 100, 100)
  const projectedBonus = (2000 * bonusPct / 100).toFixed(0)
  // Mock mode keeps the demo session; live mode opens the next open session
  // from the real activity feed (or the most recent one).
  const startSessionId = USE_MOCK
    ? 's-3'
    : (data.activityFeed?.find((i) => i.status !== 'Confirmed') || data.activityFeed?.[0])?.sessionId

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{data.teamName}</h1>
          <p className="text-sm text-gray-500">Coach dashboard</p>
        </div>
        {startSessionId && (
          <Link to={`/sessions/${startSessionId}`}
            className="rounded-lg bg-sky-600 px-5 py-2 text-sm font-medium text-white hover:bg-sky-700 text-center">
            Start session
          </Link>
        )}
      </div>

      {/* Metric cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'USD balance', value: `$${data.balance.toFixed(2)}` },
          { label: 'Hours logged', value: `${data.hoursLogged} / ${data.totalHours}` },
          { label: 'Points', value: String(data.points) },
          { label: 'Bonus share', value: `${bonusPct}%` },
        ].map((m) => (
          <div key={m.label} className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{m.label}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{m.value}</p>
          </div>
        ))}
      </div>

      {/* Bonus progress */}
      <SectionCard className="mb-6">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Bonus progress</span>
          <span className="text-gray-400">Cap 10% at 400 points</span>
        </div>
        <div className="h-2 w-full rounded-full bg-gray-100">
          <div
            className="h-2 rounded-full bg-green-500 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-gray-500">
          {data.points} / 400 points ({progressPct.toFixed(0)}%)
        </p>
        {bonusPct > 0 && (
          <p className="mt-1 text-xs text-gray-500">
            If the team wins a $2,000 prize, projected bonus is ${projectedBonus}.
          </p>
        )}
      </SectionCard>

      {/* Activity feed */}
      <SectionCard title="Activity">
        <div className="flex items-center justify-between mb-3">
          <span />
          <button onClick={load} className="text-xs text-sky-600 hover:underline">Refresh</button>
        </div>
        {data.activityFeed?.length === 0 ? (
          <EmptyState heading="No sessions logged yet." />
        ) : (
          <ul className="flex flex-col divide-y divide-gray-100">
            {data.activityFeed.map((item) => (
              <li key={item.sessionId} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-gray-800">{item.label}</p>
                  {item.date && <p className="text-xs text-gray-400">{item.date}</p>}
                </div>
                <StatusPill status={item.status} />
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  )
}
