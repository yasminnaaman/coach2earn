import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCoaches, matchCoaches } from '../api.js'
import CoachCard from '../components/CoachCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const GAMES = [
  { value: '', label: 'All games' },
  { value: 'rocket_league', label: 'Rocket League' },
  { value: 'fifa', label: 'FIFA' },
  { value: 'valorant', label: 'Valorant' },
]

const ROLES = [
  { value: '', label: 'All roles' },
  { value: 'forward', label: 'Forward' },
  { value: 'goalkeeper', label: 'Goalkeeper' },
  { value: 'duelist', label: 'Duelist' },
]

export default function Discover() {
  const [coaches, setCoaches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ game: '', role: '', budgetUsd: '', goal: '' })

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    setError('')
    try {
      const data = await getCoaches({})
      setCoaches(data)
    } catch (e) {
      setError('Could not load coaches. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const body = {
        game: filters.game || 'rocket_league',
        role: filters.role || 'forward',
        goal: filters.goal || '',
        budgetUsd: filters.budgetUsd ? Number(filters.budgetUsd) : 999,
      }
      const data = await matchCoaches(body)
      setCoaches(data)
    } catch (e) {
      setError('Could not search coaches. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  function set(field) {
    return (e) => setFilters((f) => ({ ...f, [field]: e.target.value }))
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-gray-900">Find a coach</h1>
      <p className="mb-6 text-sm text-gray-500">Browse verified coaches for your game and goal.</p>

      {/* Filter form */}
      <form onSubmit={handleSearch} className="mb-8 rounded-xl border border-gray-200 bg-white p-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Game</label>
            <select value={filters.game} onChange={set('game')}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300">
              {GAMES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Role</label>
            <select value={filters.role} onChange={set('role')}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300">
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Max budget (USD/session)</label>
            <input type="number" value={filters.budgetUsd} onChange={set('budgetUsd')} placeholder="e.g. 50"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Goal</label>
            <input type="text" value={filters.goal} onChange={set('goal')} placeholder="e.g. improve rotations"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300" />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button type="submit"
            className="rounded-lg bg-sky-600 px-5 py-2 text-sm font-medium text-white hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-300">
            Find coaches
          </button>
        </div>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <LoadingSpinner />
      ) : coaches.length === 0 ? (
        <EmptyState
          heading="No coaches match your filters."
          subtext="Try a wider budget or different role."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {coaches.map((coach) => (
            <CoachCard key={coach.coachId} coach={coach} />
          ))}
        </div>
      )}
    </div>
  )
}
