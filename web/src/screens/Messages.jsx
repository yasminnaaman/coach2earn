import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getPerson, getThread, getThreads, sendMessage } from '../api.js'
import EmptyState from '../components/EmptyState.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { Avatar, Icon, PageHeader, Spinner, timeAgo, useToast } from '../components/ui.jsx'

const POLL_MS = 8000

export default function Messages() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [messages, setMessages] = useState([])
  const [person, setPerson] = useState(null)
  const [convLoading, setConvLoading] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef(null)

  const loadThreads = useCallback(async () => {
    try {
      setThreads(await getThreads())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadConversation = useCallback(async (quiet = false) => {
    if (!userId || userId === 'undefined') return
    if (!quiet) setConvLoading(true)
    try {
      const msgs = await getThread(userId)
      setMessages(msgs)
      if (!quiet) loadThreads() // unread counts change after reading
    } catch (e) {
      if (!quiet) setError(e.message)
    } finally {
      if (!quiet) setConvLoading(false)
    }
  }, [userId, loadThreads])

  useEffect(() => { loadThreads() }, [loadThreads])

  useEffect(() => {
    setMessages([])
    setPerson(null)
    setError('')
    if (!userId || userId === 'undefined') return
    loadConversation()
    getPerson(userId).then(setPerson).catch(() => setPerson({ userId, name: 'Unknown user' }))
    const t = setInterval(() => loadConversation(true), POLL_MS)
    return () => clearInterval(t)
  }, [userId, loadConversation])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  async function send(e) {
    e?.preventDefault()
    const body = draft.trim()
    if (!body || !userId) return
    setSending(true)
    try {
      const m = await sendMessage({ userId, body })
      setMessages((list) => [...list, m])
      setDraft('')
      loadThreads()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading messages…" />

  const active = threads.find((t) => t.counterpart.userId === userId)
  const name = active?.counterpart.name || person?.name || 'Conversation'

  return (
    <div>
      <PageHeader eyebrow="Inbox" title="Messages" subtitle="Plan sessions, share replays and sort out questions with your coach or players." />
      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}

      <div className="card grid h-[min(70vh,680px)] grid-cols-1 overflow-hidden p-0 md:grid-cols-[300px_1fr]">
        {/* Thread list */}
        <aside className={`flex flex-col border-white/[0.06] md:border-r ${userId ? 'hidden md:flex' : 'flex'}`}>
          <div className="border-b border-white/[0.06] px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Conversations
          </div>
          <div className="flex-1 overflow-y-auto">
            {threads.length === 0 ? (
              <p className="p-4 text-sm text-slate-400">No conversations yet. Message a coach from their profile.</p>
            ) : threads.map((t) => (
              <button key={t.counterpart.userId} onClick={() => navigate(`/messages/${t.counterpart.userId}`)}
                className={`flex w-full items-center gap-3 px-4 py-3 text-left transition ${t.counterpart.userId === userId ? 'bg-violet-500/10' : 'hover:bg-white/[0.03]'}`}>
                <Avatar name={t.counterpart.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-white">{t.counterpart.name}</p>
                    <span className="shrink-0 text-[11px] text-slate-500">{timeAgo(t.lastAt)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className={`flex-1 truncate text-xs ${t.unread ? 'font-semibold text-slate-200' : 'text-slate-400'}`}>{t.lastMessage}</p>
                    {t.unread > 0 && <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-violet-500 px-1.5 text-[10px] font-bold text-white">{t.unread}</span>}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Conversation */}
        <section className={`flex min-h-0 flex-col ${userId ? 'flex' : 'hidden md:flex'}`}>
          {!userId || userId === 'undefined' ? (
            <div className="flex flex-1 items-center justify-center p-6">
              <EmptyState icon="chat" heading="Select a conversation" subtext="Pick a thread on the left, or message a coach from their profile." />
            </div>
          ) : (
            <>
              <header className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-3">
                <button className="btn-ghost btn-sm md:hidden" onClick={() => navigate('/messages')}><Icon name="back" /></button>
                <Avatar name={name} size="sm" />
                <div>
                  <p className="text-sm font-semibold text-white">{name}</p>
                  <p className="text-xs capitalize text-slate-500">{active?.role || (person?.coachId ? 'coach' : 'member')}</p>
                </div>
              </header>
              <div className="flex-1 overflow-y-auto px-4 py-5">
                {convLoading ? (
                  <div className="flex justify-center py-10"><Spinner className="h-6 w-6 text-violet-300" /></div>
                ) : messages.length === 0 ? (
                  <p className="py-10 text-center text-sm text-slate-500">No messages yet — say hello 👋</p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {messages.map((m) => (
                      <li key={m.id} className={`flex ${m.mine ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-lg ${m.mine
                          ? 'rounded-br-md bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-violet-950/40'
                          : 'rounded-bl-md bg-white/[0.06] text-slate-100'}`}>
                          <p className="whitespace-pre-wrap break-words">{m.body}</p>
                          <p className={`mt-1 text-[10px] ${m.mine ? 'text-violet-200/70' : 'text-slate-500'}`}>{timeAgo(m.createdAt)}</p>
                        </div>
                      </li>
                    ))}
                    <li ref={endRef} />
                  </ul>
                )}
              </div>
              <form onSubmit={send} className="flex items-end gap-2 border-t border-white/[0.06] p-3">
                <textarea rows={1} value={draft} onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                  placeholder="Write a message… (Enter to send)" className="input max-h-32 resize-none" />
                <button type="submit" disabled={sending || !draft.trim()} className="btn-primary h-[42px] px-4" aria-label="Send">
                  {sending ? <Spinner /> : <Icon name="send" />}
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
