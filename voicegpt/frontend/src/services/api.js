import axios from 'axios'
import { useAuthStore } from '../store/authStore.js'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Auto-attach JWT token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 — clear session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Chat API ──────────────────────────────────────────────
export const chatApi = {
  createSession: (data) => api.post('/api/v1/chat/sessions', data),
  listSessions: () => api.get('/api/v1/chat/sessions'),
  getSession: (id) => api.get(`/api/v1/chat/sessions/${id}`),
  deleteSession: (id) => api.delete(`/api/v1/chat/sessions/${id}`),
  sendText: (data) => api.post('/api/v1/chat/text', data),
}

// ── Voice API ─────────────────────────────────────────────
export const voiceApi = {
  transcribe: (file, language) => {
    const form = new FormData()
    form.append('file', file)
    if (language) form.append('language', language)
    return api.post('/api/v1/voice/transcribe', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  synthesize: (text, language = 'en') =>
    api.post('/api/v1/voice/synthesize', { text, language }, { responseType: 'blob' }),
  status: () => api.get('/api/v1/voice/status'),
}

// ── Auth API ──────────────────────────────────────────────
export const authApi = {
  register: (data) => api.post('/api/v1/auth/register', data),
  login: (data) => api.post('/api/v1/auth/login', data),
  me: () => api.get('/api/v1/auth/me'),
}
