import { NavLink } from 'react-router-dom'
import { useAppStore } from '../store'
import {
  LayoutDashboard,
  Gamepad2,
  Play,
  BarChart3,
  Bug,
  Settings,
  ChevronLeft,
} from 'lucide-react'

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore()

  const links = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/games', icon: Gamepad2, label: 'Games' },
    { to: '/sessions', icon: Play, label: 'Sessions' },
    { to: '/analytics', icon: BarChart3, label: 'Analytics' },
    { to: '/bugs', icon: Bug, label: 'Bug Tracker' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-800 border-r border-slate-700 transform transition-transform duration-300 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-64'
      }`}
    >
      <div className="flex items-center justify-between h-16 px-6 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white">PlayMetric V2</h1>
        <button
          onClick={toggleSidebar}
          className="p-1 rounded hover:bg-slate-700 transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-slate-400" />
        </button>
      </div>

      <nav className="p-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-300 hover:bg-slate-700 hover:text-white'
              }`
            }
          >
            <link.icon className="w-5 h-5" />
            <span className="font-medium">{link.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700">
        <div className="text-xs text-slate-400 text-center">
          v2.0.0 | Advanced RL System
        </div>
      </div>
    </aside>
  )
}
