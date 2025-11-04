import { useAppStore } from '../store'
import { Menu, Bell, User } from 'lucide-react'

export default function Header() {
  const { sidebarOpen, toggleSidebar } = useAppStore()

  return (
    <header className={`h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
      <div className="flex items-center space-x-4">
        {!sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="p-2 rounded hover:bg-slate-700 transition-colors"
          >
            <Menu className="w-5 h-5 text-slate-300" />
          </button>
        )}
        <h2 className="text-lg font-semibold text-white">
          AI-Powered Game Testing Platform
        </h2>
      </div>

      <div className="flex items-center space-x-4">
        <button className="relative p-2 rounded hover:bg-slate-700 transition-colors">
          <Bell className="w-5 h-5 text-slate-300" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <button className="p-2 rounded hover:bg-slate-700 transition-colors">
          <User className="w-5 h-5 text-slate-300" />
        </button>
      </div>
    </header>
  )
}
