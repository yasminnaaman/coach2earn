import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { addEvidence, getPassport } from '../api.js'
import { getUser } from '../auth.js'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { Avatar, Icon, Spinner, fmtDate, useToast } from '../components/ui.jsx'
import { FeedbackGrid } from './SessionLogging.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const TYPES = {
  ballchasing_replay: { label: 'Replay', cls: 'bg-sky-500/15 text-sky-300', icon: 'play' },
  tournament: { label: 'Tournament', cls: 'bg-emerald-500/15 text-emerald-300', icon: 'trophy' },
  video: { label: 'Video', cls: 'bg-amber-500/15 text-amber-300', icon: 'link' },
}

export default function SkillsPassport() {
  const { playerId } = useParams()
  const toast = useToast()
  const [passport, setPassport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ type: 'ballchasing_replay', url: '' })
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  const me = getUser()
  const isOwner = USE_MOCK || (me?.id === playerId && me?.role === 'PLAYER')

  useEffect(() => {
    setLoading(true)
    getPassport(playerId)
      .then(setPassport)
      .catch(() => setError('Could not load passport. Try refreshing the page.'))
      .finally(() => setLoading(false))
  }, [playerId])

  async function handleAdd(e) {
    e.preventDefault()
    if (!/^https?:\/\//.test(form.url)) return setAddError('Links must start with http:// or https://')
    setAdding(true)
    setAddError('')
    try {
      const updated = await addEvidence(playerId, form)
      setPassport((p) => ({ ...p, evidence: updated }))
      setForm((f) => ({ ...f, url: '' }))
      toast('Evidence added to your passport.')
    } catch (err) {
      setAddError(err.message || 'Could not add evidence. Check the URL and try again.')
    } finally {
      setAdding(false)
    }
  }

  async function share() {
    const url = window.location.href
    try {
      await navigator.clipboard.writeText(url)
      toast('Passport link copied to clipboard.')
    } catch {
      window.prompt('Copy this link:', url)
    }
  }

  if (loading) return <LoadingSpinner label="Loading passport…" />
  if (error) return <ErrorMessage message={error} />
  if (!passport) return <EmptyState heading="No passport found for this player." />

  const { player, rank, replayStats, evidence = [], feedback = [] } = passport
  const stats = [
    { label: 'Matches', value: replayStats.matches },
    { label: 'Goals', value: replayStats.goals },
    { label: 'Saves', value: replayStats.saves },
    { label: 'Shots', value: replayStats.shots },
    { label: 'Boost / min', value: replayStats.boostPerMinute },
  ]
  const shootingPct = replayStats.shots ? Math.round((replayStats.goals / replayStats.shots) * 100) : 0

  return (
    <div className="flex flex-col gap-6 animate-fade-up">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-violet-700/40 via-indigo-800/30 to-cyan-700/30 p-8">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-5">
            <Avatar name={player.name} size="xl" />
            <div>
              <p className="eyebrow text-cyan-200">Skills Passport</p>
              <h1 className="mt-1 text-3xl font-bold sm:text-4xl">{player.name}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="chip bg-white/10 text-white ring-1 ring-inset ring-white/20"><Icon name="trophy" className="h-3.5 w-3.5" /> {rank}</span>
                <span className="chip bg-white/10 capitalize text-slate-200"><Icon name="gamepad" className="h-3.5 w-3.5" /> {player.game?.replace(/_/g, ' ')}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={share} className="btn-secondary"><Icon name="link" /> Share</button>
            {isOwner && <Link to="/coaches" className="btn-primary"><Icon name="search" /> Find a coach</Link>}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="card">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold">Replay stats</h2>
          <span className="text-xs text-slate-500">Sourced from Ballchasing.com · sample data for demo</span>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl bg-white/[0.03] p-4 text-center">
              <p className="font-display text-2xl font-bold text-white">{s.value}</p>
              <p className="text-xs uppercase tracking-wider text-slate-500">{s.label}</p>
            </div>
          ))}
          <div className="rounded-xl bg-gradient-to-br from-violet-500/20 to-cyan-500/10 p-4 text-center">
            <p className="font-display text-2xl font-bold text-white">{shootingPct}%</p>
            <p className="text-xs uppercase tracking-wider text-slate-400">Shooting</p>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        {/* Evidence */}
        <section className="card h-fit">
          <h2 className="mb-4 text-base font-semibold">Evidence</h2>
          {evidence.length === 0 ? (
            <p className="text-sm text-slate-400">No evidence added yet.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {evidence.map((ev) => {
                const t = TYPES[ev.type] || { label: ev.type, cls: 'bg-white/10 text-slate-300', icon: 'link' }
                return (
                  <li key={ev.id}>
                    <a href={ev.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-3 rounded-xl border border-white/[0.06] p-3 transition hover:border-violet-400/40">
                      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${t.cls}`}><Icon name={t.icon} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-xs font-semibold text-slate-300">{t.label}</span>
                        <span className="block truncate text-sm text-violet-300">{ev.url}</span>
                      </span>
                      <span className="shrink-0 text-xs text-slate-500">{fmtDate(ev.addedAt)}</span>
                    </a>
                  </li>
                )
              })}
            </ul>
          )}

          {isOwner && (
            <form onSubmit={handleAdd} className="mt-5 flex flex-col gap-3 border-t border-white/[0.06] pt-5">
              <p className="text-sm font-semibold text-white">Add evidence</p>
              <div className="flex gap-2">
                {Object.entries(TYPES).map(([k, t]) => (
                  <button key={k} type="button" onClick={() => setForm((f) => ({ ...f, type: k }))}
                    className={`chip ring-1 ring-inset ${form.type === k ? 'bg-violet-500/20 text-violet-100 ring-violet-400/40' : 'bg-white/5 text-slate-400 ring-white/10'}`}>
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input type="url" required value={form.url} placeholder="https://ballchasing.com/replay/…"
                  onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))} className="input" />
                <button type="submit" disabled={adding} className="btn-primary">{adding ? <Spinner /> : <Icon name="plus" />} Add</button>
              </div>
              <ErrorMessage message={addError} />
            </form>
          )}
        </section>

        {/* Feedback */}
        <section className="card">
          <h2 className="mb-4 text-base font-semibold">Coach feedback</h2>
          {feedback.length === 0 ? (
            <p className="text-sm text-slate-400">No feedback yet — it appears here after each coaching session.</p>
          ) : (
            <div className="flex flex-col gap-5">
              {feedback.map((fb) => (
                <div key={fb.sessionId} className="rounded-2xl border border-white/[0.06] p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm font-semibold text-white"><Avatar name={fb.coachName} size="sm" /> {fb.coachName}</span>
                    <span className="text-xs text-slate-500">{fmtDate(fb.date)}</span>
                  </div>
                  <FeedbackGrid feedback={fb} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
