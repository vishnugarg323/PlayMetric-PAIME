import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bug, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import Button from '../components/Button'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'

interface BugReport {
  id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  status: 'open' | 'in-progress' | 'resolved' | 'closed'
  game_id: string
  game_name: string
  session_id?: string
  created_at: string
  updated_at: string
}

export default function BugTracker() {
  const queryClient = useQueryClient()
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterSeverity, setFilterSeverity] = useState<string>('all')

  const { data: bugs, isLoading } = useQuery<BugReport[]>({
    queryKey: ['bugs', filterStatus, filterSeverity],
    queryFn: async () => {
      // Mock data - replace with actual API call
      const allBugs: BugReport[] = [
        {
          id: '1',
          title: 'App crashes on startup',
          description: 'The application crashes immediately after launch on Android 13',
          severity: 'critical' as const,
          status: 'open' as const,
          game_id: 'game-1',
          game_name: 'Test Game',
          session_id: 'session-123',
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '2',
          title: 'Login button unresponsive',
          description: 'Login button does not respond to tap events occasionally',
          severity: 'high' as const,
          status: 'in-progress' as const,
          game_id: 'game-1',
          game_name: 'Test Game',
          created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '3',
          title: 'UI rendering issue',
          description: 'Some UI elements overlap on smaller screens',
          severity: 'medium' as const,
          status: 'resolved' as const,
          game_id: 'game-2',
          game_name: 'Another Game',
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
        },
      ]
      return allBugs.filter(bug => 
        (filterStatus === 'all' || bug.status === filterStatus) &&
        (filterSeverity === 'all' || bug.severity === filterSeverity)
      )
    },
    refetchInterval: 10000,
  })

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      // Mock API call - replace with actual endpoint
      await new Promise(resolve => setTimeout(resolve, 500))
      return { id, status }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bugs'] })
    },
  })

  if (isLoading) return <Loading text="Loading bugs..." />

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-600 text-white'
      case 'high': return 'bg-orange-600 text-white'
      case 'medium': return 'bg-yellow-600 text-white'
      case 'low': return 'bg-blue-600 text-white'
      default: return 'bg-slate-600 text-white'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open': return <AlertCircle className="w-4 h-4" />
      case 'in-progress': return <Bug className="w-4 h-4" />
      case 'resolved': return <CheckCircle className="w-4 h-4" />
      case 'closed': return <XCircle className="w-4 h-4" />
      default: return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'text-red-500'
      case 'in-progress': return 'text-yellow-500'
      case 'resolved': return 'text-green-500'
      case 'closed': return 'text-slate-500'
      default: return 'text-slate-400'
    }
  }

  const openBugs = bugs?.filter(b => b.status === 'open') || []
  const inProgressBugs = bugs?.filter(b => b.status === 'in-progress') || []
  const resolvedBugs = bugs?.filter(b => b.status === 'resolved') || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Bug Tracker</h1>
          <p className="text-slate-400">Track and manage bugs detected during testing</p>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
          >
            <option value="all">All Status</option>
            <option value="open">Open</option>
            <option value="in-progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Total Bugs</p>
          <p className="text-3xl font-bold text-white">{bugs?.length || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Open</p>
          <p className="text-3xl font-bold text-red-500">{openBugs.length}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">In Progress</p>
          <p className="text-3xl font-bold text-yellow-500">{inProgressBugs.length}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Resolved</p>
          <p className="text-3xl font-bold text-green-500">{resolvedBugs.length}</p>
        </div>
      </div>

      {bugs?.length === 0 ? (
        <EmptyState
          title="No bugs found"
          description="Great! No bugs have been detected yet"
          icon={<Bug className="w-16 h-16" />}
        />
      ) : (
        <div className="space-y-4">
          {bugs?.map(bug => (
            <div key={bug.id} className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-primary-500 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-white">{bug.title}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(bug.severity)}`}>
                      {bug.severity}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 mb-2">{bug.description}</p>
                  <p className="text-xs text-slate-500">
                    {bug.game_name} • Created {new Date(bug.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`flex items-center gap-2 ${getStatusColor(bug.status)}`}>
                    {getStatusIcon(bug.status)}
                    <span className="text-sm capitalize">{bug.status.replace('-', ' ')}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {bug.status === 'open' && (
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => updateStatusMutation.mutate({ id: bug.id, status: 'in-progress' })}
                  >
                    Start Working
                  </Button>
                )}
                {bug.status === 'in-progress' && (
                  <Button 
                    size="sm"
                    onClick={() => updateStatusMutation.mutate({ id: bug.id, status: 'resolved' })}
                  >
                    Mark Resolved
                  </Button>
                )}
                {bug.session_id && (
                  <Button size="sm" variant="secondary">
                    View Session
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
