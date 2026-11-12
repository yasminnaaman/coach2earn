import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getCoach, sendMessage } from '../api.js'
import { currentRole, isLoggedIn } from '../auth.js'
import VerifiedBadge from '../components/VerifiedBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { Avatar, Icon, Modal, Spinner, money, useToast } from '../components/ui.jsx'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const TYPE_LABELS = { ballchasing_replay: 'Replay', tournament: 'Tournament', video: 'Video' }

export default function CoachPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [coach, setCoach] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [msgOpen, setMsgOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    getCoach(id)
      .then((c) => {
        setCoach(c)
        setSelected(c.packages?.[0]?.id || null)
      })
      .catch(() => setError('Could not load this coach. Go back and try another coach.'))
      .finally(() => setLoading(false))
  }, [id])

  const loggedIn = USE_MOCK || isLoggedIn()
  const role = currentRole()

  function requireLogin(next) {
    if (loggedIn) return true
    toast('Log in to continue.', 'info')
    navigate('/login', { state: { from: { pathname: next } } })
    return false
  }

  function book() {
    const target = `/checkout/${selected}`
    if (!requireLogin(target)) return
    if (role && role !== 'PLAYER') {
      toast('Booking is for player accounts — log in as a player to book.', 'info')
      return
    }
    navigate(target)
  }

  function openMessage() {
    if (!requireLogin(`/coaches/${id}`)) return
    setMsg(`Hi ${coach.name.split(' ')[0]}! I'm interested in coaching for `)
    setMsgOpen(true)
  }

  async function send() {
    if (!msg.trim()) return
    setSending(true)
    try {
      const sent = await sendMessage({ coachId: coach.coachId, body: msg.trim() })
      setMsgOpen(false)
      toast('Message sent!')
      navigate(`/messages/${sent.recipientUserId}`)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading coach…" />
  if (error) return <ErrorMessage message={error} />
  if (!coach) return null

  const pkg = coach.packages?.find((p) => p.id === selected)

  return (
    <div className="animate-fade-up">
      <button onClick={() => navigate(-1)} className="btn-ghost btn-sm mb-6 -ml-3"><Icon name="back" /> Back</button>

      {/* Hero */}
      <div className="card relative mb-6 overflow-hidden p-0">
        <div className="h-28 bg-gradient-to-r from-violet-700/60 via-indigo-700/40 to-cyan-600/40" />
        <div className="flex flex-col gap-5 px-6 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="-mt-10 flex items-end gap-4">
            <Avatar name={coach.name} size="xl" className="ring-4 ring-panel" />
            <div className="pb-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold sm:text-3xl">{coach.name}</h1>
                {coach.verified && <VerifiedBadge />}
              </div>
              <p className="mt-1 flex flex-wrap gap-x-3 text-sm capitalize text-slate-400">
                <span className="inline-flex items-center gap-1"><Icon name="gamepad" className="h-3.5 w-3.5" />{coach.game?.replace(/_/g, ' ')}</span>
                <span>{coach.role}</span>
                {coach.endorsementCount > 0 && <span>{coach.endorsementCount} endorsements</span>}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={openMessage} className="btn-secondary"><Icon name="chat" /> Message</button>
            {pkg && <button onClick={book} className="btn-primary">Book now <Icon name="arrow" /></button>}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="flex flex-col gap-6">
          <section className="card">
            <h2 className="mb-3 text-base font-semibold">About</h2>
            <p className="whitespace-pre-line text-slate-300">{coach.bio}</p>
            {coach.goals && coach.goals !== coach.bio && (
              <div className="mt-5 rounded-xl border border-violet-400/20 bg-violet-500/[0.06] p-4">
                <p className="eyebrow mb-1">Coaching philosophy</p>
                <p className="text-sm text-slate-300">{coach.goals}</p>
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="mb-4 text-base font-semibold">Evidence & endorsements</h2>
            {coach.evidence?.length > 0 || coach.endorsements?.length > 0 ? (
              <div className="flex flex-col gap-3">
                {coach.evidence?.map((ev) => (
                  <a key={ev.id} href={ev.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-start gap-3 rounded-xl border border-white/[0.06] p-3 transition hover:border-violet-400/40">
                    <span className="chip bg-violet-500/15 text-violet-200">{TYPE_LABELS[ev.type] || ev.type}</span>
                    <span className="min-w-0 text-sm">
                      <span className="block text-slate-200">{ev.description || ev.url}</span>
                      <span className="block truncate text-xs text-slate-500">{ev.url}</span>
                    </span>
                  </a>
                ))}
                {coach.endorsements?.map((e, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="inline-flex items-center gap-2 text-slate-300"><Icon name="star" className="h-4 w-4 text-amber-300" />{e.community}</span>
                    <span className="text-slate-500">{e.date}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.05] p-4 text-sm text-cyan-100">
                <Icon name="shield" className="mt-0.5 h-5 w-5 shrink-0" />
                <p>This coach's evidence was reviewed privately by our team before they received the Verified badge. Private evidence isn't shown publicly.</p>
              </div>
            )}
          </section>
        </div>

        {/* Packages */}
        <aside className="card h-fit lg:sticky lg:top-24">
          <h2 className="mb-4 text-base font-semibold">Choose a package</h2>
          {coach.packages?.length ? (
            <>
              <div className="flex flex-col gap-3">
                {coach.packages.map((p) => (
                  <button key={p.id} onClick={() => setSelected(p.id)}
                    className={`rounded-xl border p-4 text-left transition ${selected === p.id ? 'border-violet-400/60 bg-violet-500/10 ring-4 ring-violet-500/10' : 'border-white/10 hover:border-white/20'}`}>
                    <div className="flex items-start justify-between gap-3">
                      <span className="font-semibold text-white">{p.label}</span>
                      <span className="font-display text-lg font-bold text-white">{money(p.total, p.currency)}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{p.sessions} sessions · {money(p.pricePerSession, p.currency)} each{p.durationDays ? ` · ${p.durationDays} days` : ''}</p>
                    {p.description && selected === p.id && <p className="mt-2 text-sm text-slate-300">{p.description}</p>}
                  </button>
                ))}
              </div>
              {pkg && (
                <div className="mt-5 flex flex-col gap-2 text-sm">
                  <div className="flex justify-between text-slate-400"><span>Subtotal</span><span>{money(pkg.subtotal, pkg.currency)}</span></div>
                  <div className="flex justify-between text-slate-400"><span>Platform fee ({pkg.platformFeePct}%)</span><span>{money(pkg.platformFee, pkg.currency)}</span></div>
                  <div className="divider my-1" />
                  <div className="flex justify-between font-semibold text-white"><span>Total</span><span>{money(pkg.total, pkg.currency)} {pkg.currency}</span></div>
                  {(!pkg.currency || pkg.currency === 'USD') && (
                    <p className="text-xs text-slate-500">≈ KES {Math.round(pkg.total * 129).toLocaleString()} at 1 USD = 129.00 KES (est.)</p>
                  )}
                </div>
              )}
              <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3 text-xs text-amber-200">
                Coach earns up to 10% of prize money, based on confirmed hours. Paid only after prize is received.
              </div>
              <button onClick={book} disabled={!pkg} className="btn-primary btn-lg mt-4 w-full">Book this coach <Icon name="arrow" /></button>
              {!loggedIn && <p className="mt-2 text-center text-xs text-slate-500"><Link to="/login" className="link">Log in</Link> to book.</p>}
            </>
          ) : (
            <p className="text-sm text-slate-400">This coach has no packages available right now.</p>
          )}
        </aside>
      </div>

      <Modal open={msgOpen} onClose={() => setMsgOpen(false)} title={`Message ${coach.name}`}
        footer={<>
          <button className="btn-ghost" onClick={() => setMsgOpen(false)}>Cancel</button>
          <button className="btn-primary" onClick={send} disabled={sending || !msg.trim()}>
            {sending ? <Spinner /> : <Icon name="send" />} Send
          </button>
        </>}>
        <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={5} className="input" autoFocus />
        <p className="mt-2 text-xs text-slate-500">Messages are private between you and the coach.</p>
      </Modal>
    </div>
  )
}
