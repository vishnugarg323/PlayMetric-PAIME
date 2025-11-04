import { create } from 'zustand'

interface AppStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  
  selectedGameId: string | null
  setSelectedGameId: (id: string | null) => void
  
  selectedSessionId: string | null
  setSelectedSessionId: (id: string | null) => void
}

export const useAppStore = create<AppStore>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  
  selectedGameId: null,
  setSelectedGameId: (id) => set({ selectedGameId: id }),
  
  selectedSessionId: null,
  setSelectedSessionId: (id) => set({ selectedSessionId: id }),
}))
