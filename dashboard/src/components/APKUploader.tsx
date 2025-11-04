import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { gamesApi } from '../common/api'
import { Upload, X, CheckCircle, AlertCircle } from 'lucide-react'
import Button from './Button'
import { formatBytes } from '../common/utils'

interface APKUploaderProps {
  gameId: string
  onClose: () => void
  onSuccess: () => void
}

export default function APKUploader({ gameId, onClose, onSuccess }: APKUploaderProps) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [error, setError] = useState<string>('')

  const uploadMutation = useMutation({
    mutationFn: (file: File) => 
      gamesApi.uploadAPK(gameId, file, (progress) => setUploadProgress(progress)),
    onSuccess: () => {
      setStatus('success')
      queryClient.invalidateQueries({ queryKey: ['game-versions', gameId] })
      setTimeout(() => {
        onSuccess()
      }, 1500)
    },
    onError: (err: any) => {
      setStatus('error')
      setError(err.response?.data?.message || 'Upload failed')
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const apkFile = acceptedFiles[0]
    if (apkFile && apkFile.name.endsWith('.apk')) {
      setFile(apkFile)
      setStatus('idle')
      setError('')
    } else {
      setError('Please upload a valid APK file')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/vnd.android.package-archive': ['.apk'] },
    maxFiles: 1,
  })

  const handleUpload = () => {
    if (file) {
      setStatus('uploading')
      uploadMutation.mutate(file)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-lg w-full">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-white">Upload APK</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>

        {!file ? (
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary-500 bg-primary-500/10'
                : 'border-slate-600 hover:border-slate-500'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />
            <p className="text-white mb-2">
              {isDragActive ? 'Drop the APK file here' : 'Drag & drop an APK file here'}
            </p>
            <p className="text-sm text-slate-400">or click to select file</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-white font-medium">{file.name}</p>
                {status === 'idle' && (
                  <button onClick={() => setFile(null)} className="text-slate-400 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>
              <p className="text-sm text-slate-400">{formatBytes(file.size)}</p>

              {status === 'uploading' && (
                <div className="mt-4">
                  <div className="w-full bg-slate-600 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-slate-400 mt-2">
                    Uploading... {uploadProgress.toFixed(0)}%
                  </p>
                </div>
              )}

              {status === 'success' && (
                <div className="flex items-center mt-4 text-green-500">
                  <CheckCircle className="w-5 h-5 mr-2" />
                  <p>Upload successful!</p>
                </div>
              )}

              {status === 'error' && (
                <div className="flex items-center mt-4 text-red-500">
                  <AlertCircle className="w-5 h-5 mr-2" />
                  <p>{error}</p>
                </div>
              )}
            </div>

            {status === 'idle' && (
              <div className="flex space-x-3">
                <Button variant="ghost" onClick={onClose} className="flex-1">
                  Cancel
                </Button>
                <Button onClick={handleUpload} className="flex-1">
                  Upload
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
