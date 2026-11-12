import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { approveSubmission, getReviewQueue, rejectSubmission, requestMoreEvidence } from '../api.js'
import { currentRole } from '../auth.js'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { Avatar, Icon, Modal, PageHeader, Spinner, Stat, fmtDate, useToast } from '../components/ui.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const DECISIONS = {
  approved: { title: 'Approve submission', button: 'Approve', cls: 'btn-success', placeholder: 'Optional note for the record', required: false, toast: 'Approved — the coach has been notified.' },
  rejected: { title: 'Reject submission', button: 'Reject', cls: 'btn-danger', placeholder: 'Reason for rejection (shared with the coach)', required: true, toast: 'Submission rejected.' },
  needs_more_evidence: { title: 'Request more evidence', button: 'Send request', cls: 'btn-warning', placeholder: 'What else should the coach provide?', required: true, toast: 'Request for more evidence sent.' },
}

export default function ReviewQueue() {
  const isAdmin = currentRole() === 'ADMIN'
  const toast = useToast()
  const [queue, setQueue] = useState([])
  const [decided, setDecided] = useState({})
  const [loading, setLoading] = useState(isAdmin)
  const [error, setError] = useState('')
  const [action, setAction] = useState(null) // { id, kind }
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      setQueue(await getReviewQueue())
      setDecided({})
    } catch (e) {
      setError(e.message || 'Could not load the review queue. Try refreshing.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) load()
  }, [isAdmin])

  async function decide() {
    const cfg = DECISIONS[action.kind]
    if (cfg.required && !note.trim()) return
    setBusy(true)
    try {
      const fn = { approved: approveSubmission, rejected: rejectSubmission, needs_more_evidence: requestMoreEvidence }[action.kind]
      await fn(action.id, { notes: note.trim(), reason: note.trim() })
      setDecided((d) => ({ ...d, [action.id]: action.kind }))
      toast(cfg.toast)
      setAction(null)
      setNote('')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  if (!isAdmin) {
    return (
      <EmptyState icon="shield" heading="The review queue is for admins"
        subtext={USE_MOCK ? 'Switch the demo persona to “reviewer” in the header.' : 'Log in with an admin account to review coaches.'}
        action={!USE_MOCK && <Link to="/login" className="btn-primary">Log in as admin</Link>} />
    )
  }
  if (loading) return <LoadingSpinner label="Loading review queue…" />

  const pending = queue.filter((q) => !decided[q.id])
  const cfg = action ? DECISIONS[action.kind] : null

  return (
    <div>
      <PageHeader eyebrow="Trust & safety" title="Verification queue"
        subtitle="Evidence is organised automatically — a person makes every decision."
        actions={<button className="btn-secondary" onClick={load}><Icon name="refresh" /> Refresh</button>} />

      <div className="mb-6 flex items-center gap-3 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.06] px-4 py-3 text-sm font-medium text-cyan-100">
        <Icon name="shield" className="h-5 w-5 shrink-0" /> A person reviews every coach before they are verified.
      </div>

      <div className="mb-6 grid grid-cols-3 gap-4">
        <Stat label="Pending" value={pending.length} icon="clock" tone="amber" />
        <Stat label="Decided now" value={Object.keys(decided).length} icon="check" tone="emerald" />
        <Stat label="Total in queue" value={queue.length} icon="shield" tone="violet" />
      </div>

      <ErrorMessage message={error} />

      {queue.length === 0 ? (
        <EmptyState icon="check" heading="The queue is empty" subtext="No submissions pending review. Nice work!" />
      ) : (
        <div className="flex flex-col gap-4">
          {queue.map((sub) => {
            const status = decided[sub.id]
            return (
              <section key={sub.id} className={`card transition ${status ? 'opacity-60' : ''}`}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={sub.coachName} />
                    <div>
                      <p className="font-semibold text-white">{sub.coachName}</p>
                      <p className="text-xs text-slate-400">Submitted {fmtDate(sub.submittedAt)}</p>
                    </div>
                  </div>
                  <StatusPill status={status || 'pending'} />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {sub.claims?.length > 0 && (
                    <div>
                      <p className="label">Claims</p>
                      <ul className="flex flex-col gap-1 text-sm text-slate-200">
                        {sub.claims.map((c, i) => <li key={i} className="flex gap-2"><Icon name="star" className="mt-1 h-3.5 w-3.5 shrink-0 text-violet-300" />{c}</li>)}
                      </ul>
                    </div>
                  )}
                  {sub.sources?.length > 0 && (
                    <div>
                      <p className="label">Sources</p>
                      <ul className="flex flex-col gap-1 text-sm">
                        {sub.sources.map((s, i) => (
                          <li key={i} className="truncate">
                            <a href={s.url} target="_blank" rel="noopener noreferrer" className="link">{s.url}</a>
                            {s.description && <span className="text-slate-500"> — {s.description}</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {(sub.gaps?.length > 0 || sub.redFlags?.length > 0) && (
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {sub.gaps?.length > 0 && (
                      <div className="rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3">
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-300">Gaps</p>
                        <ul className="list-disc pl-4 text-sm text-amber-100">{sub.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
                      </div>
                    )}
                    {sub.redFlags?.length > 0 && (
                      <div className="rounded-xl border border-rose-400/20 bg-rose-500/[0.06] p-3">
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-rose-300">Red flags</p>
                        <ul className="list-disc pl-4 text-sm text-rose-100">{sub.redFlags.map((f, i) => <li key={i}>{f}</li>)}</ul>
                      </div>
                    )}
                  </div>
                )}

                {sub.summary && <div className="mt-4 rounded-xl bg-white/[0.03] p-3 text-sm text-slate-300">{sub.summary}</div>}

                {!status && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button onClick={() => setAction({ id: sub.id, kind: 'approved' })} className="btn-success"><Icon name="check" /> Approve</button>
                    <button onClick={() => setAction({ id: sub.id, kind: 'rejected' })} className="btn-danger"><Icon name="x" /> Reject</button>
                    <button onClick={() => setAction({ id: sub.id, kind: 'needs_more_evidence' })} className="btn-warning"><Icon name="flag" /> Needs more evidence</button>
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}

      <Modal open={!!action} onClose={() => setAction(null)} title={cfg?.title}
        footer={<>
          <button className="btn-ghost" onClick={() => setAction(null)}>Cancel</button>
          <button className={cfg?.cls} onClick={decide} disabled={busy || (cfg?.required && !note.trim())}>
            {busy && <Spinner />} {cfg?.button}
          </button>
        </>}>
        <textarea rows={4} className="input" value={note} onChange={(e) => setNote(e.target.value)} placeholder={cfg?.placeholder} autoFocus />
        {cfg?.required && <p className="mt-2 text-xs text-slate-500">Required.</p>}
      </Modal>
    </div>
  )
}
