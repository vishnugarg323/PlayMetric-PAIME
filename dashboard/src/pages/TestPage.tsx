import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function TestPage() {
  const [games, setGames] = useState([])
  const [sessions, setSessions] = useState([])
  const [emulatorStatus, setEmulatorStatus] = useState('checking...')
  
  useEffect(() => {
    // Test API connections
    const testConnections = async () => {
      try {
        // Test backend
        const gamesData = await api.getGames()
        setGames(gamesData)
        
        const sessionsData = await api.getSessions()
        setSessions(sessionsData)
        
        // Test emulator
        const emulatorResponse = await fetch('http://localhost:5555/')
        if (emulatorResponse.ok) {
          setEmulatorStatus('Connected')
        } else {
          setEmulatorStatus('Not responding')
        }
      } catch (error) {
        console.error('Connection test failed:', error)
      }
    }
    
    testConnections()
  }, [])
  
  const triggerProcessing = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/test-trigger', {
        method: 'POST'
      })
      const data = await response.json()
      alert('Processing triggered: ' + JSON.stringify(data))
    } catch (error) {
      alert('Failed to trigger processing')
    }
  }
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">System Test Page</h1>
      
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">API Status</h2>
          <p>Games in DB: {games.length}</p>
          <p>Sessions in DB: {sessions.length}</p>
          <p>Emulator: {emulatorStatus}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          <button 
            onClick={triggerProcessing}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Trigger APK Processing
          </button>
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Games</h2>
        <pre>{JSON.stringify(games, null, 2)}</pre>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Sessions</h2>
        <pre>{JSON.stringify(sessions, null, 2)}</pre>
      </div>
    </div>
  )
}