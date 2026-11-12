import { useEffect, useState } from 'react'
import { scheduleOrderSessions } from '../api.js'
import ErrorMessage from './ErrorMessage.jsx'
import { Icon, Modal, Spinner, useToast } from './ui.jsx'

// datetime-local wants "YYYY-MM-DDTHH:mm" in local time.
function toLocalInput(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function suggestions(count) {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() + 2 + i * 3)
    d.setHours(18, 0, 0, 0)
    return toLocalInput(d)
  })
}

// Pick times for the remaining sessions on a paid order.
export default function ScheduleModal({ open, order, onClose, onScheduled }) {
  const toast = useToast()
  const remaining = order?.remaining || 0
  const [slots, setSlots] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setSlots(suggestions(Math.min(remaining, 3)))
      setError('')
    }
  }, [open, remaining])

  const min = toLocalInput(new Date(Date.now() + 60 * 60 * 1000))

  async function save() {
    const chosen = slots.filter(Boolean)
    if (!chosen.length) return setError('Pick at least one date and time.')
    setSaving(true)
    setError('')
    try {
      const updated = await scheduleOrderSessions(order.orderId, chosen.map((s) => new Date(s).toISOString()))
      toast(`${chosen.length} session${chosen.length > 1 ? 's' : ''} scheduled!`)
      onScheduled?.(updated)
      onClose()
    } catch (e) {
      setError(e.message || 'Could not schedule sessions. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Schedule sessions"
      footer={<>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={save} disabled={saving}>
          {saving ? <Spinner /> : <Icon name="calendar" />} Save {slots.filter(Boolean).length || ''} session{slots.filter(Boolean).length === 1 ? '' : 's'}
        </button>
      </>}>
      <p className="mb-4 text-sm text-slate-400">
        {remaining} session{remaining === 1 ? '' : 's'} left on <span className="text-white">{order?.packageTitle}</span>.
        Each session is 60 minutes, times are in your local timezone.
      </p>
      <div className="flex flex-col gap-3">
        {slots.map((value, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-24 shrink-0 text-xs font-semibold uppercase tracking-wider text-slate-500">Session {i + 1}</span>
            <input type="datetime-local" className="input" value={value} min={min}
              onChange={(e) => setSlots((s) => s.map((x, j) => (j === i ? e.target.value : x)))} />
            <button className="btn-ghost btn-sm" onClick={() => setSlots((s) => s.filter((_, j) => j !== i))} aria-label="Remove">
              <Icon name="x" />
            </button>
          </div>
        ))}
      </div>
      {slots.length < remaining && (
        <button className="btn-secondary btn-sm mt-3" onClick={() => setSlots((s) => [...s, suggestions(s.length + 1)[s.length]])}>
          <Icon name="plus" /> Add another session
        </button>
      )}
      <div className="mt-4"><ErrorMessage message={error} /></div>
    </Modal>
  )
}
