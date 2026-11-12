import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { captureOrder } from '../api.js'
import EmptyState from '../components/EmptyState.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ScheduleModal from '../components/ScheduleModal.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { Avatar, Icon, fmtDateTime, money } from '../components/ui.jsx'

export function downloadIcs(sessions, coachName) {
  const fmt = (d) => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z'
  const events = sessions
    .filter((s) => s.startsAt && s.status !== 'cancelled')
    .map((s) => {
      const start = new Date(s.startsAt)
      const end = s.endsAt ? new Date(s.endsAt) : new Date(start.getTime() + 3600e3)
      return [
        'BEGIN:VEVENT',
        `UID:${s.id}@sightcoach`,
        `DTSTAMP:${fmt(new Date())}`,
        `DTSTART:${fmt(start)}`,
        `DTEND:${fmt(end)}`,
        `SUMMARY:SightCoach — ${s.label || 'Coaching session'}`,
        `DESCRIPTION:Coaching session with ${coachName || 'your coach'}`,
        'END:VEVENT',
      ].join('\r\n')
    })
  if (!events.length) return 0
  const ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//SightCoach//EN', ...events, 'END:VCALENDAR'].join('\r\n')
  const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'SightCoach-sessions.ics'
  a.click()
  URL.revokeObjectURL(url)
  return events.length
}

const PAID_WITH = { mpesa_sim: 'M-Pesa (simulated)', card: 'Card (simulated)', paypal_balance: 'PayPal (simulated)' }

export default function Confirmation() {
  const params = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const orderId = params.orderId || new URLSearchParams(location.search).get('order') || location.state?.receipt?.orderId
  const [receipt, setReceipt] = useState(null)
  const [loading, setLoading] = useState(!!orderId)
  const [error, setError] = useState('')
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [calMsg, setCalMsg] = useState('')

  useEffect(() => {
    if (!orderId) return
    captureOrder(orderId)
      .then(setReceipt)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [orderId])

  if (loading) return <LoadingSpinner label="Loading your booking…" />
  if (!receipt) {
    return (
      <EmptyState heading="No booking found" subtext={error || 'Go back and complete checkout.'}
        action={<Link to="/coaches" className="btn-primary">Find a coach</Link>} />
    )
  }

  const sessions = receipt.sessions || []
  const placeholders = Array.from({ length: receipt.remaining || 0 }, (_, i) => ({ id: `tbd-${i}`, label: `Session ${sessions.length + i + 1}` }))

  function onScheduled(updated) {
    setReceipt((r) => ({ ...r, ...updated }))
  }

  function addToCalendar() {
    const n = downloadIcs(sessions, receipt.coachName)
    setCalMsg(n ? `Downloaded ${n} event${n > 1 ? 's' : ''} for your calendar.` : 'Schedule a session first, then add it to your calendar.')
  }

  return (
    <div className="animate-fade-up">
      <div className="mb-10 flex flex-col items-center text-center">
        <div className="relative mb-5">
          <span className="absolute inset-0 animate-ping rounded-full bg-emerald-400/20" />
          <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-400 text-slate-950 shadow-xl shadow-emerald-900/40">
            <Icon name="check" className="h-8 w-8" strokeWidth={3} />
          </span>
        </div>
        <p className="eyebrow">Booking confirmed</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">You're all set!</h1>
        <p className="mt-2 max-w-lg text-slate-400">
          {receipt.sessionLimit} sessions with {receipt.coachName} are paid for.
          {receipt.remaining > 0 && ' Pick times for your sessions below.'}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <section className="card">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-base font-semibold">Your sessions</h2>
            <span className="text-xs text-slate-500">{sessions.length} of {receipt.sessionLimit} scheduled</span>
          </div>
          <ul className="flex flex-col gap-2">
            {sessions.map((s) => (
              <li key={s.id} className="flex items-center gap-4 rounded-xl border border-white/[0.06] p-3">
                <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-violet-500/15 text-violet-200">
                  <span className="text-[10px] font-semibold uppercase">{new Date(s.startsAt).toLocaleDateString('en-GB', { month: 'short' })}</span>
                  <span className="font-display text-lg font-bold leading-none">{new Date(s.startsAt).getDate()}</span>
                </div>
                <div className="flex-1">
                  <p className="font-medium text-white">{s.label}</p>
                  <p className="text-xs text-slate-400">{fmtDateTime(s.startsAt)}</p>
                </div>
                <StatusPill status={s.status} />
              </li>
            ))}
            {placeholders.map((p) => (
              <li key={p.id} className="flex items-center gap-4 rounded-xl border border-dashed border-white/10 p-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/5 text-xs font-semibold text-slate-500">TBD</div>
                <p className="flex-1 text-sm text-slate-400">{p.label} — not scheduled yet</p>
              </li>
            ))}
          </ul>
          <div className="mt-5 flex flex-wrap gap-2">
            {receipt.remaining > 0 && (
              <button onClick={() => setScheduleOpen(true)} className="btn-primary"><Icon name="calendar" /> Schedule sessions</button>
            )}
            <button onClick={addToCalendar} className="btn-secondary"><Icon name="download" /> Add to calendar</button>
            <button onClick={() => navigate('/my-sessions')} className="btn-ghost">Go to My sessions <Icon name="arrow" /></button>
          </div>
          {calMsg && <p className="mt-3 text-sm text-slate-400">{calMsg}</p>}
        </section>

        <section className="card h-fit">
          <h2 className="mb-5 text-base font-semibold">Receipt</h2>
          <div className="mb-5 flex items-center gap-3">
            <Avatar name={receipt.coachName} />
            <div>
              <p className="font-semibold text-white">{receipt.coachName}</p>
              <p className="text-xs text-slate-400">{receipt.packageLabel}</p>
            </div>
          </div>
          <dl className="flex flex-col gap-2.5 text-sm">
            {[
              ['Reference', <span key="r" className="font-mono text-white">{receipt.receiptRef}</span>],
              ['Paid with', PAID_WITH[receipt.paidWith] || receipt.paidWith],
              ['Package price', money(receipt.price, receipt.currency)],
              ['Platform fee', money(0, receipt.currency)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4"><dt className="text-slate-400">{k}</dt><dd className="text-right text-slate-200">{v}</dd></div>
            ))}
            <div className="divider my-1" />
            <div className="flex justify-between text-base font-semibold text-white">
              <dt>Total paid</dt>
              <dd>{receipt.currencyPaid === 'KES' ? `KES ${receipt.totalPaidKes?.toLocaleString()}` : `USD ${receipt.totalPaidUsd?.toFixed(2)}`}</dd>
            </div>
            <p className="text-xs text-slate-500">Rate used: {receipt.rateUsed}</p>
          </dl>
          <div className="mt-5 flex flex-col gap-2">
            <span className="chip w-fit bg-emerald-500/15 text-emerald-300">✓ Bonus terms signed by both parties</span>
            <span className="chip w-fit bg-sky-500/15 text-sky-300">● Coach payout releases after each confirmed session</span>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2">
            <button onClick={() => window.print()} className="btn-secondary"><Icon name="printer" /> Print</button>
            <button onClick={() => navigate(`/messages/${receipt.coach?.userId}`)} disabled={!receipt.coach?.userId} className="btn-secondary">
              <Icon name="chat" /> Message coach
            </button>
          </div>
        </section>
      </div>

      <ScheduleModal open={scheduleOpen} order={receipt} onClose={() => setScheduleOpen(false)} onScheduled={onScheduled} />
    </div>
  )
}
