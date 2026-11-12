import { Icon } from './ui.jsx'

export default function EmptyState({ heading, subtext, icon = 'sparkles', action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 px-6 py-14 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-300">
        <Icon name={icon} className="h-6 w-6" />
      </div>
      <p className="font-display text-lg font-semibold text-white">{heading}</p>
      {subtext && <p className="mt-1 max-w-md text-sm text-slate-400">{subtext}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
