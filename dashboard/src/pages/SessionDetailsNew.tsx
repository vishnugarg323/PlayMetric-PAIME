import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { sessionsApi } from '../common/api'
import { ArrowLeft, Brain, Eye, Activity, Play, GraduationCap } from 'lucide-react'
import Button from '../components/Button'
import Loading from '../components/Loading'
import { useEffect, useState } from 'react'

interface AnalysisData {
  // Individual model results
  ocr_result?: {
    text: string
    confidence: number
  }
  blip_result?: {
    caption: string
    confidence: number
  }
  gemini_result?: {
    scene_type: string
    description: string
    confidence: number
  }
  grok_result?: {
    patterns: string[]
    confidence: number
  }
  opencv_result?: {
    ui_elements: any[]
    count: number
  }
  template_result?: {
    matched_templates: any[]
    count: number
  }
  
  // Combined learning
  combined_summary?: {
    action: string
    touch_point?: { x: number, y: number, type: string }
    confidence: number
  }
  
  // Frame comparison
  frame_diff?: {
    changes: string[]
    similarity: number
  }
}

export default function SessionDetailsNew() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  
  const [currentFrame, setCurrentFrame] = useState(0)
  const [totalFrames, setTotalFrames] = useState(0)
  const [screenshot, setScreenshot] = useState<string>('')
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null)
  
  // Learning mode specific
  const [learningStats, setLearningStats] = useState({
    framesAnalyzed: 0,
    touchesDetected: 0,
    patternsLearned: 0,
    videosProcessed: 0
  })

  const { data: session, isLoading, error } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!).then(r => {
      const data = r.data
      // Parse config to get session_type
      if (data.config && typeof data.config === 'string') {
        try {
          const config = JSON.parse(data.config)
          data.session_type = config.session_type || 'playing'
        } catch (e) {
          data.session_type = 'playing'
        }
      }
      console.log('Session loaded:', data)
      return data
    }),
    enabled: !!sessionId,
    refetchInterval: 5000,
  })

  // WebSocket - Listen for frame analysis from backend
  useEffect(() => {
    if (!sessionId || !session) return

    const ws = new WebSocket(`ws://localhost:8007/ws/learning-progress`)
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message:', data)
        
        // Video analysis progress - frame by frame
        if (data.type === 'video_analysis_progress' && data.stage === 'frame_analyzed') {
          setCurrentFrame(data.current_frame || 0)
          setTotalFrames(data.total_frames || 0)
          
          // Set screenshot from frame path
          if (data.current_screenshot) {
            // Convert frame path to accessible URL
            const framePath = data.current_screenshot.split('/').slice(-2).join('/')  // Get "video_id/frame.png"
            setScreenshot(`http://localhost:8007/frames/${framePath}`)
          }
          
          // Set analysis data from the new comprehensive structure
          setAnalysisData({
            ocr_result: {
              text: data.ocr_analysis?.text || '',
              confidence: data.ocr_analysis?.confidence || 0
            },
            blip_result: {
              caption: data.blip_analysis?.description || '',
              confidence: data.blip_analysis?.confidence || 0
            },
            gemini_result: {
              scene_type: data.gemini_analysis?.scene_type || '',
              description: data.gemini_analysis?.description || '',
              confidence: data.gemini_analysis?.confidence || 0
            },
            grok_result: {
              patterns: [data.grok_analysis?.analysis || 'N/A'],
              confidence: data.grok_analysis?.confidence || 0
            },
            opencv_result: {
              ui_elements: data.opencv_analysis?.ui_elements || [],
              count: data.opencv_analysis?.total_detected || 0
            },
            template_result: {
              matched_templates: data.template_analysis?.patterns || [],
              count: (data.template_analysis?.patterns || []).length
            },
            combined_summary: {
              action: data.combined_summary?.what_ai_learned || '',
              touch_point: data.combined_summary?.touch_point,
              confidence: data.combined_summary?.overall_confidence || 0
            },
            frame_diff: data.frame_diff  // Will be added later
          })
          
          // Update stats
          setLearningStats(prev => ({
            ...prev,
            framesAnalyzed: data.current_frame || 0,
            touchesDetected: data.combined_summary?.touch_detected ? prev.touchesDetected + 1 : prev.touchesDetected
          }))
        }
      } catch (err) {
        console.error('WebSocket parse error:', err)
      }
    }

    ws.onopen = () => console.log('WebSocket connected')
    ws.onerror = (error) => console.error('WebSocket error:', error)
    ws.onclose = () => console.log('WebSocket disconnected')

    return () => ws?.close()
  }, [sessionId, session])
  
  // 5-second auto-advance timer (as per user requirement)
  useEffect(() => {
    if (!screenshot || currentFrame >= totalFrames) return
    
    const timer = setTimeout(() => {
      // Frame will auto-advance when next WebSocket message arrives
      // This is just to show a "waiting" state after 5 seconds
      console.log('5 seconds elapsed, waiting for next frame...')
    }, 5000)
    
    return () => clearTimeout(timer)
  }, [screenshot, currentFrame, totalFrames])

  if (isLoading) return <Loading text="Loading session details..." />
  if (error || !session) return <div className="text-red-500">Session not found</div>

  const isLearningMode = session.session_type === 'learning'
  const handleStartLearning = async () => {
    // TODO: Call API to start learning
    console.log('Start learning clicked')
  }

  const handleStartPlaying = async () => {
    // TODO: Call API to start playing
    console.log('Start playing clicked')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-6">
      {/* Header */}
      <div className="max-w-[1800px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Button variant="secondary" onClick={() => navigate('/sessions')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Sessions
          </Button>
          
          <div className="flex items-center gap-4">
            {/* Start Button */}
            {session.status === 'pending' && (
              <Button 
                onClick={isLearningMode ? handleStartLearning : handleStartPlaying}
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              >
                {isLearningMode ? 'Start Learning' : 'Start Playing'}
              </Button>
            )}
            
            <div className={`px-4 py-2 rounded-lg font-semibold ${
              isLearningMode 
                ? 'bg-purple-600 text-white' 
                : 'bg-blue-600 text-white'
            }`}>
              {isLearningMode ? (
                <div className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5" />
                  Learning Mode
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Play className="w-5 h-5" />
                  Playing Mode
                </div>
              )}
            </div>
            
            <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
              session.status === 'running' ? 'bg-green-600 text-white' :
              session.status === 'completed' ? 'bg-blue-600 text-white' :
              'bg-yellow-600 text-white'
            }`}>
              {session.status}
            </span>
          </div>
        </div>
        
        {/* Frame Counter */}
        <div className="bg-slate-800/60 backdrop-blur-sm rounded-lg p-4 mb-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div className="text-lg text-white">
              <span className="text-slate-400">Current Frame:</span> 
              <span className="ml-2 font-bold text-cyan-400">{currentFrame}</span>
              <span className="text-slate-400 mx-2">/</span>
              <span className="font-bold text-slate-300">{totalFrames || 0}</span>
            </div>
            {totalFrames > 0 && (
              <div className="text-sm text-slate-400">
                {Math.round((currentFrame / totalFrames) * 100)}% Complete
              </div>
            )}
          </div>
        </div>

        {/* Main Content - 2 Column Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          
          {/* LEFT COLUMN: Single Screenshot Display (7 cols) */}
          <div className="xl:col-span-7 space-y-4">
            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg p-6 border border-slate-700">
              <div className="flex items-center gap-2 mb-4">
                <Eye className="w-5 h-5 text-blue-400" />
                <h2 className="text-xl font-semibold text-white">
                  {isLearningMode ? 'Learning from Video' : 'AI Playing Game'}
                </h2>
              </div>

              {/* Single Frame Display */}
              <div className="relative">
                {screenshot ? (
                  <div className="relative w-full bg-black rounded-lg overflow-hidden">
                    <img 
                      src={screenshot} 
                      alt={`Frame ${currentFrame}`}
                      className="w-full h-auto object-contain"
                      style={{ maxHeight: '600px' }}
                    />
                    
                    {/* Touch Point Overlay */}
                    {analysisData?.combined_summary?.touch_point && (
                      <>
                        <div 
                          className="absolute w-12 h-12 -ml-6 -mt-6 border-4 border-red-500 rounded-full animate-ping"
                          style={{
                            left: `${analysisData.combined_summary.touch_point.x}%`,
                            top: `${analysisData.combined_summary.touch_point.y}%`
                          }}
                        />
                        <div 
                          className="absolute w-3 h-3 -ml-1.5 -mt-1.5 bg-red-500 rounded-full"
                          style={{
                            left: `${analysisData.combined_summary.touch_point.x}%`,
                            top: `${analysisData.combined_summary.touch_point.y}%`
                          }}
                        />
                      </>
                    )}
                  </div>
                ) : (
                  <div className="w-full bg-slate-900 rounded-lg flex items-center justify-center" style={{ minHeight: '400px' }}>
                    <div className="text-center text-slate-500">
                      <Activity className="w-12 h-12 mx-auto mb-3" />
                      <div className="text-sm">Waiting to start...</div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Model Results Section - All AI Model Outputs */}
            {isLearningMode && analysisData && (
              <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg p-6 border border-slate-700">
                <div className="flex items-center gap-2 mb-4">
                  <Brain className="w-5 h-5 text-purple-400" />
                  <h2 className="text-xl font-semibold text-white">Individual Model Results</h2>
                </div>

                <div className="space-y-3">
                  {/* OCR Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-yellow-400 mb-2">📝 OCR (Text Recognition)</div>
                    <div className="text-xs text-slate-300 font-mono">
                      {analysisData.ocr_result?.text || 'No text detected'}
                    </div>
                    {analysisData.ocr_result?.confidence && (
                      <div className="text-xs text-slate-500 mt-1">Confidence: {Math.round(analysisData.ocr_result.confidence * 100)}%</div>
                    )}
                  </div>

                  {/* BLIP Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-blue-400 mb-2">🖼️ BLIP (Image Captioning)</div>
                    <div className="text-xs text-slate-300">
                      {analysisData.blip_result?.caption || 'Processing...'}
                    </div>
                    {analysisData.blip_result?.confidence && (
                      <div className="text-xs text-slate-500 mt-1">Confidence: {Math.round(analysisData.blip_result.confidence * 100)}%</div>
                    )}
                  </div>

                  {/* Gemini Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-green-400 mb-2">✨ Gemini (Scene Understanding)</div>
                    <div className="text-xs text-slate-300">
                      <div className="font-semibold">{analysisData.gemini_result?.scene_type || 'Analyzing...'}</div>
                      <div className="mt-1 text-slate-400">{analysisData.gemini_result?.description || ''}</div>
                    </div>
                  </div>

                  {/* Grok Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-cyan-400 mb-2">🤖 Grok (Pattern Recognition)</div>
                    <div className="text-xs text-slate-300">
                      {analysisData.grok_result?.patterns?.join(', ') || 'No patterns detected'}
                    </div>
                  </div>

                  {/* OpenCV Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-orange-400 mb-2">🎯 OpenCV (Computer Vision)</div>
                    <div className="text-xs text-slate-300">
                      UI Elements: {analysisData.opencv_result?.count || 0} detected
                    </div>
                  </div>

                  {/* Template Matching Results */}
                  <div className="bg-slate-900/50 p-3 rounded-lg">
                    <div className="text-sm font-semibold text-pink-400 mb-2">🎮 Template Matching</div>
                    <div className="text-xs text-slate-300">
                      Matched templates: {analysisData.template_result?.count || 0}
                    </div>
                  </div>

                  {/* Combined Learning */}
                  <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 p-3 rounded-lg border border-purple-500/30">
                    <div className="text-sm font-semibold text-purple-300 mb-2">🎓 Combined Learning & Action</div>
                    <div className="text-xs text-white">
                      {analysisData.combined_summary?.action ? (
                        <div>
                          <div className="font-semibold text-green-400">
                            Action: {analysisData.combined_summary.action}
                          </div>
                          {analysisData.combined_summary.touch_point && (
                            <div className="text-slate-300 mt-1">
                              Position: ({analysisData.combined_summary.touch_point.x?.toFixed(1)}%, {analysisData.combined_summary.touch_point.y?.toFixed(1)}%)
                            </div>
                          )}
                          {analysisData.combined_summary.confidence && (
                            <div className="text-slate-400 mt-1">
                              Confidence: {Math.round(analysisData.combined_summary.confidence * 100)}%
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-slate-400">No action required for this frame</div>
                      )}
                    </div>
                  </div>

                  {/* Difference from Previous Frame */}
                  {currentFrame > 1 && analysisData.frame_diff && (
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-cyan-500/30">
                      <div className="text-sm font-semibold text-cyan-400 mb-2">🔄 Difference from Previous Frame</div>
                      <div className="text-xs text-slate-300">
                        {analysisData.frame_diff.changes?.length > 0 ? (
                          <ul className="list-disc list-inside space-y-1">
                            {analysisData.frame_diff.changes.map((change: string, idx: number) => (
                              <li key={idx}>{change}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-slate-500">No significant changes detected</div>
                        )}
                        {analysisData.frame_diff.similarity !== undefined && (
                          <div className="text-slate-500 mt-2">
                            Similarity: {Math.round(analysisData.frame_diff.similarity * 100)}%
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Stats (5 cols) */}
          <div className="xl:col-span-5 space-y-4">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-purple-900/30 p-4 rounded-lg border border-purple-500/30">
                <div className="text-xs text-purple-300 mb-1">Frames Analyzed</div>
                <div className="text-2xl font-bold text-white">{learningStats.framesAnalyzed}</div>
              </div>
              <div className="bg-red-900/30 p-4 rounded-lg border border-red-500/30">
                <div className="text-xs text-red-300 mb-1">Touches Detected</div>
                <div className="text-2xl font-bold text-white">{learningStats.touchesDetected}</div>
              </div>
              <div className="bg-blue-900/30 p-4 rounded-lg border border-blue-500/30">
                <div className="text-xs text-blue-300 mb-1">Patterns Learned</div>
                <div className="text-2xl font-bold text-white">{learningStats.patternsLearned}</div>
              </div>
              <div className="bg-green-900/30 p-4 rounded-lg border border-green-500/30">
                <div className="text-xs text-green-300 mb-1">Videos Processed</div>
                <div className="text-2xl font-bold text-white">{learningStats.videosProcessed}</div>
              </div>
            </div>
          </div>

          {/* Nothing else */}
        </div>
      </div>
    </div>
  )
}
