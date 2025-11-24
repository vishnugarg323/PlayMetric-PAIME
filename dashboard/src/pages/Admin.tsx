import { useState, useEffect } from 'react'
import { Trash2, Video, Package, Database } from 'lucide-react'
import Button from '../components/Button'

interface Game {
  id: string
  package_name: string
  display_name: string
  training_video_path: string | null
}

export default function Admin() {
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedGameForAPK, setSelectedGameForAPK] = useState('')
  const [selectedGameForVideo, setSelectedGameForVideo] = useState('')
  const [demoVideo, setDemoVideo] = useState<File | null>(null)
  const [uploadingDemo, setUploadingDemo] = useState(false)

  useEffect(() => {
    fetchGames()
  }, [])

  const fetchGames = async () => {
    try {
      const response = await fetch('/api/games')
      const data = await response.json()
      setGames(data.data || [])
    } catch (error) {
      console.error('Failed to fetch games:', error)
    }
  }

  const handleDeleteGame = async () => {
    if (!selectedGameForAPK) {
      alert('Please select a game to delete')
      return
    }

    const game = games.find(g => g.package_name === selectedGameForAPK)
    if (!game) return

    if (!confirm(
      `⚠️ DELETE ALL DATA FOR "${game.display_name}"?\n\n` +
      `This will permanently remove:\n` +
      `• All APK files\n` +
      `• All versions\n` +
      `• All test sessions\n` +
      `• All screenshots\n` +
      `• All learning data\n` +
      `• Training videos\n\n` +
      `This action CANNOT be undone!`
    )) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/games/package/${selectedGameForAPK}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        alert(`✅ Successfully deleted "${game.display_name}" and all associated data`)
        setSelectedGameForAPK('')
        fetchGames()
      } else {
        const error = await response.json()
        alert(`❌ Delete failed: ${error.detail}`)
      }
    } catch (error: any) {
      alert(`❌ Delete failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteVideo = async () => {
    if (!selectedGameForVideo) {
      alert('Please select a game to delete training video')
      return
    }

    const game = games.find(g => g.package_name === selectedGameForVideo)
    if (!game) return

    if (!game.training_video_path) {
      alert('This game has no training video to delete')
      return
    }

    if (!confirm(
      `Delete training video for "${game.display_name}"?\n\n` +
      `This will remove:\n` +
      `• Training video file\n` +
      `• AI learned knowledge base\n\n` +
      `AI will no longer use learned patterns for this game.`
    )) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/games/package/${selectedGameForVideo}/video`, {
        method: 'DELETE'
      })

      if (response.ok) {
        alert(`✅ Training video deleted for "${game.display_name}"`)
        setSelectedGameForVideo('')
        fetchGames()
      } else {
        const error = await response.json()
        alert(`❌ Delete failed: ${error.detail}`)
      }
    } catch (error: any) {
      alert(`❌ Delete failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadDemoVideo = async () => {
    if (!demoVideo) {
      alert('Please select a demo video file')
      return
    }

    setUploadingDemo(true)
    try {
      const formData = new FormData()
      formData.append('demo_video', demoVideo)

      const response = await fetch('/api/system/demo-video', {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        alert('✅ Demo video uploaded successfully')
        setDemoVideo(null)
      } else {
        const error = await response.json()
        alert(`❌ Upload failed: ${error.detail}`)
      }
    } catch (error: any) {
      alert(`❌ Upload failed: ${error.message}`)
    } finally {
      setUploadingDemo(false)
    }
  }

  const gamesWithVideos = games.filter(g => g.training_video_path)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Admin Panel</h1>
        <p className="text-slate-400">Manage system data and upload demo content</p>
      </div>

      {/* Demo Video Upload */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Video className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">Upload Demo Video</h2>
        </div>
        <p className="text-slate-400 text-sm mb-4">
          Upload a demonstration video that will be displayed on the About page for investors and clients.
        </p>
        <div className="space-y-4">
          <input
            type="file"
            accept="video/*,.mp4,.webm,.mov"
            onChange={(e) => setDemoVideo(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-400
              file:mr-4 file:py-2 file:px-4
              file:rounded-lg file:border-0
              file:text-sm file:font-semibold
              file:bg-purple-600 file:text-white
              hover:file:bg-purple-700
              file:cursor-pointer cursor-pointer
            "
          />
          {demoVideo && (
            <p className="text-sm text-slate-400">
              Selected: {demoVideo.name} ({(demoVideo.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
          <Button
            onClick={handleUploadDemoVideo}
            disabled={!demoVideo || uploadingDemo}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {uploadingDemo ? 'Uploading...' : 'Upload Demo Video'}
          </Button>
        </div>
      </div>

      {/* Data Management */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Delete Game & All Data */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 border-red-900/50 bg-red-900/10">
          <div className="flex items-center gap-3 mb-6">
            <Package className="w-6 h-6 text-red-400" />
            <h2 className="text-xl font-bold text-white">Delete Game & All Data</h2>
          </div>
          <p className="text-slate-400 text-sm mb-4">
            Permanently delete a game including all APKs, versions, sessions, screenshots, and learning data.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Select Game to Delete
              </label>
              <select
                value={selectedGameForAPK}
                onChange={(e) => setSelectedGameForAPK(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">-- Select a game --</option>
                {games.map(game => (
                  <option key={game.id} value={game.package_name}>
                    {game.display_name} ({game.package_name})
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="danger"
              onClick={handleDeleteGame}
              disabled={!selectedGameForAPK || loading}
              className="w-full flex items-center justify-center gap-2"
            >
              <Trash2 className="w-5 h-5" />
              {loading ? 'Deleting...' : 'Delete Game & All Data'}
            </Button>
          </div>
        </div>

        {/* Delete Training Video */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 border-orange-900/50 bg-orange-900/10">
          <div className="flex items-center gap-3 mb-6">
            <Video className="w-6 h-6 text-orange-400" />
            <h2 className="text-xl font-bold text-white">Delete Training Video</h2>
          </div>
          <p className="text-slate-400 text-sm mb-4">
            Delete the training video and AI knowledge base for a game. The game and APK will remain.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Select Game
              </label>
              <select
                value={selectedGameForVideo}
                onChange={(e) => setSelectedGameForVideo(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                <option value="">-- Select a game --</option>
                {gamesWithVideos.length === 0 ? (
                  <option disabled>No games with training videos</option>
                ) : (
                  gamesWithVideos.map(game => (
                    <option key={game.id} value={game.package_name}>
                      {game.display_name} ({game.package_name})
                    </option>
                  ))
                )}
              </select>
            </div>
            <Button
              variant="secondary"
              onClick={handleDeleteVideo}
              disabled={!selectedGameForVideo || loading || gamesWithVideos.length === 0}
              className="w-full flex items-center justify-center gap-2 bg-orange-600 hover:bg-orange-700"
            >
              <Trash2 className="w-5 h-5" />
              {loading ? 'Deleting...' : 'Delete Training Video'}
            </Button>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Database className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-bold text-white">System Information</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-slate-400">Total Games</p>
            <p className="text-2xl font-bold text-white">{games.length}</p>
          </div>
          <div>
            <p className="text-slate-400">With Training Videos</p>
            <p className="text-2xl font-bold text-white">{gamesWithVideos.length}</p>
          </div>
          <div>
            <p className="text-slate-400">Without Videos</p>
            <p className="text-2xl font-bold text-white">{games.length - gamesWithVideos.length}</p>
          </div>
          <div>
            <p className="text-slate-400">Status</p>
            <p className="text-2xl font-bold text-green-400">Active</p>
          </div>
        </div>
      </div>
    </div>
  )
}
