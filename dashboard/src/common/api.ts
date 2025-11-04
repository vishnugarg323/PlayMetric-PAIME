import axios from 'axios'

// Use runtime config if available, fallback to import.meta.env
const API_BASE_URL = (window as any).ENV?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Game {
  id: string
  display_name: string
  package_name: string
  genre: string
  current_version_id?: string
  total_sessions: number
  total_bugs: number
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export interface GameVersion {
  id: string
  game_id: string
  version_name: string
  version_code: number
  apk_path: string
  apk_size: number
  apk_hash: string
  min_sdk: number
  target_sdk: number
  upload_date: string
  uploaded_by?: string
  metadata?: Record<string, any>
}

export interface Session {
  id: string
  game_version_id: string
  session_name?: string
  agent_mode: 'random' | 'advanced_rl' | 'manual' | 'heuristic'
  status: 'queued' | 'running' | 'completed' | 'failed' | 'stopped' | 'pending'
  started_at?: string
  completed_at?: string
  duration_seconds?: number
  target_duration_minutes?: number
  total_actions: number
  total_screenshots: number
  crashes_detected: number
  config?: Record<string, any>
  error_message?: string
  created_at: string
}

export interface Bug {
  id: string
  game_id: string
  version_id: string
  session_id?: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  type: string
  title: string
  description: string
  stack_trace?: string
  screenshot_path?: string
  status: 'open' | 'in_progress' | 'resolved' | 'wont_fix' | 'duplicate'
  first_seen: string
  last_seen: string
  occurrence_count: number
  assigned_to?: string
  resolved_at?: string
  resolution_notes?: string
}

export interface SessionMetrics {
  timestamp: string
  fps: number
  memory_mb: number
  cpu_percent: number
  battery_level?: number
  network_rx_bytes?: number
  network_tx_bytes?: number
}

export interface RLStatistics {
  steps: number
  episodes: number
  epsilon: number
  memory_size: number
  memory_capacity: number
  average_loss_100?: number
  average_reward_100?: number
  training_enabled: boolean
}

// API functions
export const gamesApi = {
  list: () => api.get<Game[]>('/games'),
  get: (id: string) => api.get<Game>(`/games/${id}`),
  create: (data: Partial<Game>) => api.post<Game>('/games', data),
  update: (id: string, data: Partial<Game>) => api.put<Game>(`/games/${id}`, data),
  delete: (id: string) => api.delete(`/games/${id}`),
  versions: (id: string) => api.get<GameVersion[]>(`/games/${id}/versions`),
  uploadAPK: (gameId: string, file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('game_id', gameId)
    return api.post<GameVersion>(`/games/${gameId}/versions/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100
          onProgress(progress)
        }
      },
    })
  },
  uploadVersion: (gameId: string, version: string, file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('apk', file)
    return api.post<GameVersion>(`/games/${gameId}/versions?version=${encodeURIComponent(version)}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100
          onProgress(progress)
        }
      },
    })
  },
}

export interface AIThinking {
  id?: number
  action_type: string
  action?: string  // Legacy field for compatibility
  type?: string  // Type of decision (rl_decision, rule_based_decision)
  reasoning: string
  q_values?: number[]
  epsilon?: number
  position?: { x?: number; y?: number }
  ui_context?: string
  timestamp: string
  exploration?: boolean  // Whether action was exploration
}

export const sessionsApi = {
  list: (params?: { game_id?: string; status?: string }) => 
    api.get<Session[]>('/sessions', { params }),
  get: (id: string) => api.get<Session>(`/sessions/${id}`),
  create: (data: { game_id: string; version_id: string; agent_mode: string; config?: any }) => 
    api.post<{ session_id: string; status: string; message: string }>('/sessions', data),
  start: (id: string) => api.post(`/sessions/${id}/start`),
  stop: (id: string) => api.post(`/sessions/${id}/stop`),
  delete: (id: string) => api.delete(`/sessions/${id}`),
  metrics: (id: string, params?: { start?: string; end?: string }) => 
    api.get<SessionMetrics[]>(`/sessions/${id}/metrics`, { params }),
  bugs: (id: string) => api.get<Bug[]>(`/sessions/${id}/bugs`),
  screenshots: (id: string) => api.get<string[]>(`/sessions/${id}/screenshots`),
  aiThinking: (id: string, limit: number = 100) => api.get<AIThinking[]>(`/sessions/${id}/ai-thinking`, { params: { limit } }),
}

export const bugsApi = {
  list: (params?: { game_id?: string; version_id?: string; severity?: string; status?: string }) => 
    api.get<Bug[]>('/bugs', { params }),
  get: (id: string) => api.get<Bug>(`/bugs/${id}`),
  update: (id: string, data: Partial<Bug>) => api.put<Bug>(`/bugs/${id}`, data),
  delete: (id: string) => api.delete(`/bugs/${id}`),
}

export const analyticsApi = {
  gameStatistics: (gameId: string) => api.get(`/analytics/games/${gameId}/statistics`),
  versionComparison: (versionId1: string, versionId2: string) => 
    api.get(`/analytics/versions/compare`, { params: { v1: versionId1, v2: versionId2 } }),
  difficultyAnalysis: (gameId: string) => api.get(`/analytics/games/${gameId}/difficulty`),
  retentionAnalysis: (gameId: string) => api.get(`/analytics/games/${gameId}/retention`),
}

export const agentApi = {
  statistics: () => api.get<RLStatistics>('/agent/statistics'),
  memoryStats: () => api.get('/agent/memory/stats'),
  configure: (data: { enable_training?: boolean; training_interval?: number }) => 
    api.post('/agent/training/configure', data),
  saveModel: (version?: string) => api.post('/agent/model/save', { version }),
}
