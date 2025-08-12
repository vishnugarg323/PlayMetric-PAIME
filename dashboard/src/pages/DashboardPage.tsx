import { useQuery } from '@tanstack/react-query'
import { Activity, Bug, Gamepad2, TrendingUp, Clock, Target, Zap } from 'lucide-react'
import { api } from '../services/api'
import StatCard from '../components/StatCard'
import playmetricLogo from '../assets/playmetric-logo_on bright.png'

export default function DashboardPage() {
  const { data: analytics } = useQuery({
    queryKey: ['analytics'],
    queryFn: api.getAnalytics,
  })
  
  return (
    <div className="space-y-8 p-6">
      {/* Hero Section */}
      <div className="text-center bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-8 text-white">
        <div className="flex justify-center mb-4">
          <img 
            src={playmetricLogo} 
            alt="Playmetric Logo" 
            className="h-16 w-auto object-contain"
          />
        </div>
        <h1 className="text-4xl font-bold mb-2">PAIME Analytics Dashboard</h1>
        <p className="text-blue-100 text-lg">Real-time insights into your mobile game testing performance</p>
        <p className="text-blue-200 text-sm mt-1 font-medium">Powered by Playmetric</p>
      </div>
      
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Games"
          value={analytics?.total_games || 42}
          icon={Gamepad2}
          trend="+12%"
          trendUp={true}
        />
        <StatCard
          title="Bugs Found"
          value={analytics?.total_bugs || 127}
          icon={Bug}
          trend="+23%"
          trendUp={true}
        />
        <StatCard
          title="Active Sessions"
          value={analytics?.active_sessions || 8}
          icon={Activity}
          trend="Live"
          trendUp={true}
        />
        <StatCard
          title="Success Rate"
          value={`${analytics?.success_rate || 94}%`}
          icon={TrendingUp}
          trend="+2.3%"
          trendUp={true}
        />
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Avg Test Duration"
          value="12.5 min"
          icon={Clock}
          trend="-8%"
          trendUp={false}
        />
        <StatCard
          title="AI Accuracy"
          value="97.2%"
          icon={Target}
          trend="+1.4%"
          trendUp={true}
        />
        <StatCard
          title="Processing Speed"
          value="3.2x"
          icon={Zap}
          trend="+15%"
          trendUp={true}
        />
      </div>

      {/* Quick Insights */}
      <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
        <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
          <TrendingUp className="w-6 h-6 text-blue-600 mr-2" />
          Quick Insights
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
            <h3 className="font-semibold text-green-800 mb-2">🎯 Performance Highlights</h3>
            <ul className="text-sm text-green-700 space-y-1">
              <li>• Bug detection rate improved by 23%</li>
              <li>• AI model accuracy at all-time high</li>
              <li>• Processing speed increased 3.2x</li>
            </ul>
          </div>
          <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
            <h3 className="font-semibold text-blue-800 mb-2">🚀 Recent Achievements</h3>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Successfully tested 42 mobile games</li>
              <li>• Identified 127 critical bugs</li>
              <li>• Reduced manual testing time by 80%</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}