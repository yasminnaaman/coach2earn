import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getCoachDashboard, getMyOrders, getThreads } from '../api.js'
import { currentRole } from '../auth.js'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { sessionStatus } from '../components/sessionStatus.js'
import { Avatar, Icon, PageHeader, Spinner, Stat, fmtDateTime, timeAgo } from '../components/ui.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export default function CoachDashboard() {
  const isCoach = currentRole() === 'COACH'
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [orders, setOrders] = useState([])
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(isCoach)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setError('')
    try {
      const [d, o, t] = await Promise.all([getCoachDashboard(), getMyOrders(), getThreads().catch(() => [])])
      setData(d)
      setOrders(o)
      setThreads(t)
    } catch (e) {
      setError(e.message || 'Could not load dashboard. Try refreshing the page.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (isCoach) load()
  }, [isCoach])

  if (!isCoach) {
    return (
      <EmptyState icon="bolt" heading="This dashboard is for coaches"
        subtext={USE_MOCK ? 'Switch the demo persona to “coach” in the header.' : 'Log in with a coach account to view your dashboard.'}
        action={!USE_MOCK && <Link to="/login" className="btn-primary">Log in as a coach</Link>} />
    )
  }
  if (loading) return <LoadingSpinner label="Loading your dashboard…" />
  if (error && !data) return <ErrorMessage message={error} />
  if (!data) return null

  const sessions = orders.flatMap((o) => o.sessions.map((s) => ({ ...s, player: o.player, packageTitle: o.packageTitle })))
  const upcoming = sessions
    .filter((s) => ['scheduled', 'confirmed'].includes(s.status))
    .sort((a, b) => new Date(a.startsAt) - new Date(b.startsAt))
  const awaiting = sessions.filter((s) => s.status === 'completed' && !s.playerConfirmed)
  const next = upcoming[0]

  const bonusPct = data.bonusPct || 0
  const progressPct = Math.min((data.points / 400) * 100, 100)
  const projectedBonus = ((2000 * bonusPct) / 100).toFixed(0)
  const unread = threads.reduce((n, t) => n + (t.unread || 0), 0)
  // One row per player, however many packages they have bought.
  const players = Object.values(orders.reduce((acc, o) => {
    const key = o.player?.userId || o.orderId
    acc[key] ||= { ...o.player, packages: 0, active: 0 }
    acc[key].packages += 1
    if (o.status === 'confirmed') acc[key].active += 1
    return acc
  }, {}))

  return (
    <div>
      <PageHeader
        eyebrow={`Team · ${data.teamName}`}
        title="Coach dashboard"
        subtitle="Track earnings, confirmed hours and your prize-share bonus."
        actions={<>
          <button onClick={() => { setRefreshing(true); load() }} className="btn-secondary" disabled={refreshing}>
            {refreshing ? <Spinner /> : <Icon name="refresh" />} Refresh
          </button>
          {next && (
            <button onClick={() => navigate(`/sessions/${next.id}`)} className="btn-primary">
              <Icon name="play" /> {next.status === 'confirmed' ? 'Resume session' : 'Start next session'}
            </button>
          )}
        </>}
      />
      {error && <div className="mb-6"><ErrorMessage message={error} /></div>}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Available balance" value={`$${Number(data.balance).toFixed(2)}`} icon="wallet" tone="emerald" hint="Released after player confirmation" />
        <Stat label="Hours logged" value={`${data.hoursLogged}`} icon="clock" tone="violet" hint={`${data.totalHours} total sessions delivered`} />
        <Stat label="Points" value={data.points} icon="star" tone="amber" hint="10 points per confirmed hour" />
        <Stat label="Bonus share" value={`${bonusPct}%`} icon="trophy" tone="cyan" hint="Of team prize money" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-6">
          {/* Upcoming */}
          <section className="card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold">Upcoming sessions</h2>
              <Link to="/my-sessions" className="link text-sm">View all</Link>
            </div>
            {upcoming.length ? (
              <ul className="flex flex-col gap-2">
                {upcoming.slice(0, 5).map((s) => {
                  const st = sessionStatus(s)
                  return (
                    <li key={s.id}>
                      <button onClick={() => navigate(`/sessions/${s.id}`)}
                        className="flex w-full items-center gap-3 rounded-xl border border-white/[0.06] p-3 text-left transition hover:border-violet-400/40 hover:bg-white/[0.03]">
                        <Avatar name={s.player?.name || '?'} size="sm" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-white">{s.player?.name} · {s.label}</p>
                          <p className="truncate text-xs text-slate-400">{fmtDateTime(s.startsAt)} · {s.packageTitle}</p>
                        </div>
                        <StatusPill status={st.key} label={st.label} />
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <p className="text-sm text-slate-400">No upcoming sessions. When players schedule, they'll appear here.</p>
            )}
          </section>

          {/* Bonus progress */}
          <section className="card">
            <div className="mb-3 flex items-center justify-between text-sm">
              <h2 className="text-base font-semibold">Bonus progress</h2>
              <span className="text-slate-400">Cap 10% at 400 points</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-white/5">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-500 transition-all" style={{ width: `${Math.max(progressPct, 2)}%` }} />
            </div>
            <p className="mt-3 text-sm text-slate-400">{data.points} / 400 points ({progressPct.toFixed(0)}%)</p>
            <p className="mt-1 text-sm text-slate-400">
              {bonusPct > 0 ? `If the team wins a $2,000 prize, your projected bonus is $${projectedBonus}.` : 'Earn points by having players confirm your sessions.'}
            </p>
          </section>

          {/* Activity */}
          <section className="card">
            <h2 className="mb-4 text-base font-semibold">Recent activity</h2>
            {data.activityFeed?.length ? (
              <ul className="flex flex-col divide-y divide-white/[0.06]">
                {data.activityFeed.map((item) => (
                  <li key={item.sessionId}>
                    <button onClick={() => navigate(`/sessions/${item.sessionId}`)} className="flex w-full items-center justify-between py-3 text-left hover:opacity-80">
                      <div>
                        <p className="text-sm font-medium text-white">{item.label}</p>
                        {item.date && <p className="text-xs text-slate-500">{item.date}</p>}
                      </div>
                      <StatusPill status={item.status} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-400">No sessions logged yet.</p>
            )}
          </section>
        </div>

        <div className="flex flex-col gap-6">
          {awaiting.length > 0 && (
            <section className="card border-amber-400/20">
              <h2 className="mb-2 text-base font-semibold">Awaiting player confirmation</h2>
              <p className="mb-4 text-sm text-slate-400">Earnings release once these are confirmed.</p>
              <ul className="flex flex-col gap-2">
                {awaiting.map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="min-w-0 text-slate-300">{s.player?.name} · {s.label}<span className="block truncate text-xs text-slate-500">{s.packageTitle}</span></span>
                    <button className="btn-ghost btn-sm" onClick={() => navigate(`/messages/${s.player?.userId}`)}>Remind</button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold">Messages {unread > 0 && <span className="chip ml-1 bg-violet-500 text-white">{unread}</span>}</h2>
              <Link to="/messages" className="link text-sm">Open inbox</Link>
            </div>
            {threads.length ? (
              <ul className="flex flex-col gap-1">
                {threads.slice(0, 4).map((t) => (
                  <li key={t.counterpart.userId}>
                    <button onClick={() => navigate(`/messages/${t.counterpart.userId}`)} className="flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-white/[0.04]">
                      <Avatar name={t.counterpart.name} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="flex justify-between gap-2">
                          <p className="truncate text-sm font-medium text-white">{t.counterpart.name}</p>
                          <span className="shrink-0 text-xs text-slate-500">{timeAgo(t.lastAt)}</span>
                        </div>
                        <p className={`truncate text-xs ${t.unread ? 'font-semibold text-slate-200' : 'text-slate-400'}`}>{t.lastMessage}</p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-slate-400">No messages yet.</p>}
          </section>

          <section className="card">
            <h2 className="mb-4 text-base font-semibold">Your players</h2>
            {players.length ? (
              <ul className="flex flex-col gap-3">
                {players.map((p) => (
                  <li key={p.userId} className="flex items-center gap-3">
                    <Avatar name={p.name || '?'} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white">{p.name}</p>
                      <p className="truncate text-xs text-slate-400">{p.packages} package{p.packages > 1 ? 's' : ''} · {p.active} active</p>
                    </div>
                    <Link to={`/messages/${p.userId}`} className="btn-ghost btn-sm" title="Message"><Icon name="chat" /></Link>
                    <Link to={`/passport/${p.userId}`} className="btn-ghost btn-sm" title="Skills Passport"><Icon name="trophy" /></Link>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-slate-400">No players yet.</p>}
          </section>
        </div>
      </div>
    </div>
  )
}
