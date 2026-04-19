import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Volume2 } from 'lucide-react'
import { useVoiceStore } from '../store/voiceStore.js'

/**
 * AudioPlayer — visual indicator when AI is speaking.
 * Draws a real-time bar animation during TTS playback.
 */
export default function AudioPlayer() {
  const isAISpeaking = useVoiceStore((s) => s.isAISpeaking)
  const canvasRef = useRef(null)
  const animRef = useRef(null)
  const frameRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const BAR_COUNT = 24

    const drawIdle = () => {
      ctx.clearRect(0, 0, W, H)
      const barW = (W / BAR_COUNT) - 2
      for (let i = 0; i < BAR_COUNT; i++) {
        const h = 4
        ctx.fillStyle = 'rgba(124,58,237,0.2)'
        ctx.beginPath()
        ctx.roundRect(i * (barW + 2), H / 2 - h / 2, barW, h, 2)
        ctx.fill()
      }
    }

    const drawActive = () => {
      ctx.clearRect(0, 0, W, H)
      frameRef.current++
      const barW = (W / BAR_COUNT) - 2
      for (let i = 0; i < BAR_COUNT; i++) {
        const t = frameRef.current * 0.06 + i * 0.4
        const h = Math.abs(Math.sin(t) * (H * 0.75)) + 4
        const hue = 260 + (i / BAR_COUNT) * 60
        ctx.fillStyle = `hsla(${hue}, 75%, 65%, 0.9)`
        ctx.beginPath()
        ctx.roundRect(i * (barW + 2), H / 2 - h / 2, barW, h, 3)
        ctx.fill()
      }
      animRef.current = requestAnimationFrame(drawActive)
    }

    if (isAISpeaking) {
      cancelAnimationFrame(animRef.current)
      drawActive()
    } else {
      cancelAnimationFrame(animRef.current)
      drawIdle()
    }

    return () => cancelAnimationFrame(animRef.current)
  }, [isAISpeaking])

  return (
    <motion.div
      animate={{ opacity: isAISpeaking ? 1 : 0.4 }}
      transition={{ duration: 0.3 }}
      style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}
    >
      <Volume2
        size={16}
        style={{ color: isAISpeaking ? 'var(--accent-3)' : 'var(--text-muted)', flexShrink: 0 }}
      />
      <canvas
        ref={canvasRef}
        id="audio-player-canvas"
        width={200}
        height={36}
        style={{ borderRadius: 8 }}
      />
      {isAISpeaking && (
        <span style={{ fontSize: 12, color: 'var(--accent-3)', whiteSpace: 'nowrap' }}>
          Speaking…
        </span>
      )}
    </motion.div>
  )
}
