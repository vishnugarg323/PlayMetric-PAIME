import { useEffect, useState } from 'react'
import { Play, Pause, Maximize2 } from 'lucide-react'

interface GamePlayerProps {
  sessionId: string;
}

export default function GamePlayer({ sessionId }: GamePlayerProps) {
  const handleStopSession = async () => {
    if (!sessionId) return;
    try {
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
      setIsPlaying(false);
    } catch (err) {
      console.error('Failed to stop session:', err);
    }
  }
  const [screenshot, setScreenshot] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState(true);
  const [gamePhase] = useState('menu');
  const [aiActions, setAiActions] = useState<any[]>([]);
  const [telemetry, setTelemetry] = useState<any[]>([]);
  const [aiAnalysis, setAiAnalysis] = useState<any[]>([]);

  // Poll for live screenshot every 2 seconds
  useEffect(() => {
    if (!isPlaying || !sessionId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/sessions/${sessionId}/screenshots?limit=1`)
  const data = await res.json();
        if (data.screenshots && data.screenshots.length > 0) {
          setScreenshot(`data:image/png;base64,${data.screenshots[0].image}`)
        }
      } catch (err) {
        setScreenshot('')
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [isPlaying, sessionId])

  // Poll for session AI actions, telemetry, and analysis every 5 seconds
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/sessions/${sessionId}`)
  const data = await res.json();
        setAiActions(data.ai_actions || [])
        setTelemetry(data.telemetry || [])
        setAiAnalysis(data.ai_analysis || [])
      } catch (err) {
        setAiActions([])
        setTelemetry([])
        setAiAnalysis([])
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [sessionId])
  
  const handleClick = async (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const x = Math.floor(((event.clientX - rect.left) / rect.width) * 1080)
    const y = Math.floor(((event.clientY - rect.top) / rect.height) * 1920)
    
    try {
      await fetch(`/api/emulator/${sessionId}/tap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ x, y })
      })
    } catch (error) {
      console.error('Failed to send tap:', error)
    }
  }
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-2 rounded-full hover:bg-gray-100"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            <span className="text-sm font-medium">{gamePhase}</span>
          </div>
          <button
            onClick={() => {/* TODO: Implement fullscreen */}}
            className="p-2 rounded-full hover:bg-gray-100"
          >
            <Maximize2 className="w-5 h-5" />
          </button>
        </div>

        {/* Game Screen - ensure image is always visible */}
        <div 
          className="relative w-full h-[480px] bg-gray-900 rounded-lg overflow-hidden cursor-pointer flex items-center justify-center"
          onClick={handleClick}
        >
          {screenshot ? (
            <img
              src={screenshot}
              alt="Game Screen"
              style={{ maxWidth: '100%', maxHeight: '100%', display: 'block', margin: 'auto', background: 'transparent' }}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-white">
              Loading...
            </div>
          )}
        </div>
        
        {/* AI Actions Table */}
        {aiActions.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-4 mt-4">
            <h4 className="font-semibold mb-2">AI Actions</h4>
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Type</th>
                  <th>Params</th>
                  <th>Confidence</th>
                  <th>Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {aiActions.map((a: any, i: number) => (
                  <tr key={a.id || i}>
                    <td>{i + 1}</td>
                    <td>{a.action_type}</td>
                    <td>{JSON.stringify(a.action_parameters)}</td>
                    <td>{a.confidence_score}</td>
                    <td>{a.reasoning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {/* Telemetry Table */}
        {telemetry.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-4 mt-4">
            <h4 className="font-semibold mb-2">Telemetry</h4>
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Level</th>
                  <th>Score</th>
                  <th>FPS</th>
                </tr>
              </thead>
              <tbody>
                {telemetry.map((t: any, i: number) => (
                  <tr key={i}>
                    <td>{t.timestamp}</td>
                    <td>{t.current_level}</td>
                    <td>{t.score}</td>
                    <td>{t.fps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {/* AI Analysis Table */}
        {aiAnalysis.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-4 mt-4">
            <h4 className="font-semibold mb-2">AI Thoughts & Analysis</h4>
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Confidence</th>
                  <th>API Used</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {aiAnalysis.map((a: any, i: number) => (
                  <tr key={a.id || i}>
                    <td>{a.analysis_type}</td>
                    <td>{a.confidence_score}</td>
                    <td>{a.api_used}</td>
                    <td>{JSON.stringify(a.analysis_data)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <h3 className="text-lg font-semibold">Live Gameplay - {gamePhase}</h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 bg-gray-100 rounded hover:bg-gray-200"
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>
          <button className="p-2 bg-red-100 rounded hover:bg-red-200 text-red-600 font-semibold" onClick={handleStopSession}>
            <span>Stop Session</span>
          </button>
          <button className="p-2 bg-gray-100 rounded hover:bg-gray-200">
            <Maximize2 className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      <div 
        className="bg-black rounded-lg overflow-hidden cursor-pointer"
        onClick={handleClick}
      >
        {screenshot ? (
          <img 
            src={screenshot} 
            alt="Game Screen" 
            className="w-full h-auto"
            style={{ maxHeight: '600px', objectFit: 'contain' }}
          />
        ) : (
          <div className="aspect-video flex items-center justify-center">
            <p className="text-white">Loading game stream...</p>
          </div>
        )}
      </div>
      <div className="mt-4 text-sm text-gray-600">
        <p>Session ID: {sessionId}</p>
        <p>Click on the screen to interact with the game</p>
      </div>
    </div>
  );
}