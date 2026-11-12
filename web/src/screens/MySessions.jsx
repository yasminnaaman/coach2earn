import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cancelSession, confirmSession, disputeSession, getMyOrders } from '../api.js'
import { currentRole } from '../auth.js'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ScheduleModal from '../components/ScheduleModal.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { sessionStatus } from '../components/sessionStatus.js'
import { Avatar, Icon, Modal, PageHeader, Spinner, fmtDateTime, money, useToast } from '../components/ui.jsx'
import { downloadIcs } from './Confirmation.jsx'

export default function MySessions() {
  const role = currentRole()
  const isCoach = role === 'COACH'
  const navigate = useNavigate()
  const toast = useToast()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [scheduleFor, setScheduleFor] = useState(null)
  const [disputeFor, setDisputeFor] = useState(null)
  const [reason, setReason] = useState('')

  async function load() {
    setError('')
    try {
      setOrders(await getMyOrders())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  async function act(id, fn, success) {
    setBusy(id)
    try {
      await fn()
      toast(success)
      await load()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy('')
    }
  }

  async function submitDispute() {
    if (!reason.trim()) return
    const id = disputeFor.id
    setDisputeFor(null)
    await act(id, () => disputeSession(id, reason.trim()), 'Dispute raised — the coach has been notified and payout is on hold.')
    setReason('')
  }

  if (role === 'ADMIN') {
    return <EmptyState icon="calendar" heading="Sessions are for players and coaches" subtext="Admins manage coach verification from the review queue."
      action={<Link to="/review" className="btn-primary">Open review queue</Link>} />
  }
  if (loading) return <LoadingSpinner label="Loading your sessions…" />

  const all = orders.flatMap((o) => o.sessions.map((s) => ({ ...s, order: o })))
  const needsAction = all.filter((s) =>
    isCoach ? s.status === 'confirmed' || (s.status === 'scheduled' && new Date(s.startsAt) < new Date())
      : (s.status === 'completed' && !s.playerConfirmed) || s.status === 'disputed')
  const upcoming = all
    .filter((s) => s.status === 'scheduled' && new Date(s.startsAt) >= new Date())
    .sort((a, b) => new Date(a.startsAt) - new Date(b.startsAt))

  function SessionRow({ s }) {
    const st = sessionStatus(s)
    const other = isCoach ? s.order.player : s.order.coach
    const loadingThis = busy === s.id
    return (
      <li className="flex flex-col gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 sm:flex-row sm:items-center">
        <div className="flex flex-1 items-center gap-3">
          <Avatar name={other?.name || '?'} size="sm" />
          <div className="min-w-0">
            <p className="font-medium text-white">{s.label} <span className="font-normal text-slate-400">with {other?.name}</span></p>
            <p className="text-xs text-slate-400">{fmtDateTime(s.startsAt)} · {s.order.packageTitle}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={st.key} label={st.label} />
          {loadingThis && <Spinner className="h-4 w-4 text-violet-300" />}
          {!isCoach && s.status === 'completed' && !s.playerConfirmed && (
            <>
              <button className="btn-success btn-sm" disabled={loadingThis}
                onClick={() => act(s.id, () => confirmSession(s.id), 'Session confirmed — coach payout released and points added!')}>
                <Icon name="check" /> Confirm
              </button>
              <button className="btn-danger btn-sm" disabled={loadingThis} onClick={() => setDisputeFor(s)}>
                <Icon name="flag" /> Dispute
              </button>
            </>
          )}
          {!isCoach && s.status === 'disputed' && (
            <button className="btn-success btn-sm" disabled={loadingThis}
              onClick={() => act(s.id, () => confirmSession(s.id), 'Dispute resolved — session confirmed.')}>
              <Icon name="check" /> Resolve & confirm
            </button>
          )}
          {isCoach && ['scheduled', 'confirmed'].includes(s.status) && (
            <button className="btn-primary btn-sm" onClick={() => navigate(`/sessions/${s.id}`)}>
              <Icon name={s.status === 'scheduled' ? 'play' : 'stop'} /> {s.status === 'scheduled' ? 'Start' : 'Finish'}
            </button>
          )}
          {s.status === 'scheduled' && (
            <button className="btn-ghost btn-sm" disabled={loadingThis}
              onClick={() => window.confirm('Cancel this session? The slot can be rescheduled.') &&
                act(s.id, () => cancelSession(s.id), 'Session cancelled — you can reschedule it.')}>
              Cancel
            </button>
          )}
          <button className="btn-ghost btn-sm" onClick={() => navigate(`/sessions/${s.id}`)}>Details <Icon name="arrow" /></button>
        </div>
      </li>
    )
  }

  return (
    <div>
      <PageHeader
        eyebrow={isCoach ? 'Coach' : 'Player'}
        title={isCoach ? 'Coaching sessions' : 'My sessions'}
        subtitle={isCoach ? 'Run your booked sessions and keep notes for your players.' : 'Schedule, confirm and review your coaching sessions.'}
        actions={<>
          <button className="btn-secondary" onClick={() => downloadIcs(all, 'your coach') || toast('No scheduled sessions to export.', 'info')}>
            <Icon name="download" /> Export calendar
          </button>
          {!isCoach && <Link to="/coaches" className="btn-primary"><Icon name="plus" /> Book a coach</Link>}
        </>}
      />
      <ErrorMessage message={error} />

      {orders.length === 0 ? (
        <EmptyState icon="calendar"
          heading={isCoach ? 'No bookings yet' : 'No sessions booked yet'}
          subtext={isCoach ? 'When players book your packages, their sessions appear here.' : 'Find a coach and book a package to get started.'}
          action={!isCoach && <Link to="/coaches" className="btn-primary">Find a coach</Link>} />
      ) : (
        <div className="flex flex-col gap-8">
          {needsAction.length > 0 && (
            <section className="card border-amber-400/20">
              <h2 className="mb-4 flex items-center gap-2 text-base font-semibold">
                <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" /> Needs your attention
              </h2>
              <p className="-mt-2 mb-4 text-sm text-slate-400">
                {isCoach ? 'Sessions in progress or past their start time.' : 'Confirm completed sessions so your coach gets paid — or raise a dispute.'}
              </p>
              <ul className="flex flex-col gap-2">{needsAction.map((s) => <SessionRow key={s.id} s={s} />)}</ul>
            </section>
          )}

          <section className="card">
            <h2 className="mb-4 text-base font-semibold">Upcoming</h2>
            {upcoming.length ? (
              <ul className="flex flex-col gap-2">{upcoming.map((s) => <SessionRow key={s.id} s={s} />)}</ul>
            ) : (
              <p className="text-sm text-slate-400">No upcoming sessions{!isCoach && ' — schedule one from a package below'}.</p>
            )}
          </section>

          <section>
            <h2 className="mb-4 text-xl font-semibold">{isCoach ? 'Player packages' : 'Your packages'}</h2>
            <div className="grid gap-4 lg:grid-cols-2">
              {orders.map((o) => {
                const done = o.sessions.filter((s) => s.status === 'completed' && s.playerConfirmed).length
                const other = isCoach ? o.player : o.coach
                return (
                  <div key={o.orderId} className="card flex flex-col gap-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <Avatar name={other?.name || '?'} />
                        <div>
                          <p className="font-semibold text-white">{o.packageTitle}</p>
                          <p className="text-xs text-slate-400">{isCoach ? 'Player' : 'Coach'}: {other?.name} · <span className="font-mono">{o.orderRef}</span></p>
                        </div>
                      </div>
                      <StatusPill status={o.status === 'completed' ? 'completed' : 'paid'} label={o.status === 'completed' ? 'Completed' : 'Active'} />
                    </div>
                    <div>
                      <div className="mb-1.5 flex justify-between text-xs text-slate-400">
                        <span>{done} of {o.sessionLimit} sessions confirmed</span>
                        <span>{money(o.price, o.currency)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/5">
                        <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" style={{ width: `${(done / o.sessionLimit) * 100}%` }} />
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {!isCoach && o.remaining > 0 && o.status === 'confirmed' && (
                        <button className="btn-primary btn-sm" onClick={() => setScheduleFor(o)}>
                          <Icon name="calendar" /> Schedule {o.remaining} remaining
                        </button>
                      )}
                      <button className="btn-secondary btn-sm" onClick={() => navigate(`/messages/${other?.userId}`)} disabled={!other?.userId}>
                        <Icon name="chat" /> Message {isCoach ? 'player' : 'coach'}
                      </button>
                      {!isCoach && (
                        <button className="btn-ghost btn-sm" onClick={() => navigate(`/confirmation/${o.orderId}`)}>Receipt</button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </div>
      )}

      <ScheduleModal open={!!scheduleFor} order={scheduleFor} onClose={() => setScheduleFor(null)} onScheduled={load} />

      <Modal open={!!disputeFor} onClose={() => setDisputeFor(null)} title="Raise a dispute"
        footer={<>
          <button className="btn-ghost" onClick={() => setDisputeFor(null)}>Cancel</button>
          <button className="btn-danger" onClick={submitDispute} disabled={!reason.trim()}><Icon name="flag" /> Submit dispute</button>
        </>}>
        <p className="mb-3 text-sm text-slate-400">
          Tell us what went wrong with {disputeFor?.label}. The coach's payout stays on hold and they'll get your message.
        </p>
        <textarea rows={4} className="input" value={reason} onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. The session ended 20 minutes early." autoFocus />
      </Modal>
    </div>
  )
}
