const COLOURS = {
  Confirmed: 'bg-green-100 text-green-700',
  Paid: 'bg-green-100 text-green-700',
  Scheduled: 'bg-amber-100 text-amber-700',
  'Pending win': 'bg-blue-100 text-blue-700',
  Disputed: 'bg-red-100 text-red-700',
  Pending: 'bg-gray-100 text-gray-600',
}

export default function StatusPill({ status }) {
  const cls = COLOURS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  )
}
