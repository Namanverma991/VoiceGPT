import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Square, Zap } from 'lucide-react'
import { useVoiceStore } from '../store/voiceStore.js'

/**
 * MicButton — animated microphone button with waveform visualization.
 * Uses MediaRecorder API to capture audio and stream chunks via WebSocket.
 */
export default function MicButton({ socket }) {
  const isRecording = useVoiceStore((s) => s.isRecording)
  const isProcessing = useVoiceStore((s) => s.isProcessing)
  const isAISpeaking = useVoiceStore((s) => s.isAISpeaking)
  const isMuted = useVoiceStore((s) => s.isMuted)
  const setRecording = useVoiceStore((s) => s.setRecording)
  const setProcessing = useVoiceStore((s) => s.setProcessing)

  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const analyserRef = useRef(null)
  const animFrameRef = useRef(null)
  const canvasRef = useRef(null)
  const [level, setLevel] = useState(0)

  // ── Audio level visualizer ──────────────────────────────
  const startVisualizer = (stream) => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const src = ctx.createMediaStreamSource(stream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    src.connect(analyser)
    analyserRef.current = analyser

    const data = new Uint8Array(analyser.frequencyBinCount)

    const draw = () => {
      analyser.getByteFrequencyData(data)
      const avg = data.slice(0, 20).reduce((a, b) => a + b, 0) / 20
      setLevel(Math.min(100, avg))

      if (canvasRef.current) {
        const canvas = canvasRef.current
        const ctx2d = canvas.getContext('2d')
        const W = canvas.width, H = canvas.height
        ctx2d.clearRect(0, 0, W, H)

        const barCount = 32
        const barWidth = W / barCount - 2
        for (let i = 0; i < barCount; i++) {
          const barHeight = (data[i] / 255) * H * 0.9
          const hue = 260 + (i / barCount) * 60
          ctx2d.fillStyle = `hsla(${hue}, 80%, 65%, 0.85)`
          ctx2d.beginPath()
          ctx2d.roundRect(
            i * (barWidth + 2),
            H / 2 - barHeight / 2,
            barWidth,
            barHeight,
            3
          )
          ctx2d.fill()
        }
      }

      animFrameRef.current = requestAnimationFrame(draw)
    }
    draw()
  }

  const stopVisualizer = () => {
    cancelAnimationFrame(animFrameRef.current)
    setLevel(0)
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d')
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
    }
  }

  // ── Start recording ─────────────────────────────────────
  const startRecording = async () => {
    if (isAISpeaking && socket) {
      socket.interrupt()
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })
      streamRef.current = stream
      startVisualizer(stream)

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mediaRecorderRef.current = recorder

      socket?.startStream()

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && socket?.connected) {
          e.data.arrayBuffer().then((buf) => socket.socket.sendBinary(buf))
        }
      }
      recorder.start(250) // send chunks every 250ms
      setRecording(true)
    } catch (err) {
      console.error('Mic error:', err)
    }
  }

  // ── Stop recording ──────────────────────────────────────
  const stopRecording = () => {
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    stopVisualizer()
    socket?.stopStream()
    setRecording(false)
    setProcessing(true)
  }

  const handleClick = () => {
    if (isRecording) stopRecording()
    else startRecording()
  }

  // Cleanup on unmount
  useEffect(() => () => {
    stopVisualizer()
    streamRef.current?.getTracks().forEach((t) => t.stop())
  }, [])

  const isDisabled = isProcessing

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      {/* Waveform Canvas */}
      <canvas
        ref={canvasRef}
        width={280}
        height={56}
        style={{
          borderRadius: 12,
          background: 'rgba(255,255,255,0.03)',
          opacity: isRecording ? 1 : 0.3,
          transition: 'opacity 0.3s ease',
        }}
      />

      {/* Mic Button */}
      <div style={{ position: 'relative' }}>
        {/* Pulse rings when recording */}
        <AnimatePresence>
          {isRecording && (
            <>
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  style={{
                    position: 'absolute', inset: -4 * i, borderRadius: '50%',
                    border: '2px solid rgba(124,58,237,0.4)',
                    pointerEvents: 'none',
                  }}
                  animate={{ scale: [1, 1.5], opacity: [0.6, 0] }}
                  transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
                />
              ))}
            </>
          )}
        </AnimatePresence>

        <motion.button
          id="mic-button"
          onClick={handleClick}
          disabled={isDisabled}
          whileHover={{ scale: isDisabled ? 1 : 1.05 }}
          whileTap={{ scale: isDisabled ? 1 : 0.95 }}
          style={{
            width: 80, height: 80, borderRadius: '50%', border: 'none',
            cursor: isDisabled ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: isRecording
              ? 'linear-gradient(135deg, #7c3aed, #ef4444)'
              : isProcessing
              ? 'linear-gradient(135deg, #0891b2, #06b6d4)'
              : 'linear-gradient(135deg, #7c3aed, #06b6d4)',
            boxShadow: isRecording
              ? '0 0 30px rgba(239,68,68,0.5), 0 0 60px rgba(124,58,237,0.3)'
              : '0 0 30px rgba(124,58,237,0.4), 0 0 60px rgba(6,182,212,0.2)',
            opacity: isDisabled ? 0.6 : 1,
            transition: 'background 0.3s ease, box-shadow 0.3s ease',
            position: 'relative', zIndex: 1,
          }}
        >
          {isProcessing ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Zap size={28} color="white" fill="white" />
            </motion.div>
          ) : isRecording ? (
            <Square size={28} color="white" fill="white" />
          ) : isMuted ? (
            <MicOff size={28} color="white" />
          ) : (
            <Mic size={28} color="white" />
          )}
        </motion.button>
      </div>

      {/* Status label */}
      <motion.p
        key={isRecording ? 'rec' : isProcessing ? 'proc' : 'idle'}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}
      >
        {isRecording
          ? '🔴 Recording — tap to stop'
          : isProcessing
          ? '⚡ Processing...'
          : isAISpeaking
          ? '🔊 AI speaking — tap to interrupt'
          : '🎤 Tap to speak'}
      </motion.p>
    </div>
  )
}
