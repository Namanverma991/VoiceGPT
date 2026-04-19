import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, User, Clock } from 'lucide-react'
import { useVoiceStore } from '../store/voiceStore.js'

const roleConfig = {
  user: {
    icon: User,
    label: 'You',
    bg: 'rgba(124, 58, 237, 0.12)',
    border: 'rgba(124, 58, 237, 0.25)',
    align: 'flex-end',
    textAlign: 'right',
  },
  assistant: {
    icon: Bot,
    label: 'VoiceGPT',
    bg: 'rgba(6, 182, 212, 0.1)',
    border: 'rgba(6, 182, 212, 0.2)',
    align: 'flex-start',
    textAlign: 'left',
  },
}

function MessageBubble({ message, index }) {
  const cfg = roleConfig[message.role] || roleConfig.assistant

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, delay: index * 0.02 }}
      style={{ display: 'flex', justifyContent: cfg.align }}
    >
      <div style={{ maxWidth: '78%' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            marginBottom: 6,
            justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
          }}
        >
          <cfg.icon size={13} style={{ color: 'var(--text-muted)' }} />
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
            {cfg.label}
          </span>
        </div>

        {/* Bubble */}
        <div
          style={{
            padding: '12px 16px',
            borderRadius: message.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
            background: cfg.bg,
            border: `1px solid ${cfg.border}`,
            backdropFilter: 'blur(10px)',
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.65,
              color: 'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              textAlign: cfg.textAlign,
            }}
          >
            {message.content}
          </p>
        </div>

        {/* Latency badge */}
        {message.latency_ms > 0 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              marginTop: 4,
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <Clock size={10} style={{ color: 'var(--text-muted)' }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {message.latency_ms}ms
            </span>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      style={{ display: 'flex', alignItems: 'center', gap: 8 }}
    >
      <Bot size={14} style={{ color: 'var(--text-muted)' }} />
      <div
        style={{
          display: 'flex', gap: 4, padding: '10px 14px',
          background: 'rgba(6,182,212,0.08)',
          border: '1px solid rgba(6,182,212,0.2)',
          borderRadius: '18px 18px 18px 4px',
        }}
      >
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-3)' }}
            animate={{ scaleY: [1, 1.8, 1] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </motion.div>
  )
}

/**
 * ChatWindow — scrolling message history with typing indicator.
 */
export default function ChatWindow() {
  const messages = useVoiceStore((s) => s.messages)
  const isProcessing = useVoiceStore((s) => s.isProcessing)
  const isAISpeaking = useVoiceStore((s) => s.isAISpeaking)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isProcessing])

  if (messages.length === 0 && !isProcessing) {
    return (
      <div
        style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
          padding: 32, opacity: 0.5,
        }}
      >
        <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 3, repeat: Infinity }}>
          <Bot size={48} style={{ color: 'var(--accent-3)' }} />
        </motion.div>
        <p style={{ textAlign: 'center', fontSize: 14, color: 'var(--text-muted)' }}>
          Press the mic button and start speaking.<br />VoiceGPT is ready to listen.
        </p>
      </div>
    )
  }

  return (
    <div
      id="chat-window"
      style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}
    >
      <AnimatePresence initial={false}>
        {messages.map((msg, i) => (
          <MessageBubble key={msg.id || i} message={msg} index={i} />
        ))}
      </AnimatePresence>

      <AnimatePresence>
        {(isProcessing || isAISpeaking) && <TypingIndicator />}
      </AnimatePresence>

      <div ref={bottomRef} />
    </div>
  )
}
