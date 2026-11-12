import { Link } from 'react-router-dom'
import SectionCard from '../components/SectionCard.jsx'

function Section({ title, children }) {
  return (
    <SectionCard className="mb-4">
      <h2 className="mb-3 text-base font-semibold text-gray-900">{title}</h2>
      {children}
    </SectionCard>
  )
}

function BulletList({ items }) {
  return (
    <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  )
}

export default function TrustPage() {
  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Trust and compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          How SightCoach protects coaches, players and teams — in plain language.
        </p>
      </div>

      {/* Verification */}
      <Section title="How coach verification works">
        <p className="mb-3 text-sm text-gray-700">
          Every coach on SightCoach goes through a review before the Verified badge appears on their profile. Here is what happens:
        </p>
        <ol className="list-decimal pl-5 space-y-2 text-sm text-gray-700">
          <li>The coach submits evidence — tournament results, replay links, team references.</li>
          <li>Our system organises the evidence and flags anything missing or unusual.</li>
          <li><strong>A person on our team reads the evidence and makes the decision</strong> — approve, reject, or ask for more.</li>
          <li>Only after a human approves does the Verified badge appear.</li>
        </ol>
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-800">
          "A person reviews every coach before they are verified."
        </div>
        <p className="mt-3 text-sm text-gray-500">
          AI helps us organise evidence quickly. It never approves or rejects anyone.
        </p>
      </Section>

      {/* Endorsements */}
      <Section title="Endorsements">
        <BulletList items={[
          'Each community member can endorse a coach once.',
          'All endorsements are public and dated — you can see who endorsed and when.',
          'If we see an unusual number of new endorsements in a short time, a person on our team investigates before any action is taken.',
          'No automated penalties. A human reviews every flag.',
        ]} />
      </Section>

      {/* Payments */}
      <Section title="How coach payments work">
        <p className="mb-3 text-sm text-gray-700">
          When you book a coach, your payment is processed by PayPal. The coach's payout is held in our platform ledger until the session is confirmed by the team.
        </p>
        <BulletList items={[
          'Base pay releases after each confirmed session.',
          'Bonus is paid only after the team\'s prize money is actually received, in the prize\'s own currency.',
        ]} />
        <p className="mt-3 text-sm text-gray-500">
          This is our own service-completion workflow — it is not a third-party financial arrangement. It exists to make sure coaches are paid only for confirmed work.
        </p>
      </Section>

      {/* Refunds */}
      <Section title="Refunds and disputes">
        <BulletList items={[
          'If a session does not happen, the team can open a dispute.',
          'No payout is released while a dispute is open.',
          'Both the coach and the team are notified and given a chance to respond.',
          'Our dispute policy is linked on the checkout page.',
        ]} />
      </Section>

      {/* Under 18 */}
      <Section title="Players under 18">
        <BulletList items={[
          'Players under 18 must have verifiable parental or guardian consent before creating a profile or booking a session.',
          'We do not use or display any data about minors without verified consent.',
          'Guardian contact and date of birth are never shown in public profiles.',
        ]} />
      </Section>

      {/* Data */}
      <Section title="Your data">
        <BulletList items={[
          'We collect only what is needed to run the platform.',
          'You are told what data is collected and why at sign-up.',
          'Your consent is explicit and can be withdrawn at any time.',
          'Payment data is processed by PayPal and is never stored on our servers.',
        ]} />
      </Section>

      {/* Financial records */}
      <Section title="Financial records">
        <p className="text-sm text-gray-700">
          Transaction records are structured to support a later KRA eTIMS integration through a certified provider.{' '}
          <strong>No eTIMS compliance is claimed at this stage.</strong>
        </p>
      </Section>

      {/* FX rates */}
      <Section title="FX rates">
        <p className="text-sm text-gray-700">
          All exchange rates and savings shown are <strong>estimates and demo values</strong>. The rate is locked for 15 minutes during checkout to give you time to complete your payment. No rate is guaranteed beyond that window.
        </p>
      </Section>

      {/* Footer nav */}
      <div className="mt-6 text-center text-xs text-gray-400">
        SightCoach · Part of BARBAH PlayEconomy ·{' '}
        <Link to="/" className="underline hover:text-gray-600">Back to home</Link>
      </div>
    </div>
  )
}
