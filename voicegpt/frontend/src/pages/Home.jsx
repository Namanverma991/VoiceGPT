import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap, LogOut, Plus, Trash2, ChevronLeft, ChevronRight,
  Globe, Send, Wifi, WifiOff, Volume2, VolumeX, Settings,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore.js'
import { useVoiceStore } from '../store/voiceStore.js'
import { useSocket } from '../hooks/useSocket.js'
import { chatApi } from '../services/api.js'
import MicButton from '../components/MicButton.jsx'
import ChatWindow from '../components/ChatWindow.jsx'
import AudioPlayer from '../components/AudioPlayer.jsx'
import Loader from '../components/Loader.jsx'

const LANGUAGES = [
  { code: 'en', label: '🇬🇧 English' },
  { code: 'hi', label: '🇮🇳 Hindi' },
  { code: 'hinglish', label: '🇮🇳 Hinglish' },
]

export default function Home() {
  // Auth
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  // Voice store
  const sessionId = useVoiceStore((s) => s.sessionId)
  const sessions = useVoiceStore((s) => s.sessions)
  const messages = useVoiceStore((s) => s.messages)
  const language = useVoiceStore((s) => s.language)
  const wsConnected = useVoiceStore((s) => s.wsConnected)
  const isMuted = useVoiceStore((s) => s.isMuted)
  const setSession = useVoiceStore((s) => s.setSession)
  const setSessions = useVoiceStore((s) => s.setSessions)
  const setMessages = useVoiceStore((s) => s.setMessages)
  const addMessage = useVoiceStore((s) => s.addMessage)
  const setLanguage = useVoiceStore((s) => s.setLanguage)
  const setMuted = useVoiceStore((s) => s.setMuted)
  const resetSession = useVoiceStore((s) => s.resetSession)

  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [textInput, setTextInput] = useState('')
  const [sendingText, setSendingText] = useState(false)
  const textInputRef = useRef(null)

  // WebSocket
  const { socket, interrupt, clearContext, sendText } = useSocket(sessionId)

  // ── Load sessions on mount ────────────────────────────
  useEffect(() => {
    ;(async () => {
      try {
        const res = await chatApi.listSessions()
        const list = res.data
        setSessions(list)
        if (list.length > 0) {
          // Load most recent session
          await loadSession(list[0].id)
        } else {
          await createNewSession()
        }
      } catch (e) {
        toast.error('Failed to load sessions')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const loadSession = async (id) => {
    try {
      const res = await chatApi.getSession(id)
      setSession(id)
      setMessages(
        res.data.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          latency_ms: m.latency_ms,
        }))
      )
      setLanguage(res.data.language || 'en')
    } catch (e) {
      toast.error('Failed to load session')
    }
  }

  const createNewSession = async () => {
    try {
      const res = await chatApi.createSession({
        title: `Chat ${new Date().toLocaleDateString()}`,
        language,
      })
      const newSession = res.data
      setSessions((prev) => [newSession, ...(Array.isArray(prev) ? prev : [])])
      setSession(newSession.id)
      resetSession()
      toast.success('New conversation started')
    } catch (e) {
      toast.error('Failed to create session')
    }
  }

  const handleDeleteSession = async (id, e) => {
    e.stopPropagation()
    try {
      await chatApi.deleteSession(id)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (id === sessionId) {
        const remaining = sessions.filter((s) => s.id !== id)
        if (remaining.length > 0) await loadSession(remaining[0].id)
        else await createNewSession()
      }
      toast.success('Session deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const handleSendText = async (e) => {
    e.preventDefault()
    const text = textInput.trim()
    if (!text || !sessionId) return

    setTextInput('')
    setSendingText(true)
    addMessage({ id: Date.now(), role: 'user', content: text })

    // Use WebSocket if connected, else REST
    if (socket?.connected) {
      sendText(text)
    } else {
      try {
        const res = await chatApi.sendText({ session_id: sessionId, message: text, language })
        addMessage({
          id: res.data.assistant_message.id,
          role: 'assistant',
          content: res.data.assistant_message.content,
          latency_ms: res.data.latency_ms,
        })
      } catch (err) {
        toast.error('Failed to send message')
      }
    }
    setSendingText(false)
  }

  const handleLogout = async () => {
    await logout()
    toast.success('Logged out')
  }

  if (loading) return <Loader message="Loading VoiceGPT…" />

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            key="sidebar"
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              width: 260, flexShrink: 0, padding: '16px 12px',
              background: 'rgba(255,255,255,0.02)',
              borderRight: '1px solid var(--glass-border)',
              display: 'flex', flexDirection: 'column', gap: 8,
              overflowY: 'auto',
            }}
          >
            {/* Logo */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 4px 16px' }}>
              <div
                style={{
                  width: 34, height: 34, borderRadius: '50%',
                  background: 'linear-gradient(135deg,#7c3aed,#06b6d4)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 0 16px rgba(124,58,237,0.4)',
                }}
              >
                <Zap size={16} color="white" fill="white" />
              </div>
              <span style={{ fontFamily: 'Outfit,sans-serif', fontWeight: 700, fontSize: 18 }}>
                VoiceGPT
              </span>
            </div>

            {/* New Chat button */}
            <button
              id="btn-new-chat"
              onClick={createNewSession}
              className="btn btn-primary"
              style={{ width: '100%', padding: '10px 16px', fontSize: 13 }}
            >
              <Plus size={15} /> New Chat
            </button>

            <div className="divider" style={{ margin: '4px 0' }} />

            {/* Session list */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {sessions.map((s) => (
                <motion.div
                  key={s.id}
                  whileHover={{ x: 2 }}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
                    background: s.id === sessionId ? 'rgba(124,58,237,0.15)' : 'transparent',
                    border: s.id === sessionId ? '1px solid rgba(124,58,237,0.3)' : '1px solid transparent',
                    marginBottom: 4, transition: 'all 0.2s ease',
                  }}
                  onClick={() => loadSession(s.id)}
                >
                  <span style={{ fontSize: 13, color: s.id === sessionId ? 'var(--text-primary)' : 'var(--text-secondary)', truncate: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: 160 }}>
                    {s.title}
                  </span>
                  <button
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, borderRadius: 4, opacity: 0.6 }}
                    title="Delete session"
                  >
                    <Trash2 size={13} />
                  </button>
                </motion.div>
              ))}
            </div>

            <div className="divider" style={{ margin: '4px 0' }} />

            {/* User info */}
            <div style={{ padding: '8px 4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {user?.username || 'User'}
                </p>
                <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                title="Logout"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 6, borderRadius: 8 }}
                id="btn-logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* ── Main Panel ──────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top bar */}
        <header
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 20px',
            borderBottom: '1px solid var(--glass-border)',
            background: 'rgba(255,255,255,0.02)', flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 6, borderRadius: 8, display: 'flex', alignItems: 'center' }}
              id="btn-toggle-sidebar"
            >
              {sidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
            </button>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>
              {sessions.find((s) => s.id === sessionId)?.title || 'VoiceGPT'}
            </h3>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* WS status */}
            <div
              className={`badge ${wsConnected ? 'badge-green' : 'badge-red'}`}
              title={wsConnected ? 'WebSocket connected' : 'No WebSocket'}
            >
              {wsConnected ? <Wifi size={11} /> : <WifiOff size={11} />}
              {wsConnected ? 'Live' : 'Offline'}
            </div>

            {/* Language selector */}
            <div style={{ position: 'relative' }}>
              <Globe size={14} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <select
                id="select-voice-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="input"
                style={{ paddingLeft: 26, paddingRight: 12, padding: '6px 12px 6px 26px', fontSize: 13, height: 34 }}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
            </div>

            {/* Mute */}
            <button
              id="btn-mute"
              onClick={() => setMuted(!isMuted)}
              title={isMuted ? 'Unmute' : 'Mute'}
              style={{ background: 'none', border: '1px solid var(--glass-border)', cursor: 'pointer', color: isMuted ? 'var(--error)' : 'var(--text-muted)', padding: 6, borderRadius: 8, display: 'flex', alignItems: 'center' }}
            >
              {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>

            {/* Clear context */}
            <button
              id="btn-clear-context"
              onClick={() => { clearContext(); resetSession(); toast.success('Context cleared') }}
              title="Clear conversation memory"
              className="btn btn-ghost"
              style={{ padding: '6px 12px', fontSize: 12 }}
            >
              Clear
            </button>
          </div>
        </header>

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <ChatWindow />
        </div>

        {/* Bottom control zone */}
        <div
          style={{
            padding: '16px 24px 20px',
            borderTop: '1px solid var(--glass-border)',
            background: 'rgba(255,255,255,0.02)',
            display: 'flex', flexDirection: 'column', gap: 16, flexShrink: 0,
          }}
        >
          {/* Audio player indicator */}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <AudioPlayer />
          </div>

          {/* Mic + text row */}
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 20 }}>
            {/* Text input */}
            <form
              onSubmit={handleSendText}
              style={{ flex: 1, display: 'flex', gap: 8 }}
            >
              <input
                ref={textInputRef}
                id="text-chat-input"
                className="input"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type a message or use the mic…"
                disabled={sendingText}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendText(e) } }}
                style={{ flex: 1 }}
              />
              <button
                type="submit"
                id="btn-send-text"
                disabled={!textInput.trim() || sendingText}
                className="btn btn-primary"
                style={{ padding: '12px 16px', flexShrink: 0 }}
              >
                <Send size={16} />
              </button>
            </form>

            {/* Mic button */}
            <div style={{ flexShrink: 0 }}>
              <MicButton socket={{ ...socket, connected: wsConnected }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
