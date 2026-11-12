import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getCoaches } from '../api.js'
import { currentRole } from '../auth.js'
import { Avatar, Icon, money } from '../components/ui.jsx'
import VerifiedBadge from '../components/VerifiedBadge.jsx'

const STEPS = [
  { icon: 'search', title: 'Find a verified coach', body: 'Filter by game, goal and budget. Every Verified badge is granted by a person on our team — never just an algorithm.' },
  { icon: 'wallet', title: 'Book & pay fairly', body: 'Pay in KES via M-Pesa or card, or in USD via PayPal. Your rate is locked for 15 minutes — no surprises.' },
  { icon: 'check', title: 'Confirm, then release pay', body: 'Coaches are paid after you confirm each session. Disputes put payouts on hold until they are resolved.' },
]

const FEATURES = [
  { icon: 'shield', title: 'Human-verified coaches', body: 'Evidence is reviewed by people, with AI only organising it.' },
  { icon: 'trophy', title: 'Skills Passport', body: 'Replay stats, evidence and coach feedback in one shareable profile.' },
  { icon: 'chat', title: 'Direct messaging', body: 'Plan sessions and share replays with your coach in-app.' },
  { icon: 'bolt', title: 'Prize-share bonuses', body: 'Coaches earn a share of team prize money based on confirmed hours.' },
]

export default function Welcome({ user }) {
  const navigate = useNavigate()
  const [coaches, setCoaches] = useState([])
  const role = currentRole()

  useEffect(() => {
    getCoaches({}).then((list) => setCoaches(list.slice(0, 3))).catch(() => setCoaches([]))
  }, [])

  const primaryCta = user
    ? role === 'COACH' ? { to: '/dashboard', label: 'Open dashboard' }
      : role === 'ADMIN' ? { to: '/review', label: 'Open review queue' }
        : { to: '/my-sessions', label: 'My sessions' }
    : { to: '/register', label: 'Create free account' }

  return (
    <div className="flex flex-col gap-24">
      {/* Hero */}
      <section className="grid items-center gap-12 pt-6 lg:grid-cols-[1.15fr_1fr]">
        <div className="animate-fade-up">
          <span className="chip mb-6 bg-white/5 py-1 text-slate-300 ring-1 ring-inset ring-white/10">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> Part of BARBAH PlayEconomy
          </span>
          <h1 className="text-4xl font-bold leading-[1.05] sm:text-6xl">
            Level up with a <span className="gradient-text">verified</span> esports coach.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-slate-400">
            SightCoach connects players and teams across Kenya and Africa with experienced coaches —
            transparent pricing, confirmed sessions and fair payouts.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button onClick={() => navigate('/coaches')} className="btn-primary btn-lg">
              <Icon name="search" /> Find a coach
            </button>
            <button onClick={() => navigate(primaryCta.to)} className="btn-secondary btn-lg">
              {primaryCta.label} <Icon name="arrow" />
            </button>
          </div>
          <div className="mt-10 flex flex-wrap gap-8">
            {[['5+', 'Verified coaches'], ['15 min', 'Rate lock'], ['85%', 'Paid to coaches']].map(([v, l]) => (
              <div key={l}>
                <p className="font-display text-2xl font-bold text-white">{v}</p>
                <p className="text-xs uppercase tracking-wider text-slate-500">{l}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Hero visual: live coach cards */}
        <div className="relative hidden lg:block">
          <div className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-violet-600/30 to-cyan-500/20 blur-2xl" />
          <div className="relative flex flex-col gap-3">
            {(coaches.length ? coaches : [null, null, null]).map((c, i) => (
              <div key={c?.coachId || i}
                className="card flex items-center gap-4 p-4 animate-float"
                style={{ animationDelay: `${i * 0.8}s`, marginLeft: i === 1 ? '2.5rem' : 0 }}>
                {c ? (
                  <>
                    <Avatar name={c.name} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-semibold text-white">{c.name}</span>
                        {c.verified && <VerifiedBadge />}
                      </div>
                      <p className="truncate text-xs capitalize text-slate-400">{c.game?.replace(/_/g, ' ')} · {c.role}</p>
                    </div>
                    <span className="font-display font-bold text-white">{money(c.priceUsd)}</span>
                  </>
                ) : (
                  <div className="h-11 w-full animate-pulse rounded-xl bg-white/5" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section>
        <p className="eyebrow text-center">How it works</p>
        <h2 className="mt-2 text-center text-3xl font-bold">From search to stronger gameplay in three steps</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="card card-hover relative overflow-hidden">
              <span className="absolute right-5 top-4 font-display text-6xl font-bold text-white/[0.04]">{i + 1}</span>
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/25 to-cyan-500/20 text-violet-200">
                <Icon name={s.icon} className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <Icon name={f.icon} className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 text-base font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-slate-400">{f.body}</p>
          </div>
        ))}
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-violet-700/40 via-indigo-700/20 to-cyan-600/20 px-8 py-14 text-center">
        <div className="absolute -left-20 -top-20 h-60 w-60 rounded-full bg-violet-500/30 blur-3xl" />
        <p className="relative text-sm font-medium text-violet-200">“A person reviews every coach before they are verified.”</p>
        <h2 className="relative mt-3 text-3xl font-bold sm:text-4xl">Ready to climb the ranks?</h2>
        <div className="relative mt-8 flex flex-wrap justify-center gap-3">
          <button onClick={() => navigate('/coaches')} className="btn-accent btn-lg">Browse coaches <Icon name="arrow" /></button>
          {!user && <Link to="/login" className="btn-secondary btn-lg">I already have an account</Link>}
        </div>
      </section>
    </div>
  )
}
