import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import './App.css'
import PersonaSwitcher from './components/PersonaSwitcher.jsx'

// Screens
import Discover from './screens/Discover.jsx'
import CoachPage from './screens/CoachPage.jsx'
import Checkout from './screens/Checkout.jsx'
import Confirmation from './screens/Confirmation.jsx'
import CoachDashboard from './screens/CoachDashboard.jsx'
import SessionLogging from './screens/SessionLogging.jsx'
import SkillsPassport from './screens/SkillsPassport.jsx'
import ConsentFlow from './screens/ConsentFlow.jsx'
import ReviewQueue from './screens/ReviewQueue.jsx'

function Header({ persona, setPersona }) {
  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white px-4 py-3">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
        <Link to="/" className="text-base font-semibold text-gray-900 no-underline">
          Coach2Earn
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <PersonaSwitcher persona={persona} onChange={(p) => {
            setPersona(p)
            localStorage.setItem('c2e_persona', p)
          }} />
          <Link to="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">Dashboard</Link>
          <Link to="/passport/player-001" className="text-sm text-gray-600 hover:text-gray-900">Passport</Link>
        </div>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-16 border-t border-gray-200 px-4 py-6 text-center text-xs text-gray-400">
      Players under 18 require parental or guardian consent. ·{' '}
      <Link to="/consent" className="underline">Consent settings</Link>
    </footer>
  )
}

export default function App() {
  const [persona, setPersona] = useState(
    () => localStorage.getItem('c2e_persona') || 'gamer'
  )

  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <Header persona={persona} setPersona={setPersona} />
        <main className="mx-auto max-w-5xl px-4 py-8">
          <Routes>
            <Route path="/" element={<Discover />} />
            <Route path="/coaches/:id" element={<CoachPage />} />
            <Route path="/checkout/:packageId" element={<Checkout />} />
            <Route path="/confirmation" element={<Confirmation />} />
            <Route path="/dashboard" element={<CoachDashboard />} />
            <Route path="/sessions/:id" element={<SessionLogging />} />
            <Route path="/passport/:playerId" element={<SkillsPassport />} />
            <Route path="/consent" element={<ConsentFlow />} />
            <Route path="/review" element={<ReviewQueue />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  )
}
