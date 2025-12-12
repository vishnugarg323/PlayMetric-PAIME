import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { gamesApi, sessionsApi } from '../common/api'
import { ArrowLeft, Smartphone, Monitor, RefreshCw, CheckCircle2 } from 'lucide-react'
import Button from '../components/Button'
import Loading from '../components/Loading'

// Type definitions
interface Game {
  id: string
  display_name: string
  package_name: string
  genre: string
  total_sessions?: number
}

interface GameVersion {
  id: string
  version_name: string
  version_code: number
  apk_size: number
  min_sdk?: number
  target_sdk?: number
  metadata?: any
}

interface CreateSessionData {
  game_id: string
  version_id: string
  agent_mode: string
  session_type: string  // 'learning' or 'playing'
  config: {
    max_duration_seconds: number
    max_actions: number
    enable_screenshots: boolean
    screenshot_interval: number
    device_mode: string
    device_ip: string
    learning_mode: string
    session_type: string  // Also in config for backward compatibility
    video_id?: string  // For learning sessions
  }
}

interface SessionResponse {
  data: {
    session_id: string
    status: string
    message: string
  }
}

export default function CreateSession() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preSelectedGameId = searchParams.get('gameId')

  const [selectedGameId, setSelectedGameId] = useState<string>(preSelectedGameId || '')
  const [selectedVersionId, setSelectedVersionId] = useState<string>('')
  const [selectedVideoId, setSelectedVideoId] = useState<string>('')
  const [sessionType, setSessionType] = useState<'learning' | 'playing'>('learning')
  const [maxDuration, setMaxDuration] = useState<number>(300)
  const [maxActions, setMaxActions] = useState<number>(1000)
  
  // Local state for device and mode selection (not from global store)
  const [deviceMode, setDeviceMode] = useState<'physical' | 'emulator'>('emulator')
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [availableDevices, setAvailableDevices] = useState<any[]>([])
  const [availableVideos, setAvailableVideos] = useState<any[]>([])
  const [loadingDevices, setLoadingDevices] = useState(false)
  const [loadingVideos, setLoadingVideos] = useState(false)

  const { data: games, isLoading: gamesLoading } = useQuery<Game[]>({
    queryKey: ['games'],
    queryFn: () => gamesApi.list().then((r: any) => r.data),
  })

  const { data: versions, isLoading: versionsLoading } = useQuery<GameVersion[]>({
    queryKey: ['game-versions', selectedGameId],
    queryFn: () => gamesApi.versions(selectedGameId).then((r: any) => r.data),
    enabled: !!selectedGameId,
  })

  // Auto-select the first version when versions load
  useEffect(() => {
    if (versions && versions.length > 0 && !selectedVersionId) {
      setSelectedVersionId(versions[0].id)
    }
  }, [versions])

  // Fetch available devices when device mode changes
  useEffect(() => {
    fetchAvailableDevices()
  }, [deviceMode])

  // Fetch available videos when game changes (for learning mode)
  useEffect(() => {
    if (selectedGameId && sessionType === 'learning') {
      fetchAvailableVideos()
    }
  }, [selectedGameId, sessionType])

  const fetchAvailableVideos = async () => {
    if (!selectedGameId) return
    
    setLoadingVideos(true)
    try {
      const API_BASE = (window as any).CONFIG?.API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE}/games/${selectedGameId}/videos`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch videos: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      setAvailableVideos(data.videos || [])
      
      // Auto-select first video if available
      if (data.videos && data.videos.length > 0 && !selectedVideoId) {
        setSelectedVideoId(data.videos[0].id)
      }
    } catch (error) {
      console.error('Failed to fetch videos:', error)
      setAvailableVideos([])
    } finally {
      setLoadingVideos(false)
    }
  }

  const fetchAvailableDevices = async () => {
    setLoadingDevices(true)
    try {
      const API_BASE = (window as any).CONFIG?.API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE}/devices/available`)
      const data = await response.json()
      
      // Filter devices based on selected mode
      const filtered = data.devices.filter((d: any) => d.device_mode === deviceMode)
      setAvailableDevices(filtered)
      
      // Auto-select first device if available
      if (filtered.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(filtered[0].device_id)
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error)
      setAvailableDevices([])
    } finally {
      setLoadingDevices(false)
    }
  }

  const createMutation = useMutation<SessionResponse, Error, CreateSessionData>({
    mutationFn: (data: CreateSessionData) =>
      sessionsApi.create(data) as Promise<SessionResponse>,
    onSuccess: (response: SessionResponse) => {
      // Navigate to unified session details page
      // SessionDetailsNew will detect mode and show appropriate UI
      const sessionId = response.data.session_id
      navigate(`/sessions/${sessionId}`)
    },
    onError: (error: any) => {
      alert(`Failed to create session: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleCreate = () => {
    if (!selectedGameId || !selectedVersionId) {
      alert('Please select a game and version')
      return
    }

    if (sessionType === 'learning' && !selectedVideoId) {
      alert('Please select a training video for learning session')
      return
    }

    const config: any = {
      max_duration_seconds: maxDuration,
      max_actions: maxActions,
      enable_screenshots: true,
      screenshot_interval: 0.5,
      session_type: sessionType, // 'learning' or 'playing'
    }

    // Add video ID for learning sessions
    if (sessionType === 'learning' && selectedVideoId) {
      config.video_id = selectedVideoId
    }

    // Only add device info if session type is 'playing'
    if (sessionType === 'playing') {
      config.device_mode = deviceMode
      
      if (selectedDeviceId) {
        if (deviceMode === 'physical') {
          const deviceIp = selectedDeviceId.split(':')[0]
          config.device_ip = deviceIp
        } else {
          config.emulator_name = selectedDeviceId
        }
      }
    }

    createMutation.mutate({
      game_id: selectedGameId,
      version_id: selectedVersionId,
      agent_mode: 'advanced_rl', // Always use RL mode
      session_type: sessionType,  // Send at top level for backend
      config,
    })
  }

  if (gamesLoading) return <Loading text="Loading games..." />

  const selectedGame = games?.find((g: Game) => g.id === selectedGameId)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/sessions')}>
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Create New Session</h1>
          <p className="text-slate-400">Configure and start a new AI testing session</p>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 space-y-6">
        {/* Game Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Select Game
          </label>
          <select
            value={selectedGameId}
            onChange={(e: any) => {
              setSelectedGameId(e.target.value)
              setSelectedVersionId('') // Reset version when game changes
            }}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">-- Choose a game --</option>
            {games?.map((game: Game) => (
              <option key={game.id} value={game.id}>
                {game.display_name} ({game.package_name})
              </option>
            ))}
          </select>
          {selectedGame && (
            <p className="mt-2 text-sm text-slate-400">
              Genre: {selectedGame.genre} • Sessions: {selectedGame.total_sessions || 0}
            </p>
          )}
        </div>

        {/* Version Selection */}
        {selectedGameId && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Select Version
            </label>
            {versionsLoading ? (
              <div className="text-slate-400">Loading versions...</div>
            ) : versions && versions.length > 0 ? (
              <>
                <select
                  value={selectedVersionId}
                  onChange={(e: any) => setSelectedVersionId(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {versions.map((version: GameVersion) => (
                    <option key={version.id} value={version.id}>
                      {version.version_name} (Code: {version.version_code}) - {(version.apk_size / 1024 / 1024).toFixed(2)} MB
                    </option>
                  ))}
                </select>
                {selectedVersionId && (
                  <p className="mt-2 text-sm text-slate-400">
                    {versions.find((v: GameVersion) => v.id === selectedVersionId)?.metadata && (
                      <>SDK: {versions.find((v: GameVersion) => v.id === selectedVersionId)?.min_sdk} - {versions.find((v: GameVersion) => v.id === selectedVersionId)?.target_sdk}</>
                    )}
                  </p>
                )}
              </>
            ) : (
              <div className="text-slate-400 p-4 bg-slate-700 rounded-lg border border-slate-600">
                No versions available. Please upload an APK first.
              </div>
            )}
          </div>
        )}

        {/* Session Type Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Session Type
          </label>
          <div className="space-y-3">
            <label className="flex items-start p-4 bg-slate-700 rounded-lg border-2 border-slate-600 cursor-pointer hover:border-primary-500 transition-colors">
              <input
                type="radio"
                name="session_type"
                value="learning"
                checked={sessionType === 'learning'}
                onChange={(e: any) => setSessionType(e.target.value)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="text-white font-semibold">AI Learning from Video</div>
                <div className="text-sm text-slate-400">
                  Process uploaded training video offline. No device needed. AI builds knowledge base.
                </div>
              </div>
            </label>
            <label className="flex items-start p-4 bg-slate-700 rounded-lg border-2 border-slate-600 cursor-pointer hover:border-primary-500 transition-colors">
              <input
                type="radio"
                name="session_type"
                value="playing"
                checked={sessionType === 'playing'}
                onChange={(e: any) => setSessionType(e.target.value)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="text-white font-semibold">AI Playing Game</div>
                <div className="text-sm text-slate-400">
                  AI plays the game using learned knowledge + built-in intelligence (RL, OCR, Vision, LLM).
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Video Selection - Only show for 'learning' session type */}
        {sessionType === 'learning' && selectedGameId && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Select Training Video
            </label>
            {loadingVideos ? (
              <div className="text-slate-400 p-4 bg-slate-700 rounded-lg">Loading videos...</div>
            ) : availableVideos.length === 0 ? (
              <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4">
                <p className="text-sm text-yellow-300">
                  ⚠️ No training videos found for this game
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Upload a training video first from the Games page
                </p>
              </div>
            ) : (
              <select
                value={selectedVideoId}
                onChange={(e) => setSelectedVideoId(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {availableVideos.map((video: any) => (
                  <option key={video.id} value={video.id}>
                    {video.metadata?.title || `Video ${video.id.slice(0, 8)}`} - {video.duration_seconds ? `${video.duration_seconds.toFixed(0)}s` : 'Duration unknown'} - {video.processing_status}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Session Configuration - Only show for 'playing' session type */}
        {sessionType === 'playing' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Max Duration (seconds)
              </label>
              <input
                type="number"
                value={maxDuration}
                onChange={(e: any) => setMaxDuration(parseInt(e.target.value))}
                min={30}
                max={3600}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-slate-400">
                Session will stop after this duration
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Max Actions
              </label>
              <input
                type="number"
                value={maxActions}
                onChange={(e: any) => setMaxActions(parseInt(e.target.value))}
                min={10}
                max={10000}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-slate-400">
                Session will stop after this many actions
              </p>
            </div>
          </div>
        )}

        {/* Device Mode Selection - Only show for 'playing' session type */}
        {sessionType === 'playing' && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Device Type
            </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label
              className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                deviceMode === 'physical'
                  ? 'bg-blue-900/30 border-blue-500'
                  : 'bg-slate-700 border-slate-600 hover:border-blue-500/50'
              }`}
            >
              <input
                type="radio"
                name="device_mode"
                value="physical"
                checked={deviceMode === 'physical'}
                onChange={(e) => setDeviceMode(e.target.value as 'physical' | 'emulator')}
                className="mt-1 mr-3"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-white font-semibold mb-1">
                  <Smartphone className="w-4 h-4" />
                  Physical Device
                </div>
                <div className="text-sm text-slate-400">
                  Use real Android phone via WiFi ADB
                </div>
              </div>
            </label>

            <label
              className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                deviceMode === 'emulator'
                  ? 'bg-yellow-900/30 border-yellow-500'
                  : 'bg-slate-700 border-slate-600 hover:border-yellow-500/50'
              }`}
            >
              <input
                type="radio"
                name="device_mode"
                value="emulator"
                checked={deviceMode === 'emulator'}
                onChange={(e) => setDeviceMode(e.target.value as 'physical' | 'emulator')}
                className="mt-1 mr-3"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-white font-semibold mb-1">
                  <Monitor className="w-4 h-4" />
                  Android Emulator
                </div>
                <div className="text-sm text-slate-400">
                  Use Android Studio emulator
                </div>
              </div>
            </label>
          </div>

          {/* Available Devices Selection */}
          {(deviceMode === 'physical' || deviceMode === 'emulator') && (
            <div className="mt-3 bg-slate-900/50 border border-slate-600/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-slate-300">
                  {deviceMode === 'physical' ? 'Available Physical Devices' : 'Available Emulators'}
                </label>
                <button
                  onClick={fetchAvailableDevices}
                  disabled={loadingDevices}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingDevices ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              {loadingDevices ? (
                <div className="text-sm text-slate-400 py-2">Detecting devices...</div>
              ) : availableDevices.length === 0 ? (
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded p-3">
                  <p className="text-sm text-yellow-300">
                    ⚠️ No {deviceMode === 'physical' ? 'physical devices' : 'emulators'} detected
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {deviceMode === 'physical' 
                      ? 'Connect a device via WiFi ADB: adb connect <IP>:5555'
                      : 'Start Android Studio emulator on your host machine'}
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {availableDevices.map((device) => (
                    <label
                      key={device.device_id}
                      className={`flex items-center p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedDeviceId === device.device_id
                          ? 'bg-green-900/30 border-green-500'
                          : 'bg-slate-800 border-slate-600 hover:border-green-500/50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="selected_device"
                        value={device.device_id}
                        checked={selectedDeviceId === device.device_id}
                        onChange={(e) => setSelectedDeviceId(e.target.value)}
                        className="mr-3"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          {selectedDeviceId === device.device_id && (
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                          )}
                          <span className="text-white font-medium">
                            {device.model || device.device_id}
                          </span>
                          {device.android_version && (
                            <span className="text-xs text-slate-400">
                              Android {device.android_version}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {device.device_id}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              {availableDevices.length === 0 && !loadingDevices && (
                <div className="mt-3 text-xs text-slate-500">
                  💡 Device will be auto-detected if you continue without selection
                </div>
              )}
            </div>
          )}
        </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-3 pt-4">
          {/* Single Create Session Button */}
          <Button
            onClick={handleCreate}
            disabled={
              !selectedGameId || 
              !selectedVersionId || 
              (sessionType === 'learning' && availableVideos.length === 0) ||
              createMutation.isPending
            }
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            {createMutation.isPending 
              ? 'Creating Session...' 
              : sessionType === 'learning' 
                ? '🎓 Start Learning from Video'
                : '🎮 Start Playing Session'
            }
          </Button>

          {/* Info Box */}
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
            <p className="text-xs text-blue-300">
              {sessionType === 'learning' 
                ? '💡 Learning session will process the uploaded training video offline (no device needed)'
                : '💡 Playing session will use learned knowledge + AI intelligence to play the game on selected device'}
            </p>
          </div>

          {/* Cancel Button */}
          <Button
            variant="ghost"
            onClick={() => navigate('/sessions')}
            className="w-full"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}
