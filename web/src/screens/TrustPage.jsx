import { Link } from 'react-router-dom'
import { Icon } from '../components/ui.jsx'

function Section({ title, icon = 'shield', children }) {
  return (
    <section className="card mb-4">
      <h2 className="mb-3 flex items-center gap-3 text-lg font-semibold text-white">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500/15 text-violet-200"><Icon name={icon} /></span>
        {title}
      </h2>
      {children}
    </section>
  )
}

function BulletList({ items }) {
  return (
    <ul className="flex flex-col gap-2 text-sm text-slate-300">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />{item}</li>
      ))}
    </ul>
  )
}

export default function TrustPage() {
  return (
    <div className="mx-auto max-w-3xl animate-fade-up">
      <div className="mb-8">
        <p className="eyebrow mb-2">Trust & compliance</p>
        <h1 className="text-3xl font-bold sm:text-4xl">How SightCoach keeps everyone safe</h1>
        <p className="mt-2 text-slate-400">
          How SightCoach protects coaches, players and teams — in plain language.
        </p>
      </div>

      {/* Verification */}
      <Section title="How coach verification works">
        <p className="mb-3 text-sm text-slate-300">
          Every coach on SightCoach goes through a review before the Verified badge appears on their profile. Here is what happens:
        </p>
        <ol className="list-decimal pl-5 space-y-2 text-sm marker:text-violet-300 text-slate-300">
          <li>The coach submits evidence — tournament results, replay links, team references.</li>
          <li>Our system organises the evidence and flags anything missing or unusual.</li>
          <li><strong className="text-white">A person on our team reads the evidence and makes the decision</strong> — approve, reject, or ask for more.</li>
          <li>Only after a human approves does the Verified badge appear.</li>
        </ol>
        <div className="mt-4 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.06] px-4 py-3 text-sm font-medium text-cyan-100">
          "A person reviews every coach before they are verified."
        </div>
        <p className="mt-3 text-sm text-slate-400">
          AI helps us organise evidence quickly. It never approves or rejects anyone.
        </p>
      </Section>

      {/* Endorsements */}
      <Section title="Endorsements" icon="star">
        <BulletList items={[
          'Each community member can endorse a coach once.',
          'All endorsements are public and dated — you can see who endorsed and when.',
          'If we see an unusual number of new endorsements in a short time, a person on our team investigates before any action is taken.',
          'No automated penalties. A human reviews every flag.',
        ]} />
      </Section>

      {/* Payments */}
      <Section title="How coach payments work" icon="wallet">
        <p className="mb-3 text-sm text-slate-300">
          When you book a coach, your payment is processed by PayPal. The coach's payout is held in our platform ledger until the session is confirmed by the team.
        </p>
        <BulletList items={[
          'Base pay releases after each confirmed session.',
          'Bonus is paid only after the team\'s prize money is actually received, in the prize\'s own currency.',
        ]} />
        <p className="mt-3 text-sm text-slate-400">
          This is our own service-completion workflow — it is not a third-party financial arrangement. It exists to make sure coaches are paid only for confirmed work.
        </p>
      </Section>

      {/* Refunds */}
      <Section title="Refunds and disputes" icon="flag">
        <BulletList items={[
          'If a session does not happen, the team can open a dispute.',
          'No payout is released while a dispute is open.',
          'Both the coach and the team are notified and given a chance to respond.',
          'Our dispute policy is linked on the checkout page.',
        ]} />
      </Section>

      {/* Under 18 */}
      <Section title="Players under 18" icon="user">
        <BulletList items={[
          'Players under 18 must have verifiable parental or guardian consent before creating a profile or booking a session.',
          'We do not use or display any data about minors without verified consent.',
          'Guardian contact and date of birth are never shown in public profiles.',
        ]} />
      </Section>

      {/* Data */}
      <Section title="Your data" icon="shield">
        <BulletList items={[
          'We collect only what is needed to run the platform.',
          'You are told what data is collected and why at sign-up.',
          'Your consent is explicit and can be withdrawn at any time.',
          'Payment data is processed by PayPal and is never stored on our servers.',
        ]} />
      </Section>

      {/* Financial records */}
      <Section title="Financial records" icon="printer">
        <p className="text-sm text-slate-300">
          Transaction records are structured to support a later KRA eTIMS integration through a certified provider.{' '}
          <strong className="text-white">No eTIMS compliance is claimed at this stage.</strong>
        </p>
      </Section>

      {/* FX rates */}
      <Section title="FX rates" icon="refresh">
        <p className="text-sm text-slate-300">
          All exchange rates and savings shown are <strong className="text-white">estimates and demo values</strong>. The rate is locked for 15 minutes during checkout to give you time to complete your payment. No rate is guaranteed beyond that window.
        </p>
      </Section>

      {/* Footer nav */}
      <div className="mt-6 text-center text-xs text-slate-500">
        SightCoach · Part of BARBAH PlayEconomy ·{' '}
        <Link to="/" className="link">Back to home</Link>
      </div>
    </div>
  )
}
