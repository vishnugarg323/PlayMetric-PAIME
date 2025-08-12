import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Gamepad2, Bug, Activity, BarChart3, Smartphone } from 'lucide-react'
import playmetricLogo from '../assets/playmetric-logo_on bright.png'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Games', href: '/games', icon: Gamepad2 },
    { name: 'Live Emulator', href: '/emulator', icon: Smartphone },
    { name: 'Sessions', href: '/sessions', icon: Activity },
    { name: 'Bugs', href: '/bugs', icon: Bug },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="flex">
        <div className="w-64 bg-white shadow-xl border-r border-slate-200">
          <div className="p-6 border-b border-slate-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <img 
                  src={playmetricLogo} 
                  alt="Playmetric Logo" 
                  className="w-8 h-8 object-contain"
                />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  PAIME
                </h1>
                <p className="text-xs text-slate-500 font-medium">by Playmetric</p>
              </div>
            </div>
          </div>
          <nav className="mt-6 px-3">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-4 py-3 mb-1 text-sm font-semibold rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
        <div className="flex-1">
          <main className="p-8">{children}</main>
        </div>
      </div>
    </div>
  )
}