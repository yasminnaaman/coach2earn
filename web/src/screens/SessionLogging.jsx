import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  cancelSession, confirmSession, disputeSession, endSession, getSession, startSession, submitFeedback,
} from '../api.js'
import { currentRole } from '../auth.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { sessionStatus } from '../components/sessionStatus.js'
import { Avatar, Icon, Modal, Spinner, fmtDateTime, useToast } from '../components/ui.jsx'

// Same convention the API uses: "+" strength, "-" focus area, ">" next goal.
export function parseNotes(notes = '') {
  const out = { strengths: [], focusAreas: [], nextGoals: [] }
  for (const raw of notes.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (line.startsWith('+')) out.strengths.push(line.slice(1).trim())
    else if (line.startsWith('>')) out.nextGoals.push(line.slice(1).trim())
    else out.focusAreas.push(line.replace(/^-/, '').trim())
  }
  return out
}

export function FeedbackGrid({ feedback }) {
  // Notes written without +/-/> markers read better as a plain summary.
  const plain = !feedback.strengths?.length && !feedback.nextGoals?.length && feedback.focusAreas?.length <= 1
  if (plain) {
    return (
      <p className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-300">
        {feedback.focusAreas?.[0] || 'No notes recorded for this session.'}
      </p>
    )
  }
  const cols = [
    { label: 'Strengths', items: feedback.strengths, cls: 'text-emerald-300', dot: 'bg-emerald-400' },
    { label: 'Focus areas', items: feedback.focusAreas, cls: 'text-amber-300', dot: 'bg-amber-400' },
    { label: 'Next goals', items: feedback.nextGoals, cls: 'text-cyan-300', dot: 'bg-cyan-400' },
  ]
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {cols.map((c) => (
        <div key={c.label} className="rounded-xl bg-white/[0.03] p-4">
          <p className={`mb-2 text-xs font-semibold uppercase tracking-wider ${c.cls}`}>{c.label}</p>
          {c.items?.length ? (
            <ul className="flex flex-col gap-1.5 text-sm text-slate-300">
              {c.items.map((it, i) => (
                <li key={i} className="flex gap-2"><span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${c.dot}`} />{it}</li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">—</p>}
        </div>
      ))}
    </div>
  )
}

const NOTE_TEMPLATE = '+ \n- \n> '

export default function SessionLogging() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const role = currentRole()
  const isCoach = role === 'COACH'
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [notes, setNotes] = useState(NOTE_TEMPLATE)
  const [feedback, setFeedback] = useState(null)
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [reason, setReason] = useState('')

  useEffect(() => {
    setLoading(true)
    getSession(id)
      .then((s) => {
        setSession(s)
        if (s.notes) setNotes(s.notes)
      })
      .catch((e) => setError(e.message || 'Could not load this session.'))
      .finally(() => setLoading(false))
  }, [id])

  async function run(fn, message) {
    setBusy(true)
    setError('')
    try {
      const updated = await fn()
      setSession((s) => ({ ...s, ...updated }))
      toast(message)
    } catch (e) {
      setError(e.message || 'Action failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  async function generateFeedback() {
    setBusy(true)
    try {
      setFeedback(await submitFeedback(session.id))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading session…" />
  if (!session) {
    return (
      <div className="flex flex-col items-start gap-4">
        <ErrorMessage message={error || 'Session not found.'} />
        <Link to="/my-sessions" className="btn-secondary"><Icon name="back" /> Back to sessions</Link>
      </div>
    )
  }

  const st = sessionStatus(session)
  const other = isCoach ? session.player : session.coach
  const cleanNotes = notes.split('\n').filter((l) => l.replace(/^[+\->]\s*$/, '').trim()).join('\n')
  const parsed = session.notes ? parseNotes(session.notes) : null
  const STEPS = ['Scheduled', 'In progress', 'Completed', 'Confirmed']
  const stepIndex = { scheduled: 0, confirmed: 1, completed: session.playerConfirmed ? 3 : 2, disputed: 2, cancelled: -1 }[session.status]

  return (
    <div className="animate-fade-up">
      <button onClick={() => navigate(-1)} className="btn-ghost btn-sm mb-6 -ml-3"><Icon name="back" /> Back</button>

      <div className="card mb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <Avatar name={other?.name || '?'} size="lg" />
            <div>
              <p className="eyebrow">{session.packageTitle}</p>
              <h1 className="mt-1 text-2xl font-bold">{session.label} <span className="text-slate-400">with {other?.name}</span></h1>
              <p className="mt-1 text-sm text-slate-400"><Icon name="clock" className="mr-1 inline h-4 w-4" />{fmtDateTime(session.startsAt)} · 60 min</p>
            </div>
          </div>
          <StatusPill status={st.key} label={st.label} />
        </div>

        {stepIndex >= 0 && (
          <div className="mt-6 grid grid-cols-4 gap-2">
            {STEPS.map((label, i) => (
              <div key={label}>
                <div className={`h-1.5 rounded-full ${i <= stepIndex ? 'bg-gradient-to-r from-violet-500 to-cyan-400' : 'bg-white/10'}`} />
                <p className={`mt-2 text-xs ${i <= stepIndex ? 'text-white' : 'text-slate-500'}`}>{label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div className="mb-6"><ErrorMessage message={error} /></div>}

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <section className="card">
          {/* ── Coach actions ─────────────────────────────────────────── */}
          {isCoach && session.status === 'scheduled' && (
            <div className="flex flex-col items-start gap-4">
              <h2 className="text-lg font-semibold">Ready when you are</h2>
              <p className="text-sm text-slate-400">Start the session when you and {other?.name} are connected. You'll add notes when you finish.</p>
              <div className="flex flex-wrap gap-2">
                <button className="btn-primary btn-lg" disabled={busy} onClick={() => run(() => startSession(session.id), 'Session started — good luck!')}>
                  {busy ? <Spinner /> : <Icon name="play" />} Start session
                </button>
                <button className="btn-ghost" disabled={busy}
                  onClick={() => window.confirm('Cancel this session?') && run(() => cancelSession(session.id), 'Session cancelled.')}>
                  Cancel session
                </button>
              </div>
            </div>
          )}

          {isCoach && session.status === 'confirmed' && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
                <h2 className="text-lg font-semibold">Session in progress</h2>
              </div>
              <div>
                <label className="label">Session notes for {other?.name}</label>
                <textarea rows={8} className="input font-mono text-sm" value={notes} onChange={(e) => setNotes(e.target.value)} />
                <p className="mt-2 text-xs text-slate-500">
                  Start lines with <span className="font-mono text-emerald-300">+</span> for strengths,
                  <span className="font-mono text-amber-300"> -</span> for focus areas and
                  <span className="font-mono text-cyan-300"> &gt;</span> for next goals. They appear on the player's Skills Passport.
                </p>
              </div>
              <button className="btn-primary btn-lg w-fit" disabled={busy}
                onClick={() => run(() => endSession(session.id, cleanNotes), 'Session completed — waiting for the player to confirm.')}>
                {busy ? <Spinner /> : <Icon name="stop" />} End session & save notes
              </button>
            </div>
          )}

          {/* ── Player actions ────────────────────────────────────────── */}
          {!isCoach && session.status === 'scheduled' && (
            <div className="flex flex-col items-start gap-4">
              <h2 className="text-lg font-semibold">Coming up</h2>
              <p className="text-sm text-slate-400">Your coach will start the session at the scheduled time. Need to change it? Cancel and reschedule from My sessions.</p>
              <div className="flex flex-wrap gap-2">
                <Link to={`/messages/${other?.userId}`} className="btn-secondary"><Icon name="chat" /> Message coach</Link>
                <button className="btn-ghost" disabled={busy}
                  onClick={() => window.confirm('Cancel this session? You can reschedule it afterwards.') && run(() => cancelSession(session.id), 'Session cancelled — reschedule it from My sessions.')}>
                  Cancel session
                </button>
              </div>
            </div>
          )}
          {!isCoach && session.status === 'confirmed' && (
            <div><h2 className="text-lg font-semibold">Session in progress</h2><p className="mt-2 text-sm text-slate-400">Your coach has started the session. Once they finish you'll be asked to confirm it.</p></div>
          )}
          {!isCoach && ((session.status === 'completed' && !session.playerConfirmed) || session.status === 'disputed') && (
            <div className="flex flex-col items-start gap-4">
              <h2 className="text-lg font-semibold">{session.status === 'disputed' ? 'Dispute open' : 'Did this session happen as planned?'}</h2>
              <p className="text-sm text-slate-400">
                {session.status === 'disputed'
                  ? 'The coach payout is on hold. Once it is sorted out, confirm the session to release it.'
                  : 'Confirming releases the coach payout and adds points to your account. If something went wrong, raise a dispute.'}
              </p>
              <div className="flex flex-wrap gap-2">
                <button className="btn-success btn-lg" disabled={busy} onClick={() => run(() => confirmSession(session.id), 'Session confirmed — thanks! Coach payout released.')}>
                  {busy ? <Spinner /> : <Icon name="check" />} {session.status === 'disputed' ? 'Resolve & confirm' : 'Confirm session'}
                </button>
                {session.status === 'completed' && (
                  <button className="btn-danger btn-lg" disabled={busy} onClick={() => setDisputeOpen(true)}><Icon name="flag" /> Dispute</button>
                )}
              </div>
            </div>
          )}

          {/* ── Shared: finished / cancelled ──────────────────────────── */}
          {session.status === 'completed' && (session.playerConfirmed || isCoach) && (
            <div className="mb-2">
              <h2 className="text-lg font-semibold">{session.playerConfirmed ? 'Session confirmed 🎉' : 'Waiting for the player to confirm'}</h2>
              <p className="mt-1 text-sm text-slate-400">
                {session.playerConfirmed
                  ? isCoach ? 'Your earning for this session is now available.' : 'Thanks for confirming — your points have been added.'
                  : 'Your earning is recorded and will be released when the player confirms.'}
              </p>
            </div>
          )}
          {isCoach && session.status === 'disputed' && (
            <div><h2 className="text-lg font-semibold">The player raised a dispute</h2><p className="mt-1 text-sm text-slate-400">Check your messages for details. Payout is on hold until it's resolved.</p>
              <Link to={`/messages/${other?.userId}`} className="btn-secondary mt-4"><Icon name="chat" /> Open messages</Link></div>
          )}
          {session.status === 'cancelled' && (
            <div><h2 className="text-lg font-semibold">Session cancelled</h2><p className="mt-1 text-sm text-slate-400">{isCoach ? 'The player can reschedule this slot.' : 'You can schedule a replacement from My sessions.'}</p>
              <Link to="/my-sessions" className="btn-secondary mt-4">Go to sessions</Link></div>
          )}

          {/* ── Notes / feedback ──────────────────────────────────────── */}
          {parsed && ['completed', 'disputed'].includes(session.status) && (
            <div className="mt-6">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-semibold">Coach feedback</h3>
                {isCoach && (
                  <button className="btn-secondary btn-sm" disabled={busy} onClick={generateFeedback}>
                    <Icon name="sparkles" /> {feedback ? 'Regenerate' : 'Organise with AI'}
                  </button>
                )}
              </div>
              <FeedbackGrid feedback={feedback || parsed} />
              {feedback && <p className="mt-2 text-xs text-slate-500">AI organised the coach's own notes — it does not evaluate the player.</p>}
            </div>
          )}
        </section>

        <aside className="card h-fit">
          <h2 className="mb-4 text-base font-semibold">Details</h2>
          <dl className="flex flex-col gap-3 text-sm">
            {[
              ['Coach', session.coach?.name],
              ['Player', session.player?.name],
              ['When', fmtDateTime(session.startsAt)],
              ['Order', <span key="o" className="font-mono">{session.orderRef}</span>],
              ['Coach payout', session.playerConfirmed ? 'Released' : session.status === 'disputed' ? 'On hold' : session.status === 'completed' ? 'Pending confirmation' : 'After the session'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4"><dt className="text-slate-400">{k}</dt><dd className="text-right text-slate-200">{v}</dd></div>
            ))}
          </dl>
          <div className="mt-5 flex flex-col gap-2">
            <Link to={`/messages/${other?.userId}`} className="btn-secondary w-full"><Icon name="chat" /> Message {isCoach ? 'player' : 'coach'}</Link>
            {isCoach && session.player?.userId && (
              <Link to={`/passport/${session.player.userId}`} className="btn-ghost w-full"><Icon name="trophy" /> View player passport</Link>
            )}
          </div>
        </aside>
      </div>

      <Modal open={disputeOpen} onClose={() => setDisputeOpen(false)} title="Raise a dispute"
        footer={<>
          <button className="btn-ghost" onClick={() => setDisputeOpen(false)}>Cancel</button>
          <button className="btn-danger" disabled={!reason.trim() || busy}
            onClick={() => { setDisputeOpen(false); run(() => disputeSession(session.id, reason.trim()), 'Dispute raised — the coach has been notified.') }}>
            <Icon name="flag" /> Submit dispute
          </button>
        </>}>
        <p className="mb-3 text-sm text-slate-400">Describe what went wrong. The coach's payout stays on hold and they receive your message.</p>
        <textarea rows={4} className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. The coach didn't show up." autoFocus />
      </Modal>
    </div>
  )
}
