import { useState } from 'react'
import { Eye, Activity, Camera, Clock, Bug, Zap } from 'lucide-react'
import GamePlayer from '../components/GamePlayer'
import TelemetryChart from '../components/TelemetryChart'
import BugTimeline from '../components/BugTimeline'
import AIThoughts from '../components/AIThoughts'

export default function SessionDetailPage() {
  // Static demo session details for all games
  const sessionDetailsMap: Record<string, any> = {
    'demo-session-1': {
      session_id: 'demo-session-1',
      game_name: 'Screw Unscrew',
      status: 'active',
      start_time: new Date().toISOString(),
      end_time: null,
      max_level_reached: 2,
      max_score: 245,
      ai_thoughts: [
        'I am trying to click OK to start the level.',
        'I clicked and the screw got over.',
        'Level cleared! AI detected a UI glitch: screw count flickers.',
        'Bug categorized as UI glitch, impacts score display.'
      ],
      bugs: [
        {
          bug_id: '1',
          bug_type: 'UI glitch',
          severity: 'critical',
          description: 'Screw count display flickers when moving to level 2.',
          timestamp: new Date().toISOString()
        },
        {
          bug_id: '2',
          bug_type: 'Logic bug',
          severity: 'high',
          description: 'Screw does not register in the box on first attempt in level 2.',
          timestamp: new Date().toISOString()
        }
      ],
      telemetry: [
        { timestamp: new Date().toISOString(), fps: 60, cpu_usage: 30, memory_usage: 120 }
      ]
    },
    'demo-session-2': {
      session_id: 'demo-session-2',
      game_name: 'Factory Jam',
      status: 'completed',
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
      max_level_reached: 5,
      max_score: 980,
      ai_thoughts: [
        'Sorting bottles as they arrive on the conveyor.',
        'AI noticed a sorting error when speed increased.',
        'Bug categorized as critical: bottle sorting fails.',
        'UI froze after sorting 10 bottles.'
      ],
      bugs: [
        {
          bug_id: '3',
          bug_type: 'Sorting error',
          severity: 'critical',
          description: 'Bottle sorting fails when conveyor speed increases.',
          timestamp: new Date().toISOString()
        },
        {
          bug_id: '4',
          bug_type: 'UI freeze',
          severity: 'medium',
          description: 'UI freezes when sorting more than 10 bottles.',
          timestamp: new Date().toISOString()
        }
      ],
      telemetry: [
        { timestamp: new Date().toISOString(), fps: 55, cpu_usage: 40, memory_usage: 150 }
      ]
    },
    'demo-session-3': {
      session_id: 'demo-session-3',
      game_name: 'Blocky Knits',
      status: 'active',
      start_time: new Date().toISOString(),
      end_time: null,
      max_level_reached: 3,
      max_score: 410,
      ai_thoughts: [
        'Arranging yarn blocks for the puzzle.',
        'AI detected puzzle logic issue in hard level.',
        'Level stuck after completing level 3.',
        'Bug categorized as low severity.'
      ],
      bugs: [
        {
          bug_id: '5',
          bug_type: 'Puzzle logic',
          severity: 'high',
          description: 'Yarn blocks do not align correctly in hard levels.',
          timestamp: new Date().toISOString()
        },
        {
          bug_id: '6',
          bug_type: 'Level stuck',
          severity: 'low',
          description: 'Player gets stuck after completing level 3.',
          timestamp: new Date().toISOString()
        }
      ],
      telemetry: [
        { timestamp: new Date().toISOString(), fps: 62, cpu_usage: 25, memory_usage: 100 }
      ]
    },
    'demo-session-4': {
      session_id: 'demo-session-4',
      game_name: 'Make Them 100!',
      status: 'completed',
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
      max_level_reached: 4,
      max_score: 600,
      ai_thoughts: [
        'Dragging bubble pieces to form groups.',
        'AI detected bubble count error after popping.',
        'Pop animation bug observed when popping multiple bubbles.',
        'Bug categorized as medium severity.'
      ],
      bugs: [
        {
          bug_id: '7',
          bug_type: 'Bubble count error',
          severity: 'medium',
          description: 'Bubble count does not reset after popping.',
          timestamp: new Date().toISOString()
        },
        {
          bug_id: '8',
          bug_type: 'Pop animation bug',
          severity: 'low',
          description: 'Pop animation lags when popping multiple bubbles.',
          timestamp: new Date().toISOString()
        }
      ],
      telemetry: [
        { timestamp: new Date().toISOString(), fps: 58, cpu_usage: 35, memory_usage: 110 }
      ]
    }
  };

  // Get sessionId from route or props
  const sessionId = window.location.pathname.split('/').pop();
  const sessionDetail = sessionDetailsMap[sessionId || 'demo-session-1'];
  const [activeTab, setActiveTab] = useState<'overview' | 'live' | 'screenshots'>('overview');
  const isActive = sessionDetail.status === 'active'

  // Mock liveSession and refetchLive for demo purposes
  const [liveSession, setLiveSession] = useState<{
    current_screenshot?: string;
    latest_telemetry?: {
      fps?: number;
      current_level?: number;
      score?: number;
    };
  } | null>(null);

  function refetchLive() {
    // Simulate fetching live session data
    setLiveSession({
      current_screenshot: '', // put base64 string here if available
      latest_telemetry: {
        fps: 60,
        current_level: 2,
        score: 245
      }
    });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Session Details</h1>
          <p className="text-gray-600 mt-1">{sessionDetail.game_name} - {sessionDetail.session_id}</p>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            isActive ? 'bg-green-100 text-green-800' :
            sessionDetail.status === 'completed' ? 'bg-blue-100 text-blue-800' :
            'bg-red-100 text-red-800'
          }`}>
            {sessionDetail.status.toUpperCase()}
          </span>
          {isActive && (
            <div className="flex items-center text-green-600">
              <Activity className="w-4 h-4 mr-1 animate-pulse" />
              <span className="text-sm">Live</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Session Info Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center">
            <Clock className="w-5 h-5 text-gray-400 mr-2" />
            <div>
              <div className="text-sm text-gray-600">Duration</div>
              <div className="font-semibold">
                {sessionDetail.end_time 
                  ? Math.round((new Date(sessionDetail.end_time).getTime() - new Date(sessionDetail.start_time).getTime()) / 60000) + 'm'
                  : 'Ongoing'
                }
              </div>
            </div>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center">
            <Zap className="w-5 h-5 text-yellow-500 mr-2" />
            <div>
              <div className="text-sm text-gray-600">Max Level</div>
              <div className="font-semibold">{sessionDetail.max_level_reached}</div>
            </div>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center">
            <Bug className="w-5 h-5 text-red-500 mr-2" />
            <div>
              <div className="text-sm text-gray-600">Bugs Found</div>
              <div className="font-semibold">{sessionDetail.bugs?.length || 0}</div>
            </div>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center">
            <Activity className="w-5 h-5 text-blue-500 mr-2" />
            <div>
              <div className="text-sm text-gray-600">Score</div>
              <div className="font-semibold">{sessionDetail.max_score || 0}</div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Eye className="w-4 h-4 mr-2" />
              Overview
            </button>
            {isActive && (
              <button
                onClick={() => setActiveTab('live')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center ${
                  activeTab === 'live'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Activity className="w-4 h-4 mr-2" />
                Live View
                <span className="ml-1 w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              </button>
            )}
            <button
              onClick={() => setActiveTab('screenshots')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center ${
                activeTab === 'screenshots'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Camera className="w-4 h-4 mr-2" />
              Screenshots ({sessionDetail?.screenshots?.length || 0})
            </button>
          </nav>
        </div>
        
        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold mb-3">Game Player</h3>
                  <div className="aspect-video bg-gray-200 rounded flex items-center justify-center">
                    <GamePlayer sessionId={sessionId!} />
                  </div>
                </div>
                <TelemetryChart data={sessionDetail.telemetry || []} />
              </div>
              
              <div className="space-y-6">
                <AIThoughts sessionId={sessionId!} />
                <BugTimeline bugs={sessionDetail.bugs || []} />
              </div>
            </div>
          )}
          
          {/* Live Tab */}
          {activeTab === 'live' && isActive && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Live Session Monitoring</h3>
                <button
                  onClick={() => refetchLive()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
                >
                  <Activity className="w-4 h-4 mr-2" />
                  Refresh
                </button>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Live Screenshot */}
                <div className="bg-white rounded-lg border">
                  <div className="p-4 border-b">
                    <h4 className="font-medium">Current Screen</h4>
                  </div>
                  <div className="p-4">
                    <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
                      {liveSession?.current_screenshot ? (
                        <img
                          src={`data:image/png;base64,${liveSession.current_screenshot}`}
                          alt="Live screenshot"
                          className="max-w-full max-h-full object-contain rounded"
                        />
                      ) : (
                        <div className="text-center text-gray-500">
                          <Camera className="w-12 h-12 mx-auto mb-2 opacity-50" />
                          <p>No live screenshot available</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Live Stats */}
                <div className="space-y-4">
                  <div className="bg-white rounded-lg border p-4">
                    <h4 className="font-medium mb-3">Current Performance</h4>
                    {liveSession?.latest_telemetry ? (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-600">FPS:</span>
                          <span className="font-medium">{liveSession.latest_telemetry.fps || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Level:</span>
                          <span className="font-medium">{liveSession.latest_telemetry.current_level || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Score:</span>
                          <span className="font-medium">{liveSession.latest_telemetry.score || 'N/A'}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-500">No telemetry data available</p>
                    )}
                  </div>
                  
                  <div className="bg-white rounded-lg border p-4">
                    <h4 className="font-medium mb-3">Session Status</h4>
                    <div className="space-y-2">
                      <div className="flex items-center">
                        <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                        <span className="text-sm">AI Agent Active</span>
                      </div>
                      <div className="flex items-center">
                        <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                        <span className="text-sm">Game Running</span>
                      </div>
                      <div className="text-sm text-gray-600 mt-2">
                        Last updated: {new Date().toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Screenshots Tab */}
          {activeTab === 'screenshots' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Session Screenshots</h3>
              {sessionDetail?.screenshots?.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {sessionDetail.screenshots.map((screenshot: any, index: number) => (
                    <div key={index} className="bg-white rounded-lg border overflow-hidden">
                      <div className="aspect-video bg-gray-100">
                        <img
                          src={screenshot.url || screenshot.data}
                          alt={`Screenshot ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-2">
                        <p className="text-xs text-gray-600">
                          {screenshot.timestamp ? new Date(screenshot.timestamp).toLocaleTimeString() : `Image ${index + 1}`}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Camera className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No screenshots available for this session</p>
                  <p className="text-sm mt-2">Screenshots will appear here during testing</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}