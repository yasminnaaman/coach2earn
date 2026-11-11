import { useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { scheduleSession } from '../api.js'
import SectionCard from '../components/SectionCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

function formatDate(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
}

function generateIcs(sessions) {
  const events = sessions
    .filter((s) => s.startsAt)
    .map((s) => {
      const start = new Date(s.startsAt)
      const end = new Date(start.getTime() + 60 * 60 * 1000)
      const fmt = (d) =>
        d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z'
      return [
        'BEGIN:VEVENT',
        `DTSTART:${fmt(start)}`,
        `DTEND:${fmt(end)}`,
        `SUMMARY:Coach2Earn — ${s.label || 'Coaching session'}`,
        `DESCRIPTION:Coaching session with Coach Dani K.`,
        'END:VEVENT',
      ].join('\r\n')
    })
    .join('\r\n')

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Coach2Earn//EN',
    events,
    'END:VCALENDAR',
  ].join('\r\n')
}

function ScheduleModal({ sessions, onClose }) {
  const unscheduled = sessions.filter((s) => !s.startsAt)
  const [dates, setDates] = useState({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await Promise.all(
        unscheduled.map((s) => dates[s.id] && scheduleSession(s.id, { startsAt: new Date(dates[s.id]).toISOString() }))
      )
      onClose()
    } catch {
      setError('Could not schedule sessions. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Schedule remaining sessions</h2>
        <ErrorMessage message={error} />
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-3">
          {unscheduled.map((s) => (
            <div key={s.id}>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {s.label || 'Session'}
              </label>
              <input type="date" value={dates[s.id] || ''}
                onChange={(e) => setDates((d) => ({ ...d, [s.id]: e.target.value }))}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
          ))}
          <div className="mt-2 flex gap-3">
            <button type="submit" disabled={saving}
              className="flex-1 rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
              {saving ? 'Saving…' : 'Save schedule'}
            </button>
            <button type="button" onClick={onClose}
              className="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Confirmation() {
  const location = useLocation()
  const receipt = location.state?.receipt

  const [showModal, setShowModal] = useState(false)

  if (!receipt) {
    return (
      <EmptyState
        heading="No booking found."
        subtext="Go back and complete checkout."
      />
    )
  }

  function handleAddToCalendar() {
    const ics = generateIcs(receipt.bookedSessions)
    const blob = new Blob([ics], { type: 'text/calendar' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'coach2earn-sessions.ics'
    a.click()
    URL.revokeObjectURL(url)
  }

  const scheduled = receipt.bookedSessions.filter((s) => s.startsAt)
  const unscheduled = receipt.bookedSessions.filter((s) => !s.startsAt)

  return (
    <div>
      {/* Success header */}
      <div className="mb-8 flex flex-col items-center text-center">
        <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
          <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-gray-900">Payment received</h1>
        <p className="mt-1 text-sm text-gray-600">
          Your {receipt.bookedSessions.length} sessions with Coach {receipt.coachName} are booked.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Sessions card */}
        <SectionCard title="Your sessions">
          <ul className="flex flex-col gap-3">
            {receipt.bookedSessions.map((s) => (
              <li key={s.id} className="flex items-center gap-3">
                <div className={`flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-lg border text-xs font-medium
                  ${s.startsAt ? 'border-indigo-200 bg-indigo-50 text-indigo-700' : 'border-gray-200 bg-gray-50 text-gray-400'}`}>
                  {s.startsAt ? (
                    <>
                      <span>{new Date(s.startsAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>
                      <span>{new Date(s.startsAt).toLocaleDateString('en-GB', { weekday: 'short' })}</span>
                    </>
                  ) : (
                    <span>TBD</span>
                  )}
                </div>
                <span className="text-sm text-gray-700">{s.label || 'To be scheduled'}</span>
              </li>
            ))}
          </ul>
          <div className="mt-5 flex gap-3">
            <button onClick={handleAddToCalendar}
              className="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Add to calendar
            </button>
            {unscheduled.length > 0 && (
              <button onClick={() => setShowModal(true)}
                className="flex-1 rounded-lg border border-indigo-200 py-2 text-sm text-indigo-600 hover:bg-indigo-50">
                Schedule rest
              </button>
            )}
          </div>
        </SectionCard>

        {/* Receipt card */}
        <SectionCard title="Receipt">
          <dl className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Reference</dt>
              <dd className="font-mono font-medium text-gray-900">{receipt.receiptRef}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Paid with</dt>
              <dd className="text-gray-700 capitalize">{receipt.paidWith?.replace('_', ' ')}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Package</dt>
              <dd className="text-gray-700">{receipt.packageLabel}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Platform fee</dt>
              <dd className="text-gray-700">${receipt.platformFee?.toFixed(2)}</dd>
            </div>
            <div className="flex justify-between border-t border-gray-100 pt-2 font-semibold">
              <dt>Total paid</dt>
              <dd>{receipt.currency === 'KES'
                ? `KES ${receipt.totalPaidKes?.toLocaleString()}`
                : `USD ${receipt.totalPaidUsd?.toFixed(2)}`}
              </dd>
            </div>
            {receipt.rateUsed && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Rate used</dt>
                <dd className="text-xs text-gray-400">{receipt.rateUsed}</dd>
              </div>
            )}
          </dl>

          {/* Badges */}
          <div className="mt-4 flex flex-col gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1.5 text-xs font-medium text-green-700">
              ✓ Bonus terms signed by both parties
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700">
              ● Coach payout releases after each confirmed session
            </span>
          </div>

          <div className="mt-5 flex gap-3">
            <button onClick={() => window.print()}
              className="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Receipt
            </button>
            <button onClick={() => alert('Messaging coming soon.')}
              className="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Message coach
            </button>
          </div>
        </SectionCard>
      </div>

      {showModal && (
        <ScheduleModal sessions={receipt.bookedSessions} onClose={() => setShowModal(false)} />
      )}
    </div>
  )
}
