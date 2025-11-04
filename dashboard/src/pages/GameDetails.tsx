import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { gamesApi } from '../lib/api'
import { Upload, Plus } from 'lucide-react'
import Button from '../components/Button'
import Loading from '../components/Loading'
import APKUploader from '../components/APKUploader'
import { formatBytes, formatRelativeTime } from '../lib/utils'

export default function GameDetails() {
  const { gameId } = useParams()
  const [showUploadModal, setShowUploadModal] = useState(false)

  const { data: game, isLoading: gameLoading } = useQuery({
    queryKey: ['games', gameId],
    queryFn: () => gamesApi.get(gameId!).then(r => r.data),
    enabled: !!gameId,
  })

  const { data: versions, isLoading: versionsLoading } = useQuery({
    queryKey: ['game-versions', gameId],
    queryFn: () => gamesApi.versions(gameId!).then(r => r.data),
    enabled: !!gameId,
  })

  if (gameLoading || versionsLoading) return <Loading text="Loading game details..." />
  if (!game) return <div className="text-white">Game not found</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{game.display_name}</h1>
          <p className="text-slate-400">{game.package_name}</p>
        </div>
        <Button onClick={() => setShowUploadModal(true)}>
          <Upload className="w-5 h-5 mr-2" />
          Upload APK
        </Button>
      </div>

      {/* Game Info */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Game Information</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-slate-400">Genre</p>
            <p className="text-lg font-semibold text-white">{game.genre}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Total Sessions</p>
            <p className="text-lg font-semibold text-white">{game.total_sessions || 0}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Total Bugs</p>
            <p className="text-lg font-semibold text-white">{game.total_bugs || 0}</p>
          </div>
        </div>
      </div>

      {/* Versions */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Versions</h2>
          <Button size="sm" onClick={() => setShowUploadModal(true)}>
            <Plus className="w-4 h-4 mr-1" />
            Add Version
          </Button>
        </div>
        <div className="space-y-3">
          {versions?.map(version => (
            <div key={version.id} className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
              <div>
                <p className="text-white font-semibold">{version.version_name} (Code: {version.version_code})</p>
                <p className="text-sm text-slate-400">
                  Uploaded {formatRelativeTime(version.upload_date)} • {formatBytes(version.apk_size)}
                </p>
                <p className="text-sm text-slate-400">
                  SDK: {version.min_sdk} - {version.target_sdk}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 font-mono">{version.apk_hash.substring(0, 12)}...</p>
              </div>
            </div>
          ))}
          {(!versions || versions.length === 0) && (
            <p className="text-slate-400 text-center py-8">No versions uploaded yet</p>
          )}
        </div>
      </div>

      {/* APK Upload Modal */}
      {showUploadModal && (
        <APKUploader
          gameId={gameId!}
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => setShowUploadModal(false)}
        />
      )}
    </div>
  )
}
