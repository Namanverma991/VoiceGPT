import { create } from 'zustand'

export const useVoiceStore = create((set, get) => ({
  // Session
  sessionId: null,
  sessions: [],
  messages: [],

  // Voice state
  isRecording: false,
  isProcessing: false,
  isAISpeaking: false,
  isMuted: false,

  // Transcript
  transcript: '',
  language: 'en',

  // WebSocket
  wsConnected: false,

  setSession: (id) => set({ sessionId: id }),
  setSessions: (sessions) => set({ sessions }),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  setRecording: (v) => set({ isRecording: v }),
  setProcessing: (v) => set({ isProcessing: v }),
  setAISpeaking: (v) => set({ isAISpeaking: v }),
  setMuted: (v) => set({ isMuted: v }),
  setTranscript: (v) => set({ transcript: v }),
  setLanguage: (v) => set({ language: v }),
  setWsConnected: (v) => set({ wsConnected: v }),

  resetSession: () => set({
    messages: [],
    transcript: '',
    isRecording: false,
    isProcessing: false,
    isAISpeaking: false,
  }),
}))
