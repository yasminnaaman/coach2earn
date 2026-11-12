import { useEffect, useState } from 'react'

const pad = (n) => String(n).padStart(2, '0')
const secondsUntil = (iso) => Math.max(0, Math.floor((new Date(iso) - Date.now()) / 1000))

export default function RateLockCountdown({ expiresAt, onExpire }) {
  const [secondsLeft, setSecondsLeft] = useState(() => secondsUntil(expiresAt))

  useEffect(() => {
    setSecondsLeft(secondsUntil(expiresAt))
    const t = setInterval(() => {
      const left = secondsUntil(expiresAt)
      setSecondsLeft(left)
      if (left <= 0) {
        clearInterval(t)
        onExpire?.()
      }
    }, 1000)
    return () => clearInterval(t)
  }, [expiresAt, onExpire])

  if (secondsLeft <= 0) {
    return (
      <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
        Rate expired — refreshing your quote…
      </div>
    )
  }
  const pct = Math.min(100, (secondsLeft / 900) * 100)
  return (
    <div className="rounded-xl border border-amber-400/20 bg-amber-400/[0.07] px-4 py-3 text-sm text-amber-200">
      <div className="flex items-center justify-between">
        <span>Rate locked</span>
        <span className="font-mono font-semibold">{pad(Math.floor(secondsLeft / 60))}:{pad(secondsLeft % 60)}</span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-amber-400/10">
        <div className="h-full rounded-full bg-amber-300 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
