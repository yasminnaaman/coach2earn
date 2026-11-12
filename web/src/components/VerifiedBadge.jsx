export default function VerifiedBadge() {
  return (
    <span className="chip bg-cyan-400/10 text-cyan-300 ring-1 ring-inset ring-cyan-400/30" title="Reviewed by a person on our team">
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 2l2.4 1.8 3-.2.9 2.9 2.5 1.7-1 2.8 1 2.8-2.5 1.7-.9 2.9-3-.2L12 22l-2.4-1.8-3 .2-.9-2.9-2.5-1.7 1-2.8-1-2.8 2.5-1.7.9-2.9 3 .2L12 2z" />
        <path d="M8.5 12.2l2.3 2.3 4.7-4.8" stroke="#0e1424" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Verified
    </span>
  )
}
