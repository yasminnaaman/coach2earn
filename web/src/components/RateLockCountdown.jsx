import { useEffect, useState } from 'react'

function pad(n) {
  return String(n).padStart(2, '0')
}

export default function RateLockCountdown({ expiresAt, onExpire }) {
  const [secondsLeft, setSecondsLeft] = useState(() => {
    return Math.max(0, Math.floor((new Date(expiresAt) - Date.now()) / 1000))
  })
  const [expired, setExpired] = useState(secondsLeft <= 0)

  useEffect(() => {
    setSecondsLeft(Math.max(0, Math.floor((new Date(expiresAt) - Date.now()) / 1000)))
    setExpired(false)
  }, [expiresAt])

  useEffect(() => {
    if (expired) return
    if (secondsLeft <= 0) {
      setExpired(true)
      onExpire?.()
      return
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [secondsLeft, expired, onExpire])

  if (expired) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        Rate expired. Refresh the quote.
      </div>
    )
  }

  const mins = Math.floor(secondsLeft / 60)
  const secs = secondsLeft % 60
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
      Rate locked for{' '}
      <span className="font-mono font-semibold">
        {pad(mins)}:{pad(secs)}
      </span>
    </div>
  )
}
