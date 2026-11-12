import { useEffect, useMemo, useState } from 'react'
import { getCoaches, matchCoaches } from '../api.js'
import CoachCard from '../components/CoachCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Icon, PageHeader } from '../components/ui.jsx'

const GAMES = [
  { value: 'rocket_league', label: 'Rocket League' },
  { value: 'fifa', label: 'EA FC / FIFA' },
  { value: 'valorant', label: 'Valorant' },
]
const GOAL_IDEAS = ['rotations', 'aerials', 'boost management', 'mental game', 'team communication']
const EMPTY = { game: 'rocket_league', budgetUsd: '', goal: '' }

export default function Discover() {
  const [coaches, setCoaches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState(EMPTY)
  const [searched, setSearched] = useState(false)
  const [sort, setSort] = useState('match')

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    setError('')
    setSearched(false)
    try {
      setCoaches(await getCoaches({}))
    } catch (e) {
      setError(e.message || 'Could not load coaches. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch(e) {
    e?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const budget = filters.budgetUsd ? Number(filters.budgetUsd) : 999
      const data = await matchCoaches({ game: filters.game, role: '', goal: filters.goal.trim(), budgetUsd: budget })
      setCoaches(filters.budgetUsd ? data.filter((c) => c.priceUsd <= budget) : data)
      setSearched(true)
    } catch (e) {
      setError(e.message || 'Could not search coaches. Try again.')
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setFilters(EMPTY)
    loadAll()
  }

  const sorted = useMemo(() => {
    const list = [...coaches]
    if (sort === 'price') list.sort((a, b) => a.priceUsd - b.priceUsd)
    else if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    else list.sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    return list
  }, [coaches, sort])

  const set = (field) => (e) => setFilters((f) => ({ ...f, [field]: e.target.value }))

  return (
    <div>
      <PageHeader
        eyebrow="Coach discovery"
        title="Find your coach"
        subtitle="Search verified coaches by game, goal and budget. Our matcher ranks them and explains why."
      />

      <form onSubmit={handleSearch} className="card mb-8 animate-fade-up">
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_2fr_auto] md:items-end">
          <div>
            <label className="label" htmlFor="f-game">Game</label>
            <select id="f-game" value={filters.game} onChange={set('game')} className="input">
              {GAMES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-budget">Max $ / session</label>
            <input id="f-budget" type="number" min="0" value={filters.budgetUsd} onChange={set('budgetUsd')} placeholder="Any" className="input" />
          </div>
          <div>
            <label className="label" htmlFor="f-goal">Your goal</label>
            <input id="f-goal" type="text" value={filters.goal} onChange={set('goal')} placeholder="e.g. improve rotations" className="input" />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary flex-1 md:flex-none"><Icon name="sparkles" /> Match me</button>
            <button type="button" onClick={reset} className="btn-secondary" title="Show all coaches"><Icon name="refresh" /></button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Try:</span>
          {GOAL_IDEAS.map((g) => (
            <button key={g} type="button" onClick={() => setFilters((f) => ({ ...f, goal: g }))}
              className={`chip ring-1 ring-inset transition ${filters.goal === g ? 'bg-violet-500/20 text-violet-200 ring-violet-400/40' : 'bg-white/5 text-slate-400 ring-white/10 hover:text-white'}`}>
              {g}
            </button>
          ))}
        </div>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <LoadingSpinner label="Finding coaches…" />
      ) : sorted.length === 0 ? (
        <EmptyState
          icon="search"
          heading="No coaches match your filters"
          subtext={filters.game !== 'rocket_league' ? 'We currently only have Rocket League coaches — more games are coming soon.' : 'Try a higher budget or a different goal.'}
          action={<button onClick={reset} className="btn-secondary">Show all coaches</button>}
        />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-400">
              <span className="font-semibold text-white">{sorted.length}</span> {searched ? 'matched' : 'verified'} coach{sorted.length !== 1 && 'es'}
            </p>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Sort</span>
              {[['match', 'Best match'], ['price', 'Price'], ['name', 'Name']].map(([k, l]) => (
                <button key={k} onClick={() => setSort(k)}
                  className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${sort === k ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {sorted.map((coach, i) => <CoachCard key={coach.coachId} coach={coach} index={i} />)}
          </div>
        </>
      )}
    </div>
  )
}
