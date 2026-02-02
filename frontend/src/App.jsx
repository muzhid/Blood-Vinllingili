import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { useEffect, useState } from 'react'
import { supabase } from './lib/supabaseClient'
import { Toaster } from "@/components/ui/sonner"
import { ThemeProvider } from "@/components/theme-provider"

function App() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check Local Storage for Custom Admin Auth
    const storedUser = localStorage.getItem('admin_user')
    if (storedUser) {
      setSession(JSON.parse(storedUser))
    }
    setLoading(false)
  }, [])

  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>

  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <Router>
        <Routes>
          <Route path="/" element={!session ? <Login /> : <Navigate to="/dashboard" />} />
          <Route path="/dashboard" element={session ? <Dashboard /> : <Navigate to="/" />} />
        </Routes>
        <Toaster />
      </Router>
    </ThemeProvider>
  )
}

export default App
