// Human label + pill key for a session from the API.
//   scheduled → Scheduled · confirmed → In progress (coach started it)
//   completed → Awaiting confirmation until the player confirms → Confirmed
export function sessionStatus(s) {
  if (s.status === 'completed') {
    return s.playerConfirmed
      ? { key: 'confirmed', label: 'Confirmed' }
      : { key: 'awaiting confirmation', label: 'Awaiting confirmation' }
  }
  if (s.status === 'confirmed') return { key: 'in progress', label: 'In progress' }
  return { key: s.status, label: s.status.charAt(0).toUpperCase() + s.status.slice(1) }
}
