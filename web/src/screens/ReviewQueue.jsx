import { useState, useEffect } from 'react'
import { getReviewQueue, approveSubmission, rejectSubmission } from '../api.js'
import SectionCard from '../components/SectionCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

function RejectModal({ onConfirm, onClose }) {
  const [reason, setReason] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-3 text-base font-semibold text-gray-900">Reject submission</h2>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)}
          rows={3} placeholder="Reason for rejection"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
        <div className="mt-3 flex gap-3">
          <button onClick={() => onConfirm(reason)}
            className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700">
            Reject
          </button>
          <button onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-600 hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ReviewQueue() {
  const persona = localStorage.getItem('c2e_persona') || 'gamer'
  const [queue, setQueue] = useState([])
  const [statuses, setStatuses] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [rejectTarget, setRejectTarget] = useState(null)

  useEffect(() => {
    if (persona !== 'reviewer') { setLoading(false); return }
    getReviewQueue()
      .then(setQueue)
      .catch(() => setError('Could not load the review queue. Try refreshing.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleApprove(id) {
    try {
      await approveSubmission(id)
      setStatuses((s) => ({ ...s, [id]: 'approved' }))
    } catch {
      setError('Approval failed. Try again.')
    }
  }

  async function handleReject(id, reason) {
    try {
      await rejectSubmission(id, { reason })
      setStatuses((s) => ({ ...s, [id]: 'rejected' }))
      setRejectTarget(null)
    } catch {
      setError('Rejection failed. Try again.')
    }
  }

  if (persona !== 'reviewer') {
    return <EmptyState heading="Switch to the reviewer persona to view the queue." subtext="Use the demo persona switcher in the header." />
  }
  if (loading) return <LoadingSpinner />

  return (
    <div>
      {/* Required banner — must appear before any AI content */}
      <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-800">
        A person reviews every coach before they are verified.
      </div>

      <h1 className="mb-4 text-2xl font-semibold text-gray-900">Verification queue</h1>
      <ErrorMessage message={error} />

      {queue.length === 0 ? (
        <EmptyState heading="The queue is empty." subtext="No submissions pending review." />
      ) : (
        <div className="flex flex-col gap-6">
          {queue.map((sub) => {
            const status = statuses[sub.id]
            return (
              <SectionCard key={sub.id}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-semibold text-gray-900">{sub.coachName}</p>
                    <p className="text-xs text-gray-400">Submitted {new Date(sub.submittedAt).toLocaleDateString()}</p>
                  </div>
                  {status === 'approved' && (
                    <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">Approved</span>
                  )}
                  {status === 'rejected' && (
                    <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">Rejected</span>
                  )}
                </div>

                {/* Claims */}
                {sub.claims?.length > 0 && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">Claims</p>
                    <ul className="list-disc pl-4 text-sm text-gray-700 space-y-0.5">
                      {sub.claims.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}

                {/* Sources */}
                {sub.sources?.length > 0 && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">Sources</p>
                    <ul className="flex flex-col gap-1">
                      {sub.sources.map((s, i) => (
                        <li key={i} className="text-sm">
                          <a href={s.url} target="_blank" rel="noopener noreferrer"
                            className="text-indigo-600 hover:underline">{s.url}</a>
                          {s.description && <span className="ml-2 text-gray-500">— {s.description}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Gaps */}
                {sub.gaps?.length > 0 && (
                  <div className="mb-3 rounded-lg bg-amber-50 p-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-amber-600">Gaps</p>
                    <ul className="list-disc pl-4 text-sm text-amber-800 space-y-0.5">
                      {sub.gaps.map((g, i) => <li key={i}>{g}</li>)}
                    </ul>
                  </div>
                )}

                {/* Red flags */}
                {sub.redFlags?.length > 0 && (
                  <div className="mb-3 rounded-lg bg-red-50 p-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-red-600">Red flags</p>
                    <ul className="list-disc pl-4 text-sm text-red-700 space-y-0.5">
                      {sub.redFlags.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}

                {/* AI summary */}
                {sub.summary && (
                  <div className="mb-4 rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
                    {sub.summary}
                  </div>
                )}

                {/* Actions */}
                {!status && (
                  <div className="flex gap-3">
                    <button onClick={() => handleApprove(sub.id)}
                      className="flex-1 rounded-lg bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700">
                      Approve
                    </button>
                    <button onClick={() => setRejectTarget(sub.id)}
                      className="flex-1 rounded-lg border border-red-200 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
                      Reject
                    </button>
                    <button onClick={() => alert('Request sent to coach.')}
                      className="flex-1 rounded-lg border border-amber-200 py-2 text-sm font-medium text-amber-600 hover:bg-amber-50">
                      Needs more evidence
                    </button>
                  </div>
                )}
              </SectionCard>
            )
          })}
        </div>
      )}

      {rejectTarget && (
        <RejectModal
          onConfirm={(reason) => handleReject(rejectTarget, reason)}
          onClose={() => setRejectTarget(null)}
        />
      )}
    </div>
  )
}
