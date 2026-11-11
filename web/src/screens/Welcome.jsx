import { useNavigate } from 'react-router-dom'

export default function Welcome() {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center">
      {/* Hero */}
      <section className="w-full rounded-2xl bg-gradient-to-br from-sky-100 to-blue-200 px-6 py-16 text-center md:py-24">
        <span className="mb-4 inline-block rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-700">
          Part of BARBAH PlayEconomy
        </span>
        <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-semibold leading-tight text-gray-900 md:text-5xl">
          Find a verified esports coach. Pay fairly. Grow faster.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-gray-600">
          SightCoach connects players and teams in Kenya and Africa with experienced coaches — with transparent pricing, confirmed sessions, and fair payouts in USD.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate('/coaches')}
            className="rounded-lg bg-sky-600 px-6 py-3 text-sm font-medium text-white hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-300"
          >
            Find a coach
          </button>
          <button
            onClick={() => navigate('/register')}
            className="rounded-lg border border-sky-300 bg-white px-6 py-3 text-sm font-medium text-sky-700 hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
          >
            Sign up free
          </button>
        </div>
      </section>

      {/* How it works */}
      <section className="mt-16 w-full">
        <h2 className="mb-8 text-center text-xl font-semibold text-gray-900">How it works</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          {[
            {
              step: '1',
              title: 'Find a verified coach',
              body: 'Browse coaches filtered by game, role, and budget. Every verified coach has been reviewed by a person — not just an algorithm.',
            },
            {
              step: '2',
              title: 'Book and pay securely',
              body: 'Pay in KES via M-Pesa or card, or in USD via PayPal. The rate is locked for 15 minutes so there are no surprises.',
            },
            {
              step: '3',
              title: 'Confirm sessions, release pay',
              body: 'After each confirmed session the coach\'s payout is queued. Coaches also earn a bonus share from any prize money the team wins.',
            },
          ].map((item) => (
            <div key={item.step} className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-sky-100 text-sm font-bold text-sky-700">
                {item.step}
              </div>
              <h3 className="mb-2 font-semibold text-gray-900">{item.title}</h3>
              <p className="text-sm text-gray-600">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Trust line */}
      <section className="mt-16 w-full rounded-xl border border-gray-200 bg-white p-8 text-center">
        <p className="text-sm font-medium text-gray-700">
          "A person reviews every coach before they are verified."
        </p>
        <p className="mt-1 text-xs text-gray-400">SightCoach trust policy</p>
      </section>

      {/* CTA footer */}
      <section className="mt-12 w-full text-center">
        <p className="text-sm text-gray-500">Already have an account?</p>
        <button
          onClick={() => navigate('/login')}
          className="mt-2 text-sm font-medium text-sky-600 hover:underline"
        >
          Log in
        </button>
      </section>
    </div>
  )
}
