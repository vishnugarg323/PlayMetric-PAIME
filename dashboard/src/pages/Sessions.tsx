import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsApi } from '../lib/api'
import { Play, Square, Trash2, Eye, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'
import { formatRelativeTime } from '../lib/utils'

export default function Sessions() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list().then(r => r.data),
    refetchInterval: 5000,
  })

  const stopMutation = useMutation({
    mutationFn: (id: string) => sessionsApi.stop(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => sessionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  if (isLoading) return <Loading text="Loading sessions..." />

  const runningSessions = sessions?.filter(s => s.status === 'running') || []
  const completedSessions = sessions?.filter(s => s.status === 'completed') || []
  const failedSessions = sessions?.filter(s => s.status === 'failed') || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Test Sessions</h1>
          <p className="text-slate-400">Monitor and manage your testing sessions</p>
        </div>
        <Button onClick={() => navigate('/sessions/create')}>
          <Play className="w-5 h-5 mr-2" />
          New Session
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Total Sessions</p>
          <p className="text-3xl font-bold text-white">{sessions?.length || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Running</p>
          <p className="text-3xl font-bold text-green-500">{runningSessions.length}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Completed</p>
          <p className="text-3xl font-bold text-blue-500">{completedSessions.length}</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <p className="text-sm text-slate-400 mb-1">Failed</p>
          <p className="text-3xl font-bold text-red-500">{failedSessions.length}</p>
        </div>
      </div>

      {sessions?.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          description="Click 'New Session' above to start your first testing session"
          icon={<Clock className="w-16 h-16" />}
        />
      ) : (
        <div className="space-y-4">
          {sessions?.map(session => (
            <div key={session.id} className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-primary-500 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-white">
                      Session {session.id.substring(0, 8)}
                    </h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      session.status === 'running' ? 'bg-green-600 text-white' :
                      session.status === 'completed' ? 'bg-blue-600 text-white' :
                      session.status === 'failed' ? 'bg-red-600 text-white' :
                      'bg-slate-600 text-white'
                    }`}>
                      {session.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">{session.agent_mode} mode</p>
                </div>
                <div className="flex items-center space-x-2">
                  {session.status === 'running' && (
                    <Button 
                      variant="danger" 
                      size="sm"
                      onClick={() => stopMutation.mutate(session.id)}
                    >
                      <Square className="w-4 h-4 mr-1" />
                      Stop
                    </Button>
                  )}
                  <Button 
                    variant="secondary" 
                    size="sm"
                    onClick={() => navigate(`/sessions/${session.id}`)}
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    View
                  </Button>
                  <Button 
                    variant="danger" 
                    size="sm"
                    onClick={() => confirm('Delete this session?') && deleteMutation.mutate(session.id)}
                    disabled={session.status === 'running'}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                <div>
                  <p className="text-slate-400">Actions</p>
                  <p className="text-white font-medium">{session.total_actions || 0}</p>
                </div>
                <div>
                  <p className="text-slate-400">Screenshots</p>
                  <p className="text-white font-medium">{session.total_screenshots || 0}</p>
                </div>
                <div>
                  <p className="text-slate-400">Crashes</p>
                  <p className="text-white font-medium text-red-500">{session.crashes_detected || 0}</p>
                </div>
                <div>
                  <p className="text-slate-400">Duration</p>
                  <p className="text-white font-medium">
                    {session.duration_seconds 
                      ? `${Math.floor(session.duration_seconds / 60)}m ${session.duration_seconds % 60}s`
                      : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-slate-400">Created</p>
                  <p className="text-white font-medium">{formatRelativeTime(session.created_at)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
