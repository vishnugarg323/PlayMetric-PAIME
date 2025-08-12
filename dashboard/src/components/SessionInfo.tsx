import { Clock, Gamepad2, Hash } from 'lucide-react'

interface SessionInfoProps {
  session: {
    session_id: string
    game_name: string
    version: string
    start_time: string
    status: string
  }
}

export default function SessionInfo({ session }: SessionInfoProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Session Information</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center">
          <Gamepad2 className="w-5 h-5 text-gray-500 mr-2" />
          <div>
            <p className="text-sm text-gray-600">Game</p>
            <p className="font-medium">{session.game_name}</p>
          </div>
        </div>
        
        <div className="flex items-center">
          <Hash className="w-5 h-5 text-gray-500 mr-2" />
          <div>
            <p className="text-sm text-gray-600">Version</p>
            <p className="font-medium">{session.version}</p>
          </div>
        </div>
        
        <div className="flex items-center">
          <Clock className="w-5 h-5 text-gray-500 mr-2" />
          <div>
            <p className="text-sm text-gray-600">Started</p>
            <p className="font-medium">{new Date(session.start_time).toLocaleString()}</p>
          </div>
        </div>
        
        <div className="flex items-center">
          <div className="w-5 h-5 mr-2"></div>
          <div>
            <p className="text-sm text-gray-600">Status</p>
            <p className="font-medium">{session.status}</p>
          </div>
        </div>
      </div>
    </div>
  )
}