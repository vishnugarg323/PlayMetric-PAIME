import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Games from './pages/Games'
import GameDetails from './pages/GameDetails'
import Sessions from './pages/Sessions'
import CreateSession from './pages/CreateSession'
import SessionDetailsNew from './pages/SessionDetailsNew'
import Analytics from './pages/Analytics'
import BugTracker from './pages/BugTracker'
import VersionComparison from './pages/VersionComparison'
import Settings from './pages/Settings'
import About from './pages/About'
import Admin from './pages/Admin'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public route - Login */}
          <Route path="/login" element={<Login />} />
          
          {/* Public route - About (no authentication required) */}
          <Route path="/about" element={<About />} />
          
          {/* Protected routes - require authentication */}
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="games" element={<Games />} />
            <Route path="games/:gameId" element={<GameDetails />} />
            <Route path="sessions" element={<Sessions />} />
            <Route path="sessions/create" element={<CreateSession />} />
            <Route path="sessions/:sessionId" element={<SessionDetailsNew />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="bugs" element={<BugTracker />} />
            <Route path="version-comparison" element={<VersionComparison />} />
            <Route path="settings" element={<Settings />} />
            <Route path="admin" element={<Admin />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
