export default function SectionCard({ title, children, className = '' }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-6 ${className}`}>
      {title && <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">{title}</h2>}
      {children}
    </div>
  )
}
