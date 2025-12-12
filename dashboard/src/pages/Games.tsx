import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { gamesApi } from '../common/api'
import { Plus, Upload, Trash2, Eye, Video } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'
import { formatRelativeTime } from '../common/utils'

export default function Games() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showVideoModal, setShowVideoModal] = useState(false)
  const [selectedGameForVideo, setSelectedGameForVideo] = useState<string>('')
  const [genre, setGenre] = useState('')
  const [apkFile, setApkFile] = useState<File | null>(null)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadingVideo, setUploadingVideo] = useState(false)

  const { data: games, isLoading } = useQuery({
    queryKey: ['games'],
    queryFn: () => gamesApi.list().then(r => r.data),
  })

  const handleUpload = async () => {
    if (!apkFile || !genre) {
      alert('Please select an APK file and choose a genre')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('apk', apkFile)
      formData.append('genre', genre)
      
      // Add optional training video
      if (videoFile) {
        formData.append('training_video', videoFile)
      }

      const response = await fetch('/api/games/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      queryClient.invalidateQueries({ queryKey: ['games'] })
      setShowCreateModal(false)
      setGenre('')
      setApkFile(null)
      setVideoFile(null)
    } catch (error: any) {
      alert(`Upload failed: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  const deleteMutation = useMutation({
    mutationFn: (id: string) => gamesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['games'] })
    },
  })

  const handleUploadVideo = async () => {
    if (!selectedGameForVideo || !videoFile) {
      alert('Please select a game and video file')
      return
    }

    setUploadingVideo(true)
    try {
      // Use /api/ prefix to go through nginx proxy
      const formData = new FormData()
      formData.append('video', videoFile)

      const response = await fetch(`/api/games/${selectedGameForVideo}/videos/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      alert('✅ Training video uploaded successfully!')
      setShowVideoModal(false)
      setSelectedGameForVideo('')
      setVideoFile(null)
      queryClient.invalidateQueries({ queryKey: ['games'] })
    } catch (error: any) {
      alert(`❌ Upload failed: ${error.message}`)
    } finally {
      setUploadingVideo(false)
    }
  }

  if (isLoading) return <Loading text="Loading games..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Games</h1>
          <p className="text-slate-400">Manage your game library</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowVideoModal(true)} variant="secondary">
            <Video className="w-5 h-5 mr-2" />
            Upload Video
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-5 h-5 mr-2" />
            Add Game
          </Button>
        </div>
      </div>

      {games?.length === 0 ? (
        <EmptyState
          title="No games yet"
          description="Click 'Add Game' button above to add your first game and start testing"
          icon={<Upload className="w-16 h-16" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {games?.map(game => (
            <div key={game.id} className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-primary-500 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">{game.display_name}</h3>
                  <p className="text-sm text-slate-400">{game.package_name}</p>
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Genre</span>
                  <span className="text-white">{game.genre}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Sessions</span>
                  <span className="text-white">{game.total_sessions || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Bugs</span>
                  <span className="text-white">{game.total_bugs || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Updated</span>
                  <span className="text-white">{formatRelativeTime(game.updated_at)}</span>
                </div>
              </div>

              <div className="flex space-x-2">
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="flex-1"
                  onClick={() => navigate(`/games/${game.id}`)}
                >
                  <Eye className="w-4 h-4 mr-1" />
                  View
                </Button>
                <Button 
                  variant="danger" 
                  size="sm"
                  onClick={() => confirm('Delete this game?') && deleteMutation.mutate(game.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Game Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-md w-full">
            <h2 className="text-2xl font-bold text-white mb-4">Upload Game APK</h2>
            <p className="text-slate-400 text-sm mb-6">
              Upload your APK file and the game name, package, and version will be automatically extracted
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Genre *
                </label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select genre...</option>
                  <option value="puzzle">Puzzle</option>
                  <option value="action">Action</option>
                  <option value="adventure">Adventure</option>
                  <option value="arcade">Arcade</option>
                  <option value="strategy">Strategy</option>
                  <option value="simulation">Simulation</option>
                  <option value="racing">Racing</option>
                  <option value="sports">Sports</option>
                  <option value="casual">Casual</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  APK File *
                </label>
                <input
                  type="file"
                  accept=".apk"
                  onChange={(e) => setApkFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-400
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-semibold
                    file:bg-primary-600 file:text-white
                    hover:file:bg-primary-700
                    file:cursor-pointer cursor-pointer
                  "
                />
                {apkFile && (
                  <p className="mt-2 text-sm text-slate-400">
                    Selected: {apkFile.name} ({(apkFile.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Training Video (Optional)
                </label>
                <input
                  type="file"
                  accept="video/*,.mp4,.avi,.mov,.mkv"
                  onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-400
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-600 file:text-white
                    hover:file:bg-blue-700
                    file:cursor-pointer cursor-pointer
                  "
                />
                {videoFile && (
                  <p className="mt-2 text-sm text-slate-400">
                    Selected: {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
                <p className="mt-1 text-xs text-slate-500">
                  Upload gameplay video for AI to learn from (applies to all versions of this game)
                </p>
              </div>
              <div className="flex space-x-3 mt-6">
                <Button 
                  variant="ghost" 
                  onClick={() => {
                    setShowCreateModal(false)
                    setGenre('')
                    setApkFile(null)
                    setVideoFile(null)
                  }}
                  className="flex-1"
                  disabled={uploading}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleUpload}
                  disabled={!genre || !apkFile || uploading}
                  className="flex-1"
                >
                  {uploading ? 'Uploading...' : 'Upload Game'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Video for Existing Game Modal */}
      {showVideoModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-md w-full">
            <h2 className="text-2xl font-bold text-white mb-4">Upload Training Video</h2>
            <p className="text-slate-400 text-sm mb-6">
              Upload gameplay video for an existing game. AI will learn strategies from this video.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Select Game *
                </label>
                <select
                  value={selectedGameForVideo}
                  onChange={(e) => setSelectedGameForVideo(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Choose game...</option>
                  {games?.map(game => (
                    <option key={game.id} value={game.id}>
                      {game.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Training Video *
                </label>
                <input
                  type="file"
                  accept="video/*,.mp4,.avi,.mov,.mkv"
                  onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-400
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-600 file:text-white
                    hover:file:bg-blue-700
                    file:cursor-pointer cursor-pointer
                  "
                />
                {videoFile && (
                  <p className="mt-2 text-sm text-slate-400">
                    Selected: {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
              </div>
              <div className="flex space-x-3 mt-6">
                <Button 
                  variant="ghost" 
                  onClick={() => {
                    setShowVideoModal(false)
                    setSelectedGameForVideo('')
                    setVideoFile(null)
                  }}
                  className="flex-1"
                  disabled={uploadingVideo}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleUploadVideo}
                  disabled={!selectedGameForVideo || !videoFile || uploadingVideo}
                  className="flex-1"
                >
                  {uploadingVideo ? 'Uploading...' : 'Upload Video'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
