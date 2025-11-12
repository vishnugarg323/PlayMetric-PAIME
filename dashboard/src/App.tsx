import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Games from './pages/Games'
import GameDetails from './pages/GameDetails'
import Sessions from './pages/Sessions'
import CreateSession from './pages/CreateSession'
import SessionDetails from './pages/SessionDetails'
import Analytics from './pages/Analytics'
import BugTracker from './pages/BugTracker'
import VersionComparison from './pages/VersionComparison'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="games" element={<Games />} />
          <Route path="games/:gameId" element={<GameDetails />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/create" element={<CreateSession />} />
          <Route path="sessions/:sessionId" element={<SessionDetails />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="bugs" element={<BugTracker />} />
          <Route path="version-comparison" element={<VersionComparison />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
