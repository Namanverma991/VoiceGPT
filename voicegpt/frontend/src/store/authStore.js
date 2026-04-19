import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../services/api.js'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,

      setTokens: (access, refresh) => set({ token: access, refreshToken: refresh }),

      login: async (email, password) => {
        const res = await api.post('/api/v1/auth/login', { email, password })
        const { access_token, refresh_token } = res.data
        set({ token: access_token, refreshToken: refresh_token })
        // Fetch profile
        const me = await api.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        })
        set({ user: me.data })
        return me.data
      },

      register: async (payload) => {
        await api.post('/api/v1/auth/register', payload)
      },

      logout: async () => {
        const { token } = get()
        if (token) {
          try {
            await api.post('/api/v1/auth/logout', {}, {
              headers: { Authorization: `Bearer ${token}` },
            })
          } catch {}
        }
        set({ token: null, refreshToken: null, user: null })
      },

      fetchMe: async () => {
        const { token } = get()
        if (!token) return
        const res = await api.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        set({ user: res.data })
      },
    }),
    {
      name: 'voicegpt-auth',
      partialize: (state) => ({ token: state.token, refreshToken: state.refreshToken, user: state.user }),
    }
  )
)
