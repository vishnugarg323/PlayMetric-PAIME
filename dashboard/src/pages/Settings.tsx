import { useAppStore } from '../store'
import { Brain, User, Info } from 'lucide-react'

export default function Settings() {
  const {
    learningMode,
    setLearningMode,
  } = useAppStore()

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-slate-400">Configure AI learning preferences and view system information</p>
      </div>

      {/* Info Box */}
      <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
        <div className="flex items-start gap-2 text-sm">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-slate-300">
            <p className="font-semibold text-blue-300 mb-2">Device & Gameplay Mode Selection</p>
            <p>Device configuration and gameplay mode selection have been moved to the <strong>Create Session</strong> page.</p>
            <p className="mt-1">This allows you to choose different devices and modes for each individual session!</p>
          </div>
        </div>
      </div>

      {/* Learning Mode Configuration - Information Only */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-white mb-1 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            AI Learning Modes
          </h2>
          <p className="text-sm text-slate-400">
            Understanding how the AI learns to play games
          </p>
        </div>

        {/* Learning Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Default Learning Mode (can be changed per session)
          </label>
          <div className="space-y-3">
            <label
              className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                learningMode === 'auto_play'
                  ? 'bg-purple-900/30 border-purple-500'
                  : 'bg-slate-700 border-slate-600 hover:border-purple-500/50'
              }`}
            >
              <input
                type="radio"
                name="learning_mode"
                value="auto_play"
                checked={learningMode === 'auto_play'}
                onChange={(e) => setLearningMode(e.target.value as any)}
                className="mt-1 mr-3"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-white font-semibold mb-1">
                  <Brain className="w-4 h-4" />
                  AI Auto-Play Mode
                </div>
                <div className="text-sm text-slate-400 mb-2">
                  AI takes full control and plays the game autonomously. It explores, experiments, and learns from its own gameplay.
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-green-900/20 border border-green-500/30 rounded p-2">
                    <span className="text-green-400 font-semibold">✓ Pros:</span>
                    <ul className="text-slate-300 mt-1 space-y-0.5">
                      <li>• No human input needed</li>
                      <li>• Explores all possibilities</li>
                      <li>• Fast learning</li>
                    </ul>
                  </div>
                  <div className="bg-red-900/20 border border-red-500/30 rounded p-2">
                    <span className="text-red-400 font-semibold">✗ Cons:</span>
                    <ul className="text-slate-300 mt-1 space-y-0.5">
                      <li>• May make mistakes</li>
                      <li>• Random exploration</li>
                      <li>• Needs more iterations</li>
                    </ul>
                  </div>
                </div>
              </div>
            </label>

            <label
              className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                learningMode === 'user_guided'
                  ? 'bg-purple-900/30 border-purple-500'
                  : 'bg-slate-700 border-slate-600 hover:border-purple-500/50'
              }`}
            >
              <input
                type="radio"
                name="learning_mode"
                value="user_guided"
                checked={learningMode === 'user_guided'}
                onChange={(e) => setLearningMode(e.target.value as any)}
                className="mt-1 mr-3"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-white font-semibold mb-1">
                  <User className="w-4 h-4" />
                  User-Guided Learning Mode
                </div>
                <div className="text-sm text-slate-400 mb-2">
                  You play the game manually while AI observes and learns from your successful actions and strategies.
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-green-900/20 border border-green-500/30 rounded p-2">
                    <span className="text-green-400 font-semibold">✓ Pros:</span>
                    <ul className="text-slate-300 mt-1 space-y-0.5">
                      <li>• Learns optimal strategies</li>
                      <li>• Higher quality training data</li>
                      <li>• Faster to competence</li>
                    </ul>
                  </div>
                  <div className="bg-red-900/20 border border-red-500/30 rounded p-2">
                    <span className="text-red-400 font-semibold">✗ Cons:</span>
                    <ul className="text-slate-300 mt-1 space-y-0.5">
                      <li>• Requires human time</li>
                      <li>• Limited exploration</li>
                      <li>• Needs multiple sessions</li>
                    </ul>
                  </div>
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Learning Mode Info */}
        <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
          <div className="flex items-start gap-2 text-sm">
            <Info className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
            <div className="text-slate-300">
              <p className="font-semibold text-purple-300 mb-2">How Learning Works:</p>
              {learningMode === 'auto_play' ? (
                <div className="space-y-1">
                  <p>1. AI starts with random exploration</p>
                  <p>2. Records screen states and actions taken</p>
                  <p>3. Tracks which actions lead to progress (rewards)</p>
                  <p>4. Trains Vision AI model on collected data</p>
                  <p>5. Improves action selection over time</p>
                  <p className="mt-2 text-purple-200">
                    💡 <strong>Tip:</strong> Let AI run for longer sessions (10+ minutes) to collect more diverse training data.
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <p>1. You play the game naturally on the device</p>
                  <p>2. AI captures screenshots before each action</p>
                  <p>3. Observes where you tap/swipe and outcomes</p>
                  <p>4. Builds training dataset from your gameplay</p>
                  <p>5. Uses this data to train its models</p>
                  <p className="mt-2 text-purple-200">
                    💡 <strong>Tip:</strong> Play through different scenarios and levels for better training diversity.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
