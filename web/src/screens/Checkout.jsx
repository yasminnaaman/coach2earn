import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { getCoachForPackage, createQuote, createOrder, payOrder } from '../api.js'
import { getUser } from '../auth.js'
import VerifiedBadge from '../components/VerifiedBadge.jsx'
import RateLockCountdown from '../components/RateLockCountdown.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Avatar, Icon, Modal, PageHeader, money, useToast } from '../components/ui.jsx'

const METHODS = [
  { id: 'mpesa_sim', label: 'M-Pesa', note: 'STK push to your phone · KES', icon: 'phone', badge: 'Popular' },
  { id: 'card', label: 'Card', note: 'Visa / Mastercard · KES', icon: 'card' },
  { id: 'paypal_balance', label: 'PayPal balance', note: 'Pay in USD · no conversion', icon: 'wallet' },
]

function PaymentModal({ open, method, amountLabel, onClose, onPay }) {
  const [phone, setPhone] = useState('0712 345 678')
  const [card, setCard] = useState({ number: '4242 4242 4242 4242', expiry: '12/28', cvc: '123', name: '' })
  const [paypal, setPaypal] = useState(getUser()?.email || '')
  const [stage, setStage] = useState('form') // form | processing | error
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) { setStage('form'); setError('') }
  }, [open, method])

  function validate() {
    if (method === 'mpesa_sim' && !/^(\+?254|0)?7\d{8}$/.test(phone.replace(/\s/g, ''))) return 'Enter a valid Safaricom number, e.g. 0712 345 678.'
    if (method === 'card') {
      if (card.number.replace(/\s/g, '').length < 15) return 'Enter a valid card number.'
      if (!/^\d{2}\/\d{2}$/.test(card.expiry)) return 'Expiry must look like MM/YY.'
      if (!/^\d{3,4}$/.test(card.cvc)) return 'Enter the 3–4 digit CVC.'
    }
    if (method === 'paypal_balance' && !/\S+@\S+\.\S+/.test(paypal)) return 'Enter your PayPal email.'
    return ''
  }

  async function submit(e) {
    e.preventDefault()
    const v = validate()
    if (v) return setError(v)
    setError('')
    setStage('processing')
    try {
      await onPay({ phone: method === 'mpesa_sim' ? phone : null })
    } catch (err) {
      setError(err.message || 'Payment failed. Try again.')
      setStage('form')
    }
  }

  const title = { mpesa_sim: 'Pay with M-Pesa', card: 'Pay by card', paypal_balance: 'Pay with PayPal' }[method]
  return (
    <Modal open={open} onClose={stage === 'processing' ? undefined : onClose} title={title}>
      {stage === 'processing' ? (
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <div className="relative flex h-16 w-16 items-center justify-center">
            <span className="absolute inset-0 animate-ping rounded-full bg-violet-500/30" />
            <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-violet-500/20 text-violet-200">
              <Icon name={method === 'mpesa_sim' ? 'phone' : method === 'card' ? 'card' : 'wallet'} className="h-7 w-7" />
            </span>
          </div>
          <p className="font-semibold text-white">
            {method === 'mpesa_sim' ? 'Check your phone and enter your M-Pesa PIN…' : 'Processing your payment…'}
          </p>
          <p className="text-sm text-slate-400">Simulated for this demo — no real money moves.</p>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="rounded-xl bg-white/[0.04] px-4 py-3 text-sm">
            <span className="text-slate-400">Amount</span>
            <span className="float-right font-semibold text-white">{amountLabel}</span>
          </div>
          {method === 'mpesa_sim' && (
            <div>
              <label className="label">M-Pesa phone number</label>
              <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" />
              <p className="mt-1.5 text-xs text-slate-500">You'll receive an STK push prompt to confirm.</p>
            </div>
          )}
          {method === 'card' && (
            <>
              <div>
                <label className="label">Card number</label>
                <input className="input font-mono" value={card.number} inputMode="numeric"
                  onChange={(e) => setCard((c) => ({ ...c, number: e.target.value.replace(/[^\d ]/g, '').slice(0, 23) }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Expiry</label>
                  <input className="input font-mono" value={card.expiry} placeholder="MM/YY" onChange={(e) => setCard((c) => ({ ...c, expiry: e.target.value.slice(0, 5) }))} />
                </div>
                <div>
                  <label className="label">CVC</label>
                  <input className="input font-mono" value={card.cvc} inputMode="numeric" onChange={(e) => setCard((c) => ({ ...c, cvc: e.target.value.replace(/\D/g, '').slice(0, 4) }))} />
                </div>
              </div>
            </>
          )}
          {method === 'paypal_balance' && (
            <div>
              <label className="label">PayPal email</label>
              <input className="input" type="email" value={paypal} onChange={(e) => setPaypal(e.target.value)} />
            </div>
          )}
          <ErrorMessage message={error} />
          <button type="submit" className="btn-primary btn-lg w-full"><Icon name="shield" /> Pay {amountLabel}</button>
          <p className="text-center text-xs text-slate-500">Demo payment — simulated, no charge is made.</p>
        </form>
      )}
    </Modal>
  )
}

export default function Checkout() {
  const { packageId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const toast = useToast()

  const [coach, setCoach] = useState(null)
  const [pkg, setPkg] = useState(null)
  const [method, setMethod] = useState('mpesa_sim')
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [payOpen, setPayOpen] = useState(false)
  const [error, setError] = useState('')

  // Returning to /checkout/x?orderId=… (older links) goes straight to the receipt.
  useEffect(() => {
    const existing = searchParams.get('orderId') || searchParams.get('token')
    if (existing) navigate(`/confirmation/${existing}`, { replace: true })
  }, [searchParams, navigate])

  useEffect(() => {
    async function init() {
      try {
        const coachData = await getCoachForPackage(packageId)
        setCoach(coachData)
        const found = coachData.packages?.find((p) => p.id === packageId) || coachData.packages?.[0]
        setPkg(found)
        setQuote(await createQuote({ packageId: found?.id || packageId, paymentMethod: 'mpesa_sim' }))
      } catch (e) {
        setError(e.message || 'Could not load checkout. Go back and try again.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [packageId])

  const refreshQuote = useCallback(async () => {
    try {
      setQuote(await createQuote({ packageId: pkg?.id || packageId, paymentMethod: method }))
    } catch {
      setError('Could not refresh the quote. Try again.')
    }
  }, [method, pkg, packageId])

  async function pay({ phone }) {
    const { orderId } = await createOrder({ quoteId: quote?.id, paymentMethod: method })
    await payOrder(orderId, { paymentMethod: method, phone })
    setPayOpen(false)
    toast('Payment received — now pick your session times!')
    navigate(`/confirmation/${orderId}`)
  }

  const isKes = method !== 'paypal_balance'
  const youPay = quote ? (isKes ? `KES ${quote.amountKes?.toLocaleString()}` : `USD ${quote.amountUsd?.toFixed(2)}`) : '—'

  if (loading) return <LoadingSpinner label="Preparing checkout…" />

  return (
    <div className="animate-fade-up">
      <PageHeader eyebrow="Secure checkout" title="Complete your booking" subtitle="Your exchange rate is locked for 15 minutes." />
      {error && <div className="mb-6"><ErrorMessage message={error} /></div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        {/* Order summary */}
        <section className="card h-fit">
          <h2 className="mb-5 text-base font-semibold">Order summary</h2>
          {coach && (
            <div className="mb-5 flex items-center gap-3 rounded-xl bg-white/[0.03] p-3">
              <Avatar name={coach.name} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{coach.name}</span>
                  {coach.verified && <VerifiedBadge />}
                </div>
                <p className="text-xs capitalize text-slate-400">{coach.game?.replace(/_/g, ' ')} · {coach.role}</p>
              </div>
            </div>
          )}
          {pkg && (
            <div className="flex flex-col gap-2 text-sm">
              <p className="font-semibold text-white">{pkg.label}</p>
              <div className="flex justify-between text-slate-400">
                <span>{pkg.sessions} sessions × {money(pkg.pricePerSession, pkg.currency)}</span>
                <span>{money(pkg.subtotal, pkg.currency)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Platform fee ({pkg.platformFeePct}%)</span><span>{money(pkg.platformFee, pkg.currency)}</span>
              </div>
              <div className="divider my-2" />
              <div className="flex justify-between text-base font-semibold text-white">
                <span>Total</span><span>{money(pkg.total, pkg.currency)} {pkg.currency || 'USD'}</span>
              </div>
            </div>
          )}
          <div className="mt-5 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3 text-xs text-amber-200">
            Coach earns up to 10% of prize money, based on confirmed hours. Paid only after prize is received.
          </div>
          <ul className="mt-5 flex flex-col gap-2 text-sm text-slate-400">
            <li className="flex items-center gap-2"><Icon name="check" className="h-4 w-4 text-emerald-400" /> Coach is paid only after you confirm each session</li>
            <li className="flex items-center gap-2"><Icon name="check" className="h-4 w-4 text-emerald-400" /> Schedule sessions at times that suit you</li>
            <li className="flex items-center gap-2"><Icon name="check" className="h-4 w-4 text-emerald-400" /> Refunds follow the dispute policy</li>
          </ul>
        </section>

        {/* Payment */}
        <section className="card h-fit">
          <h2 className="mb-5 text-base font-semibold">Pay with</h2>
          <div className="flex flex-col gap-3">
            {METHODS.map((m) => (
              <label key={m.id}
                className={`flex cursor-pointer items-center gap-4 rounded-xl border p-4 transition ${method === m.id ? 'border-violet-400/60 bg-violet-500/10 ring-4 ring-violet-500/10' : 'border-white/10 hover:border-white/20'}`}>
                <input type="radio" name="method" value={m.id} checked={method === m.id} onChange={() => setMethod(m.id)} className="sr-only" />
                <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${method === m.id ? 'bg-violet-500/25 text-violet-100' : 'bg-white/5 text-slate-400'}`}>
                  <Icon name={m.icon} className="h-5 w-5" />
                </span>
                <span className="flex-1">
                  <span className="flex items-center gap-2 font-semibold text-white">
                    {m.label}
                    {m.badge && <span className="chip bg-emerald-500/15 text-emerald-300">{m.badge}</span>}
                  </span>
                  <span className="block text-xs text-slate-400">{m.note}</span>
                </span>
                <span className={`h-5 w-5 rounded-full border-2 ${method === m.id ? 'border-violet-400 bg-violet-400 shadow-[inset_0_0_0_3px_#0e1424]' : 'border-white/20'}`} />
              </label>
            ))}
          </div>

          <div className="mt-6 flex items-center justify-between rounded-xl bg-gradient-to-r from-violet-600/20 to-cyan-500/10 px-5 py-4">
            <span className="text-sm text-slate-300">You pay</span>
            <span className="font-display text-2xl font-bold text-white">{youPay}</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">{isKes ? quote?.rateLabel || '1 USD = 129.00 KES (est.)' : 'No conversion needed'}</p>

          {quote?.expiresAt && (
            <div className="mt-4"><RateLockCountdown expiresAt={quote.expiresAt} onExpire={refreshQuote} /></div>
          )}
          {isKes && (
            <div className="mt-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] px-4 py-2.5 text-xs text-emerald-200">
              Est. saving vs direct PayPal conversion: about KES 600 (estimate)
            </div>
          )}

          <button onClick={() => setPayOpen(true)} disabled={!quote} className="btn-primary btn-lg mt-6 w-full">
            <Icon name="shield" /> Pay and book sessions
          </button>
          <p className="mt-3 text-center text-xs text-slate-500">Payments in this prototype are simulated.</p>
        </section>
      </div>

      <PaymentModal open={payOpen} method={method} amountLabel={youPay} onClose={() => setPayOpen(false)} onPay={pay} />
    </div>
  )
}
