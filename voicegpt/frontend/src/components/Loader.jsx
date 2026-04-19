import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

/**
 * Loader — pulsing logo loader for full-page loading states.
 */
export default function Loader({ message = 'Loading…' }) {
  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        height: '100vh', gap: 24,
      }}
    >
      <div style={{ position: 'relative' }}>
        {[1, 2, 3].map((i) => (
          <motion.div
            key={i}
            style={{
              position: 'absolute', inset: -8 * i, borderRadius: '50%',
              border: '1px solid rgba(124,58,237,0.3)',
              pointerEvents: 'none',
            }}
            animate={{ scale: [1, 1.3], opacity: [0.5, 0] }}
            transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
          />
        ))}
        <motion.div
          animate={{ rotate: 360, scale: [1, 1.02, 1] }}
          transition={{ rotate: { duration: 3, repeat: Infinity, ease: 'linear' }, scale: { duration: 2, repeat: Infinity } }}
          style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'linear-gradient(135deg, #7c3aed, #06b6d4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 40px rgba(124,58,237,0.5)',
          }}
        >
          <Zap size={28} color="white" fill="white" />
        </motion.div>
      </div>
      <motion.p
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        style={{ color: 'var(--text-muted)', fontSize: 14, margin: 0 }}
      >
        {message}
      </motion.p>
    </div>
  )
}
