export default function ErrorMessage({ message }) {
  if (!message) return null
  return (
    <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <span className="mt-0.5">⚠</span>
      <span>{message}</span>
    </div>
  )
}
