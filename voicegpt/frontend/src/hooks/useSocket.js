import { useEffect, useRef, useCallback } from 'react'
import { VoiceSocket } from '../services/socket.js'
import { useAuthStore } from '../store/authStore.js'
import { useVoiceStore } from '../store/voiceStore.js'

/**
 * useSocket — manages WebSocket lifecycle for a voice session.
 * Handles audio chunk buffering and sequential WAV playback via Web Audio API.
 * Falls back to browser SpeechSynthesis when audio is silent (mock/dev mode).
 */
export function useSocket(sessionId) {
  const token = useAuthStore((s) => s.token)
  const language = useVoiceStore((s) => s.language)
  const setWsConnected = useVoiceStore((s) => s.setWsConnected)
  const setProcessing = useVoiceStore((s) => s.setProcessing)
  const setAISpeaking = useVoiceStore((s) => s.setAISpeaking)
  const setTranscript = useVoiceStore((s) => s.setTranscript)
  const addMessage = useVoiceStore((s) => s.addMessage)

  const socketRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const audioCtxRef = useRef(null)
  const llmBufferRef = useRef('')   // accumulate streamed LLM tokens
  const aiMsgIdRef = useRef(null)   // track current AI message id

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    return audioCtxRef.current
  }, [])

  // Check if a decoded AudioBuffer is all silence (mock mode produces zeros)
  const isSilentBuffer = useCallback((audioBuffer) => {
    const data = audioBuffer.getChannelData(0)
    for (let i = 0; i < data.length; i++) {
      if (Math.abs(data[i]) > 0.001) return false
    }
    return true
  }, [])

  // Speak text via browser SpeechSynthesis API
  const speakWithSynthesis = useCallback((text, onEnd) => {
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = language === 'hi' ? 'hi-IN' : 'en-US'
    utter.rate = 1.05
    utter.pitch = 1.0
    utter.volume = 1.0
    utter.onend = onEnd || (() => {})
    utter.onerror = onEnd || (() => {})
    window.speechSynthesis.speak(utter)
  }, [language])

  const playNextChunk = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return
    isPlayingRef.current = true
    setAISpeaking(true)

    const { buffer, text } = audioQueueRef.current.shift()

    const onDone = () => {
      isPlayingRef.current = false
      if (audioQueueRef.current.length > 0) {
        playNextChunk()
      } else {
        setAISpeaking(false)
      }
    }

    try {
      const ctx = getAudioContext()
      const decoded = await ctx.decodeAudioData(buffer.slice(0))

      // If WAV is silent (mock mode), use SpeechSynthesis instead
      if (isSilentBuffer(decoded)) {
        isPlayingRef.current = false
        speakWithSynthesis(text || 'Mock response', onDone)
        return
      }

      const source = ctx.createBufferSource()
      source.buffer = decoded
      source.connect(ctx.destination)
      source.onended = onDone
      source.start()
    } catch (e) {
      console.error('[Audio] decode error:', e)
      isPlayingRef.current = false
      // Fallback to speech synthesis on any error
      speakWithSynthesis(text || '', onDone)
    }
  }, [getAudioContext, isSilentBuffer, speakWithSynthesis, setAISpeaking])

  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case 'connected':
        setWsConnected(true)
        break

      case 'transcript':
        setProcessing(false)
        if (event.text) {
          setTranscript(event.text)
          addMessage({ role: 'user', content: event.text, id: Date.now() })
        }
        // Reset buffer for new AI turn
        llmBufferRef.current = ''
        aiMsgIdRef.current = Date.now() + 1
        break

      case 'llm_token':
        if (event.token) {
          llmBufferRef.current += event.token
        }
        break

      // KEY FIX: server sends audio_chunk as base64 JSON, not raw binary
      case 'audio_chunk': {
        if (!event.data) break
        try {
          const binary = atob(event.data)
          const ab = new ArrayBuffer(binary.length)
          const view = new Uint8Array(ab)
          for (let i = 0; i < binary.length; i++) {
            view[i] = binary.charCodeAt(i)
          }
          audioQueueRef.current.push({ buffer: ab, text: llmBufferRef.current })
          playNextChunk()
        } catch (e) {
          console.error('[WS] audio_chunk decode error:', e)
        }
        break
      }

      case 'audio_done':
        setProcessing(false)
        // Show final AI text in chat
        if (llmBufferRef.current) {
          addMessage({
            role: 'assistant',
            content: llmBufferRef.current,
            id: aiMsgIdRef.current || Date.now(),
          })
          llmBufferRef.current = ''
        }
        break

      case 'interrupted':
        audioQueueRef.current = []
        isPlayingRef.current = false
        window.speechSynthesis.cancel()
        setAISpeaking(false)
        setProcessing(false)
        break

      case 'error':
        console.error('[WS] Error:', event.error_code, event.message)
        setProcessing(false)
        setAISpeaking(false)
        break

      default:
        break
    }
  }, [addMessage, playNextChunk, setAISpeaking, setProcessing, setTranscript, setWsConnected])

  // Raw binary chunks (legacy path, kept for compatibility)
  const handleAudioChunk = useCallback((buffer) => {
    audioQueueRef.current.push({ buffer, text: llmBufferRef.current })
    playNextChunk()
  }, [playNextChunk])

  useEffect(() => {
    if (!sessionId || !token) return

    const socket = new VoiceSocket(sessionId, token, {
      onEvent: handleEvent,
      onAudioChunk: handleAudioChunk,
      onOpen: () => setWsConnected(true),
      onClose: () => {
        setWsConnected(false)
        window.speechSynthesis.cancel()
      },
      onError: (e) => console.error('[WS] Connection error:', e),
    })

    socket.connect(language)
    socketRef.current = socket

    return () => {
      socket.disconnect()
      socketRef.current = null
      setWsConnected(false)
      window.speechSynthesis.cancel()
    }
  }, [sessionId, token, language, handleEvent, handleAudioChunk, setWsConnected])

  return {
    socket: socketRef.current,
    interrupt: () => {
      window.speechSynthesis.cancel()
      socketRef.current?.interrupt()
    },
    clearContext: () => socketRef.current?.clearContext(),
    sendText: (text) => socketRef.current?.sendTextMessage(text, language),
  }
}
