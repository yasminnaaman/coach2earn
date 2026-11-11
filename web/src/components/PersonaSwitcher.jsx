const PERSONAS = ['gamer', 'coach', 'team_admin', 'reviewer']

export default function PersonaSwitcher({ persona, onChange }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-gray-500">Demo persona:</span>
      <select
        value={persona}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-200 bg-white px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
      >
        {PERSONAS.map((p) => (
          <option key={p} value={p}>
            {p.replace('_', ' ')}
          </option>
        ))}
      </select>
    </div>
  )
}
