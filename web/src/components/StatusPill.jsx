// Status badge for sessions, orders and reviews. Accepts API values
// ("scheduled", "completed") or display labels ("Confirmed", "Pending win").
const STYLES = {
  confirmed: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  paid: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  completed: 'bg-sky-500/15 text-sky-300 ring-sky-400/30',
  approved: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  scheduled: 'bg-violet-500/15 text-violet-300 ring-violet-400/30',
  started: 'bg-cyan-500/15 text-cyan-300 ring-cyan-400/30',
  'in progress': 'bg-cyan-500/15 text-cyan-300 ring-cyan-400/30',
  pending: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  'pending win': 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  'awaiting confirmation': 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  ended: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  needs_more_evidence: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  disputed: 'bg-rose-500/15 text-rose-300 ring-rose-400/30',
  rejected: 'bg-rose-500/15 text-rose-300 ring-rose-400/30',
  cancelled: 'bg-slate-500/15 text-slate-400 ring-slate-400/20',
}

export default function StatusPill({ status, label }) {
  const key = String(status || '').toLowerCase()
  const cls = STYLES[key] || 'bg-slate-500/15 text-slate-300 ring-slate-400/20'
  const text = label || String(status || '').replace(/_/g, ' ')
  return (
    <span className={`chip ring-1 ring-inset capitalize ${cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {text}
    </span>
  )
}
