/**
 * WebSocket service — manages the voice channel WebSocket connection.
 */

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export class VoiceSocket {
  constructor(sessionId, token, { onEvent, onAudioChunk, onOpen, onClose, onError } = {}) {
    this.sessionId = sessionId
    this.token = token
    this.onEvent = onEvent || (() => {})
    this.onAudioChunk = onAudioChunk || (() => {})
    this.onOpen = onOpen || (() => {})
    this.onClose = onClose || (() => {})
    this.onError = onError || (() => {})
    this.ws = null
    this.pingInterval = null
  }

  connect(language = 'en') {
    const url = `${WS_BASE}/ws/voice/${this.sessionId}?token=${this.token}&language=${language}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.onOpen()
      // Keepalive ping every 30s
      this.pingInterval = setInterval(() => this.send({ type: 'ping' }), 30000)
    }

    this.ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'audio_chunk' && data.data) {
            // Decode base64 → ArrayBuffer for audio playback
            const binary = atob(data.data)
            const bytes = new Uint8Array(binary.length)
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
            this.onAudioChunk(bytes.buffer, data.chunk_id)
          } else {
            this.onEvent(data)
          }
        } catch (e) {
          console.error('[VoiceSocket] JSON parse error:', e)
        }
      }
    }

    this.ws.onclose = (event) => {
      clearInterval(this.pingInterval)
      this.onClose(event)
    }

    this.ws.onerror = (err) => {
      this.onError(err)
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  sendBinary(buffer) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(buffer)
    }
  }

  startStream() { this.send({ type: 'start_stream' }) }
  stopStream() { this.send({ type: 'stop_stream' }) }
  interrupt() { this.send({ type: 'interrupt' }) }
  clearContext() { this.send({ type: 'clear_context' }) }

  sendTextMessage(text, language = 'en') {
    this.send({ type: 'text_message', text, language })
  }

  disconnect() {
    clearInterval(this.pingInterval)
    this.ws?.close()
  }

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
