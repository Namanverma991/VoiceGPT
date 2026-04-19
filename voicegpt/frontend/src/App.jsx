import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import { useAuthStore } from './store/authStore.js'

function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(15,15,30,0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#f8fafc',
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(20px)',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#0a0a14' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0a0a14' } },
        }}
      />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Home />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
