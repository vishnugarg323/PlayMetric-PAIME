import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { sessionsApi, AIThinking } from '../lib/api'
import { ArrowLeft, Square, Clock, Bug, Activity, Brain, Zap } from 'lucide-react'
import Button from '../components/Button'
import Loading from '../components/Loading'
import { formatRelativeTime } from '../lib/utils'
import { useEffect, useState, useRef } from 'react'
import { io } from 'socket.io-client'

export default function SessionDetails() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [aiThoughts, setAiThoughts] = useState<AIThinking[]>([])
  const thoughtsEndRef = useRef<HTMLDivElement>(null)
  const [aiActive, setAiActive] = useState(false)
  const [screenshotUrl, setScreenshotUrl] = useState('')
  const [screenshotInfo, setScreenshotInfo] = useState<any>(null)
  const [latestAiAnalysis, setLatestAiAnalysis] = useState<any>(null)

  const { data: session, isLoading, error, isError } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 5000,
    refetchOnMount: 'always',
    staleTime: 0,
  })

  // Fetch AI thinking history on mount
  useEffect(() => {
    if (!sessionId) return
    
    sessionsApi.aiThinking(sessionId, 100)
      .then(r => {
        if (r.data && r.data.length > 0) {
          setAiThoughts(r.data)
        }
      })
      .catch(err => console.error('Failed to load AI thinking history:', err))
  }, [sessionId])

  // Poll AI status and update screenshot
  useEffect(() => {
    // Show screenshot for running sessions
    if (!sessionId || session?.status !== 'running') return

    // Poll AI status every 2 seconds
    const statusInterval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8004/play/status')
        const data = await response.json()
        setAiActive(data.ai_active || false)
      } catch (error) {
        console.error('Failed to fetch AI status:', error)
      }
    }, 2000)

    // Update screenshot every 2 seconds (slower to match AI pace)
    const screenshotInterval = setInterval(() => {
      // Use AI's current screenshot endpoint
      setScreenshotUrl(`http://localhost:8004/play/current-screenshot-image?t=${Date.now()}`)
      
      // Also get screenshot info
      fetch('http://localhost:8004/play/latest-screenshot')
        .then(r => r.json())
        .then(data => setScreenshotInfo(data))
        .catch(err => console.error('Failed to fetch screenshot info:', err))
    }, 2000)

    return () => {
      clearInterval(statusInterval)
      clearInterval(screenshotInterval)
    }
  }, [sessionId, session?.status])

  // Activate AI handler
  const handleActivateAI = async () => {
    try {
      const response = await fetch('http://localhost:8004/play/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      setAiActive(data.ai_active)
    } catch (error) {
      console.error('Failed to activate AI:', error)
    }
  }

  // Pause AI handler
  const handlePauseAI = async () => {
    try {
      const response = await fetch('http://localhost:8004/play/pause', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      setAiActive(data.ai_active)
    } catch (error) {
      console.error('Failed to pause AI:', error)
    }
  }

  // WebSocket connection for AI thinking
  useEffect(() => {
    if (!sessionId) return

    const socketInstance = io('http://localhost:8000', {
      transports: ['websocket'],
      reconnection: true,
    })

    socketInstance.on('connect', () => {
      console.log('Connected to WebSocket for AI thinking')
      socketInstance.emit('subscribe_session', { session_id: sessionId })
    })

    socketInstance.on(`session_${sessionId}`, (payload: any) => {
      if (payload.type === 'ai_thinking' && payload.data) {
        // Store latest AI analysis data (OCR, UI elements, etc.)
        setLatestAiAnalysis({
          ocr_detected: payload.data.ocr_detected || false,
          ui_elements_detected: payload.data.ui_elements_detected || 0,
          screen_changed: payload.data.screen_changed || false,
          stuck: payload.data.stuck || false,
          action: payload.data.action,
          reasoning: payload.data.reasoning
        })
        
        // Convert real-time data to match AIThinking interface
        const thinking: AIThinking = {
          action_type: payload.data.action || 'unknown',
          action: payload.data.action || 'unknown',
          type: payload.data.type || 'rule_based_decision',
          reasoning: payload.data.reasoning || '',
          q_values: payload.data.q_values,
          epsilon: payload.data.epsilon,
          position: payload.data.position,
          timestamp: payload.data.timestamp || new Date().toISOString(),
          exploration: payload.data.exploration || false
        }
        // Add new thoughts at the beginning (latest first) - no auto-scroll
        setAiThoughts(prev => [thinking, ...prev.slice(0, 49)]) // Keep last 50, newest first
      }
    })

    socketInstance.on('disconnect', () => {
      console.log('Disconnected from WebSocket')
    })

    return () => {
      socketInstance.disconnect()
    }
  }, [sessionId])

  if (isLoading) return <Loading text="Loading session..." />
  if (isError) return <div className="text-white">Error loading session: {error?.message || 'Unknown error'}</div>
  if (!session) return <div className="text-white">Session not found</div>

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-500 bg-green-500/10'
      case 'completed': return 'text-blue-500 bg-blue-500/10'
      case 'failed': return 'text-red-500 bg-red-500/10'
      case 'stopped': return 'text-yellow-500 bg-yellow-500/10'
      default: return 'text-slate-500 bg-slate-500/10'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="secondary" size="sm" onClick={() => navigate('/sessions')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              Session {session.id.substring(0, 8)}
            </h1>
            <p className="text-slate-400">{session.agent_mode} mode</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`px-3 py-1 rounded-lg text-sm font-medium ${getStatusColor(session.status)}`}>
            {session.status}
          </span>
          {session.status === 'running' && (
            <>
              {/* AI Control Button */}
              <Button
                variant={aiActive ? "secondary" : "primary"}
                size="sm"
                onClick={aiActive ? handlePauseAI : handleActivateAI}
                className={aiActive ? "bg-orange-600 hover:bg-orange-700" : ""}
              >
                {aiActive ? (
                  <>⏸️ Pause AI</>
                ) : (
                  <>▶️ Start AI</>
                )}
              </Button>
              <Button variant="danger" size="sm">
                <Square className="w-4 h-4 mr-2" />
                Stop Session
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-slate-400">Total Actions</p>
            <Activity className="w-5 h-5 text-primary-500" />
          </div>
          <p className="text-3xl font-bold text-white">{session.total_actions || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-slate-400">Screenshots</p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-white">{session.total_screenshots || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-slate-400">Crashes</p>
            <Bug className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-3xl font-bold text-red-500">{session.crashes_detected || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-slate-400">Duration</p>
            <Clock className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-white">
            {session.duration_seconds 
              ? `${Math.floor(session.duration_seconds / 60)}m ${session.duration_seconds % 60}s`
              : '-'}
          </p>
        </div>
      </div>

      {/* Live Screenshot Preview */}
      {session.status === 'running' && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
            📸 Current Screen (What AI Sees)
          </h2>
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Screenshot Image */}
            <div className="flex-shrink-0">
              {screenshotUrl ? (
                <div className="relative">
                  <img 
                    src={screenshotUrl}
                    alt="Current Screen"
                    className="w-full lg:w-72 rounded-lg border-2 border-slate-600 shadow-lg"
                    onError={() => setScreenshotUrl('')}
                  />
                  <div className="absolute top-2 right-2 bg-black/70 px-2 py-1 rounded text-xs text-white">
                    {aiActive ? '🤖 AI Active' : '⏸️ Waiting'}
                  </div>
                </div>
              ) : (
                <div className="w-full lg:w-72 h-96 bg-slate-900 rounded-lg border-2 border-slate-600 flex items-center justify-center">
                  <div className="text-center text-slate-500">
                    <Activity className="w-12 h-12 mx-auto mb-2 opacity-50 animate-pulse" />
                    <p>Waiting for screenshot...</p>
                  </div>
                </div>
              )}
            </div>

            {/* AI Analysis Info */}
            <div className="flex-1 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-300 mb-2">🧠 What AI Detected from Image</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-900 rounded-lg p-3">
                    <p className="text-xs text-slate-400">OCR Text Found</p>
                    <p className={`text-lg font-bold ${latestAiAnalysis?.ocr_detected ? 'text-green-400' : 'text-slate-500'}`}>
                      {latestAiAnalysis?.ocr_detected ? '✓ Yes' : '○ None'}
                    </p>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <p className="text-xs text-slate-400">UI Elements</p>
                    <p className="text-lg font-bold text-white">
                      {latestAiAnalysis?.ui_elements_detected || 0}
                    </p>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <p className="text-xs text-slate-400">Screen Changed</p>
                    <p className={`text-lg font-bold ${latestAiAnalysis?.screen_changed ? 'text-green-400' : 'text-orange-400'}`}>
                      {latestAiAnalysis?.screen_changed ? '✓ Yes' : '○ Static'}
                    </p>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <p className="text-xs text-slate-400">AI Status</p>
                    <p className={`text-lg font-bold ${latestAiAnalysis?.stuck ? 'text-red-400' : 'text-green-400'}`}>
                      {latestAiAnalysis?.stuck ? '⚠ Stuck' : '✓ Active'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-900 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">📊 Capture Stats</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Screenshots:</span>
                    <span className="text-white font-bold">{screenshotInfo?.screenshot_count || 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Status:</span>
                    <span className={`font-bold ${screenshotInfo?.capturing ? 'text-green-400' : 'text-red-400'}`}>
                      {screenshotInfo?.capturing ? '● Capturing' : '○ Stopped'}
                    </span>
                  </div>
                </div>
              </div>

              {latestAiAnalysis?.reasoning && (
                <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3">
                  <p className="text-xs text-blue-300">
                    💡 <strong>AI Analysis:</strong> {latestAiAnalysis.reasoning}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action Breakdown */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
          <Activity className="w-5 h-5 mr-2 text-primary-500" />
          Action Breakdown
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {/* Calculate action counts from AI thoughts */}
          {(() => {
            const actionCounts = aiThoughts.reduce((acc, thought) => {
              const action = (thought.action || thought.action_type || 'unknown').toLowerCase().replace(/\s+/g, '_');
              acc[action] = (acc[action] || 0) + 1;
              return acc;
            }, {} as Record<string, number>);

            const actionTypes = [
              { key: 'tap', label: 'Taps', icon: '👆', color: 'text-green-400' },
              { key: 'swipe_up', label: 'Swipe Up', icon: '⬆️', color: 'text-blue-400' },
              { key: 'swipe_down', label: 'Swipe Down', icon: '⬇️', color: 'text-blue-400' },
              { key: 'swipe_left', label: 'Swipe Left', icon: '⬅️', color: 'text-blue-400' },
              { key: 'swipe_right', label: 'Swipe Right', icon: '➡️', color: 'text-blue-400' },
              { key: 'back', label: 'Back', icon: '◀️', color: 'text-yellow-400' },
              { key: 'wait', label: 'Wait', icon: '⏸️', color: 'text-slate-400' }
            ];

            return actionTypes.map(({ key, label, icon, color }) => (
              <div key={key} className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">{icon}</span>
                  <p className={`text-2xl font-bold ${color}`}>
                    {actionCounts[key] || 0}
                  </p>
                </div>
                <p className="text-xs text-slate-400">{label}</p>
              </div>
            ));
          })()}
        </div>
        
        {/* Total Swipes Counter */}
        <div className="mt-4 p-4 bg-slate-900 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Total Swipes:</span>
            <span className="text-2xl font-bold text-blue-400">
              {aiThoughts.filter(t => (t.action || t.action_type || '').toLowerCase().includes('swipe')).length}
            </span>
          </div>
        </div>
      </div>

      {/* Session Info */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Session Information</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-400 mb-1">Game ID</p>
            <p className="text-white font-medium">{session.game_version_id}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Version ID</p>
            <p className="text-white font-medium">{session.game_version_id}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Agent Mode</p>
            <p className="text-white font-medium capitalize">{session.agent_mode.replace('_', ' ')}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Created</p>
            <p className="text-white font-medium">{formatRelativeTime(session.created_at)}</p>
          </div>
          {session.started_at && (
            <div>
              <p className="text-sm text-slate-400 mb-1">Started</p>
              <p className="text-white font-medium">{formatRelativeTime(session.started_at)}</p>
            </div>
          )}
          {session.completed_at && (
            <div>
              <p className="text-sm text-slate-400 mb-1">Completed</p>
              <p className="text-white font-medium">{formatRelativeTime(session.completed_at)}</p>
            </div>
          )}
          <div>
            <p className="text-sm text-slate-400 mb-1">Status</p>
            <p className="text-white font-medium capitalize">{session.status}</p>
          </div>
        </div>
      </div>

      {/* Configuration */}
      {session.config && Object.keys(session.config).length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Configuration</h2>
          <pre className="bg-slate-900 rounded p-4 text-sm text-slate-300 overflow-x-auto">
            {JSON.stringify(session.config, null, 2)}
          </pre>
        </div>
      )}

      {/* Error Message */}
      {session.error_message && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-red-400 mb-4">Error</h2>
          <pre className="bg-slate-900 rounded p-4 text-sm text-red-300 overflow-x-auto">
            {session.error_message}
          </pre>
        </div>
      )}

      {/* AI Thinking Logs */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
          <Brain className="w-5 h-5 mr-2 text-purple-500" />
          AI Thinking ({aiThoughts.length})
        </h2>
        <div className="bg-slate-900 rounded-lg overflow-y-auto" style={{ height: '500px' }}>
          {aiThoughts.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-500">
              <div className="text-center">
                <Zap className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Waiting for AI decisions...</p>
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {aiThoughts.map((thought, idx) => (
                <div key={idx} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                  <div className="flex items-start justify-between mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      thought.type === 'rl_decision' 
                        ? 'bg-purple-500/20 text-purple-300'
                        : 'bg-blue-500/20 text-blue-300'
                    }`}>
                      {thought.type === 'rl_decision' ? '🧠 RL Agent' : '📋 Rule-Based'}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(thought.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <div className="space-y-1">
                    <p className="text-white font-medium">
                      Action: <span className="text-primary-400">{thought.action || thought.action_type}</span>
                    </p>
                    
                    {thought.position && (
                      <p className="text-sm text-slate-400">
                        Position: ({thought.position.x || 'N/A'}, {thought.position.y || 'N/A'})
                      </p>
                    )}
                    
                    {thought.reasoning && (
                      <p className="text-sm text-slate-300 mt-2">{thought.reasoning}</p>
                    )}
                    
                    {thought.epsilon !== undefined && (
                      <p className="text-xs text-slate-500 mt-2">
                        Exploration rate: {(thought.epsilon * 100).toFixed(1)}%
                        {thought.exploration && <span className="text-yellow-500 ml-2">🎲 Exploring</span>}
                      </p>
                    )}
                    
                    {thought.q_values && thought.q_values.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-slate-500 mb-1">Q-Values:</p>
                        <div className="flex gap-1">
                          {thought.q_values.slice(0, 8).map((val, i) => (
                            <div
                              key={i}
                              className="h-6 bg-primary-500/20 rounded px-1 text-xs text-primary-300"
                              style={{ width: `${Math.abs(val) * 20 + 20}px` }}
                              title={`Action ${i}: ${val.toFixed(2)}`}
                            >
                              {val > 0 ? '+' : ''}{val.toFixed(1)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={thoughtsEndRef} />
            </div>
          )}
        </div>
        <p className="text-slate-400 text-sm mt-2">
          Real-time AI reasoning and decision-making process
        </p>
      </div>
    </div>
  )
}
