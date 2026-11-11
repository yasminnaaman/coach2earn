export default function VerifiedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
      <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
        <path d="M6 0L7.5 2h2.5v2.5L12 6l-2 1.5V10H7.5L6 12l-1.5-2H2V7.5L0 6l2-1.5V2h2.5L6 0z" />
        <path d="M4.5 6l1 1 2.5-2.5" stroke="white" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Verified
    </span>
  )
}
