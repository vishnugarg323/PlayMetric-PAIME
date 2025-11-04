import { useQuery } from '@tanstack/react-query'
import { gamesApi, sessionsApi, bugsApi, agentApi } from '../common/api'
import { StatCard } from '../components/Card'
import { Gamepad2, Play, Bug, Brain, AlertTriangle } from 'lucide-react'
import Loading from '../components/Loading'

export default function Dashboard() {
  const { data: games, isLoading: gamesLoading } = useQuery({
    queryKey: ['games'],
    queryFn: () => gamesApi.list().then(r => r.data),
  })

  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list().then(r => r.data),
  })

  const { data: bugs, isLoading: bugsLoading } = useQuery({
    queryKey: ['bugs'],
    queryFn: () => bugsApi.list().then(r => r.data),
  })

  const { data: rlStats } = useQuery({
    queryKey: ['agent-stats'],
    queryFn: () => agentApi.statistics().then(r => r.data),
    refetchInterval: 5000,
  })

  if (gamesLoading || sessionsLoading || bugsLoading) {
    return <Loading text="Loading dashboard..." />
  }

  const activeGames = games?.length || 0
  const runningSessions = sessions?.filter(s => s.status === 'running').length || 0
  const openBugs = bugs?.filter(b => b.status === 'open').length || 0
  const criticalBugs = bugs?.filter(b => b.severity === 'critical' && b.status === 'open').length || 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Overview of your AI-powered game testing platform</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Games"
          value={activeGames}
          icon={<Gamepad2 className="w-6 h-6 text-primary-500" />}
        />
        <StatCard
          title="Running Sessions"
          value={runningSessions}
          icon={<Play className="w-6 h-6 text-primary-500" />}
        />
        <StatCard
          title="Open Bugs"
          value={openBugs}
          icon={<Bug className="w-6 h-6 text-primary-500" />}
        />
        <StatCard
          title="Critical Bugs"
          value={criticalBugs}
          icon={<AlertTriangle className="w-6 h-6 text-red-500" />}
        />
      </div>

      {/* RL Agent Status */}
      {rlStats && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white flex items-center">
              <Brain className="w-5 h-5 mr-2 text-primary-500" />
              RL Agent Status
            </h2>
            <span className={`px-3 py-1 rounded-full text-sm ${rlStats.training_enabled ? 'bg-green-600 text-white' : 'bg-gray-600 text-white'}`}>
              {rlStats.training_enabled ? 'Training Active' : 'Training Paused'}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-slate-400">Total Steps</p>
              <p className="text-2xl font-bold text-white">{rlStats?.steps?.toLocaleString() || 0}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Episodes</p>
              <p className="text-2xl font-bold text-white">{rlStats?.episodes || 0}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Exploration Rate</p>
              <p className="text-2xl font-bold text-white">{((rlStats?.epsilon || 0) * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Memory</p>
              <p className="text-2xl font-bold text-white">
                {rlStats?.memory_size || 0} / {rlStats?.memory_capacity || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Sessions</h2>
          <div className="space-y-3">
            {sessions?.slice(0, 5).map(session => (
              <div key={session.id} className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
                <div>
                  <p className="text-white font-medium">Session {session.id.substring(0, 8)}</p>
                  <p className="text-sm text-slate-400">{session.agent_mode}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${
                  session.status === 'running' ? 'bg-green-600 text-white' :
                  session.status === 'completed' ? 'bg-blue-600 text-white' :
                  'bg-gray-600 text-white'
                }`}>
                  {session.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Bugs</h2>
          <div className="space-y-3">
            {bugs?.slice(0, 5).map(bug => (
              <div key={bug.id} className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
                <div>
                  <p className="text-white font-medium">{bug.title}</p>
                  <p className="text-sm text-slate-400">{bug.type}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${
                  bug.severity === 'critical' ? 'bg-red-600 text-white' :
                  bug.severity === 'high' ? 'bg-orange-600 text-white' :
                  bug.severity === 'medium' ? 'bg-yellow-600 text-white' :
                  'bg-blue-600 text-white'
                }`}>
                  {bug.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
