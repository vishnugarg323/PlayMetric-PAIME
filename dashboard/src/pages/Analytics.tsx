import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { gamesApi } from '../lib/api'
import { BarChart3, TrendingUp, Clock, Activity } from 'lucide-react'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'

export default function Analytics() {
  const [selectedGame, setSelectedGame] = useState<string>('all')
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d')

  const { data: games } = useQuery({
    queryKey: ['games'],
    queryFn: () => gamesApi.list().then(r => r.data),
  })

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', selectedGame, timeRange],
    queryFn: async () => {
      // Mock data - replace with actual API call
      return {
        totalSessions: 156,
        avgSessionDuration: 342,
        totalActions: 12456,
        crashRate: 2.3,
        topActions: [
          { action: 'tap', count: 5234 },
          { action: 'swipe', count: 3421 },
          { action: 'scroll', count: 2156 },
          { action: 'type', count: 1645 },
        ],
        dailyStats: Array.from({ length: 7 }, (_, i) => ({
          date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toLocaleDateString(),
          sessions: Math.floor(Math.random() * 30) + 10,
          crashes: Math.floor(Math.random() * 5),
        })),
      }
    },
  })

  if (isLoading) return <Loading text="Loading analytics..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
          <p className="text-slate-400">Track performance and usage metrics</p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedGame}
            onChange={(e) => setSelectedGame(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
          >
            <option value="all">All Games</option>
            {games?.map(game => (
              <option key={game.id} value={game.id}>{game.display_name}</option>
            ))}
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>
      </div>

      {!analytics ? (
        <EmptyState
          title="No analytics data"
          description="Run some test sessions to see analytics"
          icon={<BarChart3 className="w-16 h-16" />}
        />
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-400">Total Sessions</p>
                <Activity className="w-5 h-5 text-primary-500" />
              </div>
              <p className="text-3xl font-bold text-white">{analytics.totalSessions}</p>
              <p className="text-xs text-green-500 mt-1">↑ 12% from last period</p>
            </div>
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-400">Avg Duration</p>
                <Clock className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold text-white">{Math.floor(analytics.avgSessionDuration / 60)}m</p>
              <p className="text-xs text-slate-400 mt-1">{analytics.avgSessionDuration}s total</p>
            </div>
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-400">Total Actions</p>
                <TrendingUp className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-3xl font-bold text-white">{analytics.totalActions.toLocaleString()}</p>
              <p className="text-xs text-green-500 mt-1">↑ 8% from last period</p>
            </div>
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-400">Crash Rate</p>
                <BarChart3 className="w-5 h-5 text-red-500" />
              </div>
              <p className="text-3xl font-bold text-white">{analytics.crashRate}%</p>
              <p className="text-xs text-red-500 mt-1">↓ 1.2% from last period</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Actions */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Top Actions</h3>
              <div className="space-y-3">
                {analytics.topActions.map((action, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-slate-300 capitalize">{action.action}</span>
                    <div className="flex items-center space-x-3">
                      <div className="w-32 bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full"
                          style={{ width: `${(action.count / analytics.topActions[0].count) * 100}%` }}
                        />
                      </div>
                      <span className="text-white font-medium w-16 text-right">{action.count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Daily Activity */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Daily Activity</h3>
              <div className="space-y-2">
                {analytics.dailyStats.map((stat, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{stat.date}</span>
                    <div className="flex items-center space-x-4">
                      <span className="text-white">{stat.sessions} sessions</span>
                      <span className="text-red-500">{stat.crashes} crashes</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
