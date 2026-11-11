export default function EmptyState({ heading, subtext }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 text-3xl text-gray-300">○</div>
      <p className="font-medium text-gray-700">{heading}</p>
      {subtext && <p className="mt-1 text-sm text-gray-500">{subtext}</p>}
    </div>
  )
}
