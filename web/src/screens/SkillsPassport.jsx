import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getPassport, addEvidence } from '../api.js'
import SectionCard from '../components/SectionCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const TYPE_COLOURS = {
  ballchasing_replay: 'bg-blue-100 text-blue-700',
  tournament: 'bg-green-100 text-green-700',
  video: 'bg-amber-100 text-amber-700',
}
const TYPE_LABELS = { ballchasing_replay: 'Replay', tournament: 'Tournament', video: 'Video' }
const EVIDENCE_TYPES = ['ballchasing_replay', 'tournament', 'video']

export default function SkillsPassport() {
  const { playerId } = useParams()
  const [passport, setPassport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [evidenceForm, setEvidenceForm] = useState({ type: 'ballchasing_replay', url: '' })
  const [addingEvidence, setAddingEvidence] = useState(false)
  const [addError, setAddError] = useState('')

  useEffect(() => {
    getPassport(playerId)
      .then(setPassport)
      .catch(() => setError('Could not load passport. Try refreshing the page.'))
      .finally(() => setLoading(false))
  }, [playerId])

  async function handleAddEvidence(e) {
    e.preventDefault()
    if (!evidenceForm.url) return
    setAddingEvidence(true); setAddError('')
    try {
      const updated = await addEvidence(playerId, evidenceForm)
      setPassport((p) => ({ ...p, evidence: updated }))
      setEvidenceForm((f) => ({ ...f, url: '' }))
    } catch {
      setAddError('Could not add evidence. Check the URL and try again.')
    } finally {
      setAddingEvidence(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <div className="mt-4"><ErrorMessage message={error} /></div>
  if (!passport) return (
    <EmptyState
      heading="No passport found for this player."
      subtext="Stats and evidence will appear here once the player profile is set up."
    />
  )

  const { player, rank, replayStats, evidence = [], feedback = [] } = passport

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-gray-900">{player.name}</h1>
          <span className="rounded-full bg-sky-100 px-3 py-1 text-sm font-medium text-sky-700">{rank}</span>
        </div>
        <p className="text-sm text-gray-500">{player.game?.replace('_', ' ')}</p>
      </div>

      {/* Replay stats */}
      <SectionCard title="Replay stats">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
          {[
            { label: 'Matches', value: replayStats.matches },
            { label: 'Goals', value: replayStats.goals },
            { label: 'Saves', value: replayStats.saves },
            { label: 'Shots', value: replayStats.shots },
            { label: 'Boost/min', value: replayStats.boostPerMinute },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-2xl font-semibold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-400">{s.label}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-gray-400">Stats sourced from Ballchasing.com. Sample data used for demo.</p>
      </SectionCard>

      {/* Evidence */}
      <SectionCard title="Evidence">
        {evidence.length === 0 ? (
          <p className="text-sm text-gray-400">No evidence added yet.</p>
        ) : (
          <ul className="flex flex-col gap-3 mb-4">
            {evidence.map((ev) => (
              <li key={ev.id} className="flex items-start gap-3">
                <span className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-xs font-medium ${TYPE_COLOURS[ev.type] || 'bg-gray-100 text-gray-500'}`}>
                  {TYPE_LABELS[ev.type] || ev.type}
                </span>
                <div className="min-w-0">
                  <a href={ev.url} target="_blank" rel="noopener noreferrer"
                    className="break-all text-sm text-sky-600 hover:underline">{ev.url}</a>
                  <p className="text-xs text-gray-400">{new Date(ev.addedAt).toLocaleDateString()}</p>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Add evidence form */}
        <form onSubmit={handleAddEvidence} className="flex flex-col gap-2 border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-gray-600 mb-1">Add evidence</p>
          <ErrorMessage message={addError} />
          <div className="flex gap-2">
            <select value={evidenceForm.type}
              onChange={(e) => setEvidenceForm((f) => ({ ...f, type: e.target.value }))}
              className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300">
              {EVIDENCE_TYPES.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
            <input type="url" value={evidenceForm.url} required
              onChange={(e) => setEvidenceForm((f) => ({ ...f, url: e.target.value }))}
              placeholder="https://..."
              className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300" />
            <button type="submit" disabled={addingEvidence}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60">
              {addingEvidence ? '…' : 'Add'}
            </button>
          </div>
        </form>
      </SectionCard>

      {/* Coach feedback history */}
      <SectionCard title="Coach feedback">
        {feedback.length === 0 ? (
          <p className="text-sm text-gray-400">No feedback recorded yet.</p>
        ) : (
          <div className="flex flex-col gap-5">
            {feedback.map((fb) => (
              <div key={fb.sessionId} className="rounded-lg border border-gray-100 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-800">{fb.coachName}</span>
                  <span className="text-xs text-gray-400">{new Date(fb.date).toLocaleDateString()}</span>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Strengths', items: fb.strengths, colour: 'text-green-700' },
                    { label: 'Focus areas', items: fb.focusAreas, colour: 'text-amber-700' },
                    { label: 'Next goals', items: fb.nextGoals, colour: 'text-sky-700' },
                  ].map(({ label, items, colour }) => (
                    <div key={label}>
                      <p className={`mb-1 text-xs font-medium uppercase tracking-wide ${colour}`}>{label}</p>
                      <ul className="list-disc pl-4 text-sm text-gray-700 space-y-1">
                        {items.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  )
}
