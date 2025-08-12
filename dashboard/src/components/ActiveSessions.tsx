import { Link } from 'react-router-dom'
import { PlayCircle, StopCircle } from 'lucide-react'

interface Session {
  session_id: string
  game_name: string
  version: string
  start_time: string
  status: string
}

interface ActiveSessionsProps {
  sessions: Session[]
}

export default function ActiveSessions({ sessions }: ActiveSessionsProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Active Sessions</h3>
      
      <div className="space-y-4">
        {sessions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No active sessions</p>
        ) : (
          sessions.map((session) => (
            <Link
              key={session.session_id}
              to={`/sessions/${session.session_id}`}
              className="block p-4 border rounded-lg hover:bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{session.game_name}</h4>
                  <p className="text-sm text-gray-600">v{session.version}</p>
                </div>
                {session.status === 'active' ? (
                  <PlayCircle className="w-6 h-6 text-green-500" />
                ) : (
                  <StopCircle className="w-6 h-6 text-gray-400" />
                )}
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}