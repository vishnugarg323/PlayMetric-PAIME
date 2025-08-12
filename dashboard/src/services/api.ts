import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  getGames: async () => {
    const { data } = await apiClient.get('/api/games')
    return data
  },
  
  getGame: async (gameId: string) => {
    const { data } = await apiClient.get(`/api/games/${gameId}`)
    return data
  },
  
  getGameBugs: async (gameId: string) => {
    const { data } = await apiClient.get(`/api/games/${gameId}/bugs`)
    return data
  },
  
  getGameSessions: async (gameId: string) => {
    const { data } = await apiClient.get(`/api/games/${gameId}/sessions`)
    return data
  },
  
  getSessions: async () => {
    const { data } = await apiClient.get('/api/sessions')
    return data
  },
  
  getSessionDetails: async (sessionId: string) => {
    const { data } = await apiClient.get(`/api/sessions/${sessionId}`)
    return data
  },
  
  getBugs: async () => {
    const { data } = await apiClient.get('/api/bugs')
    return data
  },
  
  getAnalytics: async () => {
    const { data } = await apiClient.get('/api/analytics/overview')
    return data
  },
  
  getAnalyticsOverview: async () => {
    const { data } = await apiClient.get('/api/analytics/overview')
    return data
  },
  
  uploadAPK: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const { data } = await apiClient.post('/api/upload-apk', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  getGameAnalysis: async (gameId: string) => {
    const { data } = await apiClient.get(`/api/games/${gameId}/analysis`)
    return data
  },

  startGameTesting: async (gameId: string) => {
    const { data } = await apiClient.post(`/api/games/${gameId}/start-testing`)
    return data
  },

  stopGameTesting: async (gameId: string) => {
    const { data } = await apiClient.post(`/api/games/${gameId}/stop-testing`)
    return data
  },

  createGameSession: async (gameId: string) => {
    const { data } = await apiClient.post(`/api/games/${gameId}/sessions`)
    return data
  },
}