export default function SessionsPage() {
  // Static demo sessions for all games
  const sessions = [
    {
      session_id: 'demo-session-1',
      game_name: 'Screw Unscrew',
      status: 'active',
      start_time: new Date().toISOString(),
    },
    {
      session_id: 'demo-session-2',
      game_name: 'Factory Jam',
      status: 'completed',
      start_time: new Date().toISOString(),
    },
    {
      session_id: 'demo-session-3',
      game_name: 'Blocky Knits',
      status: 'active',
      start_time: new Date().toISOString(),
    },
    {
      session_id: 'demo-session-4',
      game_name: 'Make Them 100!',
      status: 'completed',
      start_time: new Date().toISOString(),
    }
  ];
  const isLoading = false;
  
  if (isLoading) return <div>Loading...</div>
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Testing Sessions</h1>
      
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Game</th>
                <th className="text-left py-2">Status</th>
                <th className="text-left py-2">Started</th>
                <th className="text-left py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.session_id} className="border-b">
                  <td className="py-3">{session.game_name}</td>
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      session.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {session.status}
                    </span>
                  </td>
                  <td className="py-3">{new Date(session.start_time).toLocaleString()}</td>
                  <td className="py-3">
                    <a
                      href={`/sessions/${session.session_id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      View Details
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}