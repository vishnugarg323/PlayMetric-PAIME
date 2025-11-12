import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type DeviceMode = 'emulator' | 'physical'
export type LearningMode = 'auto_play' | 'user_guided'

interface AppStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  
  selectedGameId: string | null
  setSelectedGameId: (id: string | null) => void
  
  selectedSessionId: string | null
  setSelectedSessionId: (id: string | null) => void
  
  // Device Configuration
  deviceMode: DeviceMode
  setDeviceMode: (mode: DeviceMode) => void
  deviceIp: string
  setDeviceIp: (ip: string) => void
  
  // Learning Configuration
  learningMode: LearningMode
  setLearningMode: (mode: LearningMode) => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      selectedGameId: null,
      setSelectedGameId: (id) => set({ selectedGameId: id }),
      
      selectedSessionId: null,
      setSelectedSessionId: (id) => set({ selectedSessionId: id }),
      
      // Device Configuration - defaults from .env
      deviceMode: 'physical', // Default to physical device
      setDeviceMode: (mode) => set({ deviceMode: mode }),
      deviceIp: '192.168.0.80', // Default device IP
      setDeviceIp: (ip) => set({ deviceIp: ip }),
      
      // Learning Configuration
      learningMode: 'auto_play', // Default to AI auto-play
      setLearningMode: (mode) => set({ learningMode: mode }),
    }),
    {
      name: 'playmetric-settings', // LocalStorage key
      partialize: (state) => ({
        deviceMode: state.deviceMode,
        deviceIp: state.deviceIp,
        learningMode: state.learningMode,
      }),
    }
  )
)
