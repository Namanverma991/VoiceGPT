import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { Zap, Mail, Lock, User, Globe, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore.js'

export default function Login() {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loginAction = useAuthStore((s) => s.login)
  const registerAction = useAuthStore((s) => s.register)

  const [form, setForm] = useState({
    email: '', password: '', username: '', language: 'en',
  })

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'login') {
        await loginAction(form.email, form.password)
        toast.success('Welcome back! 🎉')
        navigate('/')
      } else {
        await registerAction({
          email: form.email,
          password: form.password,
          username: form.username,
          preferred_language: form.language,
        })
        toast.success('Account created! Please log in.')
        setMode('login')
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Something went wrong'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px',
        background: 'radial-gradient(ellipse at top, rgba(124,58,237,0.15) 0%, transparent 60%), var(--bg-primary)',
      }}
    >
      <div style={{ width: '100%', maxWidth: 440 }}>
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ textAlign: 'center', marginBottom: 40 }}
        >
          <motion.div
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 4, repeat: Infinity }}
            style={{
              width: 72, height: 72, borderRadius: '50%', margin: '0 auto 16px',
              background: 'linear-gradient(135deg, #7c3aed, #06b6d4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 40px rgba(124,58,237,0.5)',
            }}
          >
            <Zap size={32} color="white" fill="white" />
          </motion.div>
          <h1 className="gradient-text" style={{ fontSize: '2.2rem', marginBottom: 8 }}>
            VoiceGPT
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            Your real-time AI voice assistant
          </p>
        </motion.div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
          style={{ padding: 32 }}
        >
          {/* Tab switcher */}
          <div
            style={{
              display: 'flex', background: 'rgba(255,255,255,0.04)',
              borderRadius: 12, padding: 4, marginBottom: 28,
            }}
          >
            {['login', 'register'].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 9, border: 'none',
                  cursor: 'pointer', fontFamily: 'Inter, sans-serif', fontWeight: 600,
                  fontSize: 14, transition: 'all 0.25s ease',
                  background: mode === m ? 'linear-gradient(135deg,#7c3aed,#06b6d4)' : 'transparent',
                  color: mode === m ? 'white' : 'var(--text-muted)',
                }}
              >
                {m === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Username (register only) */}
            {mode === 'register' && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Username
                </label>
                <div style={{ position: 'relative' }}>
                  <User size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    className="input" type="text" required minLength={3}
                    placeholder="yourusername" value={form.username}
                    onChange={(e) => update('username', e.target.value)}
                    style={{ paddingLeft: 36 }}
                    id="input-username"
                  />
                </div>
              </motion.div>
            )}

            {/* Email */}
            <div>
              <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Email
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  className="input" type="email" required
                  placeholder="you@example.com" value={form.email}
                  onChange={(e) => update('email', e.target.value)}
                  style={{ paddingLeft: 36 }}
                  id="input-email"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  className="input" type={showPassword ? 'text' : 'password'} required minLength={8}
                  placeholder="••••••••" value={form.password}
                  onChange={(e) => update('password', e.target.value)}
                  style={{ paddingLeft: 36, paddingRight: 40 }}
                  id="input-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Language (register only) */}
            {mode === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Language preference
                </label>
                <div style={{ position: 'relative' }}>
                  <Globe size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <select
                    className="input" value={form.language}
                    onChange={(e) => update('language', e.target.value)}
                    style={{ paddingLeft: 36, cursor: 'pointer' }}
                    id="select-language"
                  >
                    <option value="en">🇬🇧 English</option>
                    <option value="hi">🇮🇳 Hindi</option>
                    <option value="hinglish">🇮🇳 Hinglish</option>
                  </select>
                </div>
              </div>
            )}

            {/* Submit */}
            <motion.button
              type="submit"
              id="btn-submit"
              disabled={loading}
              className="btn btn-primary"
              whileHover={{ scale: loading ? 1 : 1.02 }}
              whileTap={{ scale: loading ? 1 : 0.98 }}
              style={{ marginTop: 8, height: 48, opacity: loading ? 0.7 : 1 }}
            >
              {loading ? (
                <div className="spinner" style={{ borderTopColor: 'white' }} />
              ) : mode === 'login' ? (
                'Sign In'
              ) : (
                'Create Account'
              )}
            </motion.button>
          </form>
        </motion.div>

        <p style={{ textAlign: 'center', marginTop: 24, fontSize: 13, color: 'var(--text-muted)' }}>
          Production-grade Voice AI · Open Source
        </p>
      </div>
    </div>
  )
}
