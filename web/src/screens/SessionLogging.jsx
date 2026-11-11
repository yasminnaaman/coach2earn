import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { startSession, endSession, confirmSession, disputeSession } from '../api.js'
import SectionCard from '../components/SectionCard.jsx'
import StatusPill from '../components/StatusPill.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import EmptyState from '../components/EmptyState.jsx'

// Demo sessions map — in the real app these would be fetched
const DEMO_SESSIONS = {
  's-1': { id: 's-1', label: 'Gameplay assessment', status: 'Confirmed', date: '2026-11-12', proposedHours: 1 },
  's-2': { id: 's-2', label: 'Rotations and positioning', status: 'Paid', date: '2026-11-14', proposedHours: 1 },
  's-3': { id: 's-3', label: 'Team comms review', status: 'Scheduled', date: '2026-11-19', proposedHours: null },
  's-4': { id: 's-4', label: 'TBD', status: 'Scheduled', date: null, proposedHours: null },
  'new': { id: 'new', label: 'New session', status: 'Scheduled', date: null, proposedHours: null },
}

export default function SessionLogging() {
  const { id } = useParams()
  const persona = localStorage.getItem('c2e_persona') || 'gamer'
  const [session, setSession] = useState(DEMO_SESSIONS[id] || DEMO_SESSIONS['s-3'])
  const [proposedHours, setProposedHours] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function run(fn, optimisticStatus) {
    setLoading(true); setError(''); setMessage('')
    try {
      await fn()
      setSession((s) => ({ ...s, status: optimisticStatus }))
      if (optimisticStatus === 'Confirmed') setMessage('Session confirmed. Points and bonus updated.')
      if (optimisticStatus === 'Disputed') setMessage('Dispute raised. Both parties have been notified.')
    } catch {
      setError('Action failed. Try again.')
    } finally {
      setLoading(false)
    }
  }

  if (persona !== 'coach' && persona !== 'team_admin') {
    return <EmptyState heading="Switch to the coach or team admin persona to manage sessions." subtext="Use the demo persona switcher in the header." />
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Session</h1>
      <ErrorMessage message={error} />
      {message && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {message}
        </div>
      )}

      <SectionCard>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="font-semibold text-gray-900">{session.label}</p>
            {session.date && <p className="text-xs text-gray-400">{session.date}</p>}
          </div>
          <StatusPill status={session.status} />
        </div>

        {/* Coach view */}
        {persona === 'coach' && (
          <div className="flex flex-col gap-3">
            {session.status === 'Scheduled' && (
              <button disabled={loading}
                onClick={() => run(() => startSession(session.id), 'started')}
                className="rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
                Start session
              </button>
            )}
            {session.status === 'started' && (
              <button disabled={loading}
                onClick={() => run(() => endSession(session.id), 'ended')}
                className="rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
                End session
              </button>
            )}
            {session.status === 'ended' && (
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">Proposed hours</label>
                <input type="number" min="0" max="8" step="0.5" value={proposedHours}
                  onChange={(e) => setProposedHours(e.target.value)}
                  placeholder="e.g. 1.0"
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                <button disabled={loading || !proposedHours}
                  onClick={() => run(() => Promise.resolve(), 'Pending')}
                  className="rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
                  Submit hours
                </button>
              </div>
            )}
            {['Confirmed', 'Paid'].includes(session.status) && (
              <p className="text-sm text-gray-500">This session has been confirmed.</p>
            )}
          </div>
        )}

        {/* Team admin view */}
        {persona === 'team_admin' && (
          <div className="flex flex-col gap-3">
            {session.proposedHours != null && (
              <p className="text-sm text-gray-600">Proposed hours: <strong>{session.proposedHours}</strong></p>
            )}
            {!['Confirmed', 'Paid', 'Disputed'].includes(session.status) && (
              <div className="flex gap-3">
                <button disabled={loading}
                  onClick={() => run(() => confirmSession(session.id), 'Confirmed')}
                  className="flex-1 rounded-lg bg-green-600 py-2.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-60">
                  Confirm session
                </button>
                <button disabled={loading}
                  onClick={() => run(() => disputeSession(session.id), 'Disputed')}
                  className="flex-1 rounded-lg border border-gray-200 py-2.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-60">
                  Dispute
                </button>
              </div>
            )}
            {session.status === 'Confirmed' && (
              <p className="text-sm text-gray-500">Session confirmed. Coach payout is queued.</p>
            )}
            {session.status === 'Disputed' && (
              <p className="text-sm text-amber-600">Dispute raised. Both parties have been notified.</p>
            )}
          </div>
        )}
      </SectionCard>
    </div>
  )
}
