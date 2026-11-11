import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { getCoach, createQuote, createOrder, captureOrder } from '../api.js'
import VerifiedBadge from '../components/VerifiedBadge.jsx'
import SectionCard from '../components/SectionCard.jsx'
import RateLockCountdown from '../components/RateLockCountdown.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const METHODS = [
  { id: 'mpesa_sim', label: 'M-Pesa (simulated — demo only)', note: '1 USD = 129.00 KES (est.)' },
  { id: 'card', label: 'Card', note: '1 USD = 129.00 KES (est.)' },
  { id: 'paypal_balance', label: 'PayPal balance', note: 'No conversion needed' },
]

function CoachAvatar({ name }) {
  const initials = name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-sky-100 text-sm font-bold text-sky-700">
      {initials}
    </div>
  )
}

export default function Checkout() {
  const { packageId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [coach, setCoach] = useState(null)
  const [pkg, setPkg] = useState(null)
  const [method, setMethod] = useState('mpesa_sim')
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState('')

  // On mount: load coach + package, then get initial quote
  useEffect(() => {
    async function init() {
      try {
        // coach-001 has pkg-001 — for mock we derive coachId from packageId mapping
        const coachData = await getCoach('coach-001')
        setCoach(coachData)
        const foundPkg = coachData.packages?.find((p) => p.id === packageId) || coachData.packages?.[0]
        setPkg(foundPkg)
        const q = await createQuote({ packageId: foundPkg?.id || packageId, paymentMethod: 'mpesa_sim' })
        setQuote(q)
      } catch (e) {
        setError('Could not load checkout. Go back and try again.')
      } finally {
        setLoading(false)
      }
    }

    // If returning from PayPal with token/orderId — capture immediately
    const token = searchParams.get('token') || searchParams.get('orderId')
    if (token) {
      captureOrder(token)
        .then((receipt) => navigate('/confirmation', { state: { receipt } }))
        .catch(() => setError('Payment capture failed. Try again or choose a different payment method.'))
      return
    }

    init()
  }, [packageId])

  const refreshQuote = useCallback(async () => {
    try {
      const q = await createQuote({ packageId: pkg?.id || packageId, paymentMethod: method })
      setQuote(q)
    } catch {
      setError('Could not refresh the quote. Try again.')
    }
  }, [method, pkg, packageId])

  async function handleMethodChange(newMethod) {
    setMethod(newMethod)
    try {
      const q = await createQuote({ packageId: pkg?.id || packageId, paymentMethod: newMethod })
      setQuote(q)
    } catch {
      // non-fatal — keep existing quote
    }
  }

  async function handlePay() {
    setPaying(true)
    setError('')
    try {
      const order = await createOrder({ quoteId: quote?.id })
      // In mock mode approvalUrl is the confirmation page directly
      window.location.href = order.approvalUrl
    } catch (e) {
      setError('Payment could not be processed. Try again or choose a different payment method.')
      setPaying(false)
    }
  }

  const isKes = method !== 'paypal_balance'
  const youPay = isKes
    ? `KES ${quote?.amountKes?.toLocaleString() || '20,898'}`
    : `USD ${quote?.amountUsd?.toFixed(2) || '162.00'}`
  const rateNote = isKes ? '1 USD = 129.00 KES (est.)' : 'No conversion needed'

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Checkout</h1>
      <ErrorMessage message={error} />

      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Left — order summary */}
        <SectionCard title="Order summary">
          {coach && (
            <div className="mb-4 flex items-center gap-3">
              <CoachAvatar name={coach.name} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{coach.name}</span>
                  {coach.verified && <VerifiedBadge />}
                </div>
                <p className="text-xs text-gray-500">{coach.endorsementCount} endorsements</p>
              </div>
            </div>
          )}

          {/* Package lines */}
          {pkg && (
            <div className="flex flex-col gap-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">{pkg.sessions} sessions × ${pkg.pricePerSession.toFixed(2)}</span>
                <span>${pkg.subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>Platform fee ({pkg.platformFeePct}%)</span>
                <span>${pkg.platformFee.toFixed(2)}</span>
              </div>
              <div className="flex justify-between border-t border-gray-100 pt-2 font-semibold">
                <span>Total</span>
                <span>${pkg.total.toFixed(2)} USD</span>
              </div>
            </div>
          )}

          {/* Bonus terms */}
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            Coach earns up to 10% of prize money, based on confirmed hours. Paid only after prize is received.
          </div>
        </SectionCard>

        {/* Right — payment */}
        <SectionCard title="Pay with">
          {/* Method selector */}
          <div className="flex flex-col gap-2 mb-4">
            {METHODS.map((m) => (
              <label key={m.id}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition ${method === m.id ? 'border-sky-400 bg-sky-50' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
                <input type="radio" name="method" value={m.id} checked={method === m.id}
                  onChange={() => handleMethodChange(m.id)} className="mt-0.5" />
                <div>
                  <p className="font-medium text-gray-800">{m.label}</p>
                  <p className="text-xs text-gray-500">{m.note}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Rate summary */}
          <div className="mb-3 flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3 text-sm">
            <span className="text-gray-600">You pay</span>
            <span className="font-semibold text-gray-900">{youPay}</span>
          </div>
          <p className="mb-3 text-xs text-gray-400">{rateNote}</p>

          {/* Rate lock countdown */}
          {quote?.expiresAt && (
            <div className="mb-3">
              <RateLockCountdown expiresAt={quote.expiresAt} onExpire={refreshQuote} />
            </div>
          )}

          {/* FX saving note — only for KES methods */}
          {isKes && (
            <div className="mb-4 rounded-lg bg-green-50 px-3 py-2 text-xs text-green-700">
              Est. saving vs direct PayPal conversion: about KES 600 (estimate)
            </div>
          )}

          {/* Pay button */}
          <button
            onClick={handlePay}
            disabled={paying}
            className="w-full rounded-lg bg-sky-600 py-3 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-sky-300"
          >
            {paying ? 'Processing…' : 'Pay and book sessions'}
          </button>

          <p className="mt-3 text-center text-xs text-gray-400">
            Refunds follow the dispute policy.
          </p>
        </SectionCard>
      </div>
    </div>
  )
}
