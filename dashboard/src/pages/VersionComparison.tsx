import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, Bug, Target, Clock, Zap, AlertTriangle, Activity, TrendingDown as Crash } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

// Dummy game info - Using actual game from database
const DUMMY_GAME = {
  game_id: 'dummy-game',
  game_name: 'Screw Pin Puzzle',
  package_name: 'com.ruffgames.screw.pull',
  category: 'Puzzle'
}

// Dummy data fallback for Screw Pin Puzzle game different versions
const DUMMY_VERSIONS = [
  {
    id: 'v1',
    version_name: '1.0.5',
    version_code: 105,
    releaseDate: '2024-08-15',
    totalLevels: 100,
  },
  {
    id: 'v2',
    version_name: '1.1.2',
    version_code: 112,
    releaseDate: '2024-09-20',
    totalLevels: 120,
  },
  {
    id: 'v3',
    version_name: '1.2.8',
    version_code: 128,
    releaseDate: '2024-10-15',
    totalLevels: 150,
  },
  {
    id: 'v4',
    version_name: '2.0.1',
    version_code: 201,
    releaseDate: '2024-11-05',
    totalLevels: 200,
  },
]

const DUMMY_COMPARISON_DATA = {
  'v1-v2': {
    // Database fields
    bugs_fixed_count: 5,
    bugs_introduced_count: 1,
    regression_bugs_count: 0,
    performance_change_percent: 12.3,
    crash_rate_change_percent: -18.4,
    difficulty_change_percent: -5.2,
    retention_change_percent: 8.7,
    levels_easier: 3,
    levels_harder: 1,
    summary: 'Version 1.1.2 delivers significant stability improvements with an 18.4% reduction in crash rates. Performance optimizations result in 12.3% faster level loading. Five critical bugs from v1.0.5 were resolved, including screw collision detection and physics glitches. Minor difficulty rebalancing makes early levels more accessible, contributing to 8.7% better day-1 retention.',
    recommendations: [
      'Monitor the new screw animation issue reported on Level 23',
      'A/B test the simplified tutorial on Levels 1-5 for optimal onboarding',
      'Consider expanding Level 20 hints based on improved completion rates',
      'Track user feedback on the new bolt color scheme'
    ],
    
    // Additional UI data
    levelDifficulty: [
      { level: 5, v1: 3.2, v2: 2.8, change: -12.5, label: 'Easier' },
      { level: 10, v1: 4.5, v2: 4.5, change: 0, label: 'Same' },
      { level: 15, v1: 5.1, v2: 5.8, change: 13.7, label: 'Harder' },
      { level: 20, v1: 6.2, v2: 5.5, change: -11.3, label: 'Easier' },
      { level: 25, v1: 7.3, v2: 8.1, change: 11.0, label: 'Harder' },
    ],
    bugsFixed: [
      { id: 1, level: 8, description: 'Screws overlapping causing incorrect unscrewing sequence', severity: 'high' },
      { id: 2, level: 12, description: 'Timer continues when app is backgrounded', severity: 'medium' },
      { id: 3, level: 18, description: 'Wrong sound effect when removing last screw', severity: 'low' },
      { id: 4, level: 7, description: 'Physics glitch allows screws to pass through metal plates', severity: 'critical' },
      { id: 5, level: 15, description: 'Hint button not working on certain device models', severity: 'high' },
    ],
    bugsIntroduced: [
      { id: 6, level: 23, description: 'New screw rotation animation stutters on older devices', severity: 'medium' },
    ],
    progressionChanges: {
      avgCompletionTime: { v1: 45.2, v2: 42.8, change: -5.3 },
      avgActionsPerLevel: { v1: 18.5, v2: 17.2, change: -7.0 },
      successRate: { v1: 78.3, v2: 82.1, change: 4.9 },
      hintsUsed: { v1: 3.2, v2: 2.1, change: -34.4 },
    },
  },
  'v2-v3': {
    // Database fields
    bugs_fixed_count: 1,
    bugs_introduced_count: 3,
    regression_bugs_count: 2,
    performance_change_percent: -7.8,
    crash_rate_change_percent: 22.6,
    difficulty_change_percent: 8.9,
    retention_change_percent: -6.3,
    levels_easier: 1,
    levels_harder: 3,
    summary: 'Version 1.2.8 introduces 30 new challenging levels but suffers from stability issues. Crash rate increased 22.6% due to device-specific bugs on Samsung and Xiaomi devices. Performance degraded with new visual effects. Two regression bugs reappeared from v1.0.5. Increased difficulty in levels 30-50 led to 6.3% drop in retention. Immediate hotfix recommended.',
    recommendations: [
      'URGENT: Fix Level 35 metal plate collision causing app freeze on Samsung Galaxy S21/S22',
      'Investigate crash on screen rotation - affects 15% of Android 13 devices',
      'Revert or optimize particle effects causing 7.8% performance drop',
      'Consider difficulty rebalancing for Levels 30-45 - completion rate dropped 18%',
      'Re-test regression bugs: screw physics glitch and timer issues resurfaced'
    ],
    
    // Additional UI data
    levelDifficulty: [
      { level: 5, v1: 2.8, v2: 2.9, change: 3.6, label: 'Slightly Harder' },
      { level: 10, v1: 4.5, v2: 4.3, change: -4.4, label: 'Easier' },
      { level: 15, v1: 5.8, v2: 6.5, change: 12.1, label: 'Harder' },
      { level: 20, v1: 5.5, v2: 5.2, change: -5.5, label: 'Easier' },
      { level: 30, v1: 8.2, v2: 9.1, change: 11.0, label: 'Harder' },
    ],
    bugsFixed: [
      { id: 6, level: 23, description: 'Fixed screw rotation animation stutter', severity: 'medium' },
    ],
    bugsIntroduced: [
      { id: 7, level: 35, description: 'Metal plate collision causes app freeze on Samsung devices', severity: 'critical' },
      { id: 8, level: 42, description: 'App crashes when rotating screen during screw removal', severity: 'high' },
      { id: 9, level: 28, description: 'New particle effects cause lag on mid-range phones', severity: 'medium' },
    ],
    progressionChanges: {
      avgCompletionTime: { v1: 42.8, v2: 46.5, change: 8.6 },
      avgActionsPerLevel: { v1: 17.2, v2: 19.8, change: 15.1 },
      successRate: { v1: 82.1, v2: 75.4, change: -8.2 },
      hintsUsed: { v1: 2.1, v2: 3.8, change: 81.0 },
    },
  },
  'v3-v4': {
    // Database fields
    bugs_fixed_count: 6,
    bugs_introduced_count: 1,
    regression_bugs_count: 0,
    performance_change_percent: 24.7,
    crash_rate_change_percent: -51.3,
    difficulty_change_percent: -14.8,
    retention_change_percent: 28.9,
    levels_easier: 5,
    levels_harder: 0,
    summary: 'Version 2.0.1 is a major quality milestone that resolves all critical issues from v1.2.8. Crash rate plummeted by 51.3% with device-specific fixes for Samsung and Xiaomi. Performance improved 24.7% through optimized particle rendering and physics calculations. Comprehensive difficulty rebalancing across 50 levels resulted in 28.9% retention boost. Best performing version to date with only one minor UI issue.',
    recommendations: [
      'Excellent release - establish as quality baseline for future updates',
      'Minor: Improve screw unlock tutorial clarity on Level 55 (12% skip rate)',
      'Leverage stability improvements in marketing campaigns',
      'Continue current QA process - device testing particularly effective',
      'Monitor long-term retention metrics for newly rebalanced levels',
      'Consider similar rebalancing approach for Levels 100-150'
    ],
    
    // Additional UI data
    levelDifficulty: [
      { level: 10, v1: 4.3, v2: 3.8, change: -11.6, label: 'Easier' },
      { level: 20, v1: 5.2, v2: 5.0, change: -3.8, label: 'Slightly Easier' },
      { level: 30, v1: 9.1, v2: 7.2, change: -20.9, label: 'Much Easier' },
      { level: 40, v1: 10.5, v2: 9.8, change: -6.7, label: 'Easier' },
      { level: 50, v1: 12.1, v2: 11.5, change: -5.0, label: 'Easier' },
    ],
    bugsFixed: [
      { id: 7, level: 35, description: 'Fixed critical metal plate collision freeze on Samsung Galaxy devices', severity: 'critical' },
      { id: 8, level: 42, description: 'Resolved screen rotation crash on Android 13', severity: 'high' },
      { id: 9, level: 28, description: 'Optimized particle effects for mid-range devices', severity: 'medium' },
      { id: 10, level: 15, description: 'Improved screw spawning physics accuracy', severity: 'medium' },
      { id: 11, level: 7, description: 'Fixed regression: screw-through-plate glitch', severity: 'high' },
      { id: 12, level: 12, description: 'Fixed regression: timer running in background', severity: 'medium' },
    ],
    bugsIntroduced: [
      { id: 13, level: 55, description: 'New screw unlock mechanic tutorial could be clearer', severity: 'low' },
    ],
    progressionChanges: {
      avgCompletionTime: { v1: 46.5, v2: 38.2, change: -17.8 },
      avgActionsPerLevel: { v1: 19.8, v2: 15.4, change: -22.2 },
      successRate: { v1: 75.4, v2: 88.9, change: 17.9 },
      hintsUsed: { v1: 3.8, v2: 1.9, change: -50.0 },
    },
  },
}

const TrendIcon = ({ value }: { value: number }) => {
  if (value > 5) return <TrendingUp className="w-4 h-4 text-red-400" />
  if (value < -5) return <TrendingDown className="w-4 h-4 text-green-400" />
  return <Minus className="w-4 h-4 text-slate-400" />
}

const ChangeText = ({ value, suffix = '%', inverse = false }: { value: number; suffix?: string; inverse?: boolean }) => {
  const isPositive = inverse ? value < 0 : value > 0
  const color = Math.abs(value) < 5 ? 'text-slate-400' : isPositive ? 'text-green-400' : 'text-red-400'
  const prefix = value > 0 ? '+' : ''
  
  return (
    <span className={`font-semibold ${color}`}>
      {prefix}{value.toFixed(1)}{suffix}
    </span>
  )
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'bg-red-900/30 border-red-500/50 text-red-300'
    case 'high':
      return 'bg-orange-900/30 border-orange-500/50 text-orange-300'
    case 'medium':
      return 'bg-yellow-900/30 border-yellow-500/50 text-yellow-300'
    case 'low':
      return 'bg-blue-900/30 border-blue-500/50 text-blue-300'
    default:
      return 'bg-slate-700 border-slate-600 text-slate-300'
  }
}

export default function VersionComparison() {
  const [version1, setVersion1] = useState('v1')
  const [version2, setVersion2] = useState('v2')
  const [selectedGame, setSelectedGame] = useState('dummy-game')

  // Fetch all games
  const { data: games = [] } = useQuery({
    queryKey: ['games'],
    queryFn: () => fetch('http://localhost:8000/games').then(r => r.json()),
  })

  // Fetch versions for selected game
  const { data: versions = [] } = useQuery({
    queryKey: ['game-versions', selectedGame],
    queryFn: () => selectedGame && selectedGame !== 'dummy-game' ? fetch(`http://localhost:8000/games/${selectedGame}/versions`).then(r => r.json()) : Promise.resolve([]),
    enabled: !!(selectedGame && selectedGame !== 'dummy-game'),
  })

  // Fetch comparison data when both versions are selected
  const { data: comparisonData } = useQuery({
    queryKey: ['version-comparison', version1, version2],
    queryFn: () => fetch(`http://localhost:8000/analytics/versions/compare?v1=${version1}&v2=${version2}`).then(r => r.json()),
    enabled: !!(version1 && version2 && version1 !== version2 && !version1.startsWith('v') && !version2.startsWith('v')),
  })

  // Don't auto-switch to real games - keep dummy data by default
  // Users can manually select a real game if they want
  useEffect(() => {
    // Only switch if user manually selected a real game
    if (versions && versions.length > 1 && selectedGame !== 'dummy-game' && !version1 && !version2) {
      setVersion1((versions as any)[0].id)
      setVersion2((versions as any)[1].id)
    }
  }, [versions, version1, version2, selectedGame])

  const selectedGameInfo = selectedGame === 'dummy-game' ? DUMMY_GAME : (games as any[])?.find((g: any) => g.game_id === selectedGame)
  
  // Fallback to dummy data if no real comparison data
  const useDummyData = !comparisonData || comparisonData.message || selectedGame === 'dummy-game'

  const comparisonKey = `${version1}-${version2}`
  const reverseKey = `${version2}-${version1}`
  const data = useDummyData ? (
    DUMMY_COMPARISON_DATA[comparisonKey as keyof typeof DUMMY_COMPARISON_DATA] || 
    DUMMY_COMPARISON_DATA[reverseKey as keyof typeof DUMMY_COMPARISON_DATA]
  ) : comparisonData.comparison_data || comparisonData

  if (!data) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">No Comparison Data</h2>
        <p className="text-slate-400">Select different versions to see comparison</p>
      </div>
    )
  }

  const v1Info = useDummyData 
    ? DUMMY_VERSIONS.find(v => v.id === version1)
    : versions?.find((v: any) => v.id === version1)
  const v2Info = useDummyData
    ? DUMMY_VERSIONS.find(v => v.id === version2)
    : versions?.find((v: any) => v.id === version2)

  const v1Name = v1Info?.version_name || v1Info?.name || 'Version A'
  const v2Name = v2Info?.version_name || v2Info?.name || 'Version B'

  return (
    <div className="space-y-6">
      {/* Header with Game Name */}
      <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg border border-purple-500/30 p-6">
        <h1 className="text-3xl font-bold text-white mb-2">Version Comparison</h1>
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <p className="text-sm text-slate-400">Game:</p>
            <p className="text-xl font-semibold text-purple-300">
              {selectedGameInfo?.game_name || 'Select a game'}
            </p>
          </div>
          <div className="text-slate-500">→</div>
          <div>
            <p className="text-sm text-slate-400">Package:</p>
            <p className="text-sm font-mono text-blue-300">
              {selectedGameInfo?.package_name || 'N/A'}
            </p>
          </div>
          <div className="ml-auto">
            <p className="text-sm text-slate-400">Category:</p>
            <p className="text-sm font-medium text-green-300">
              {selectedGameInfo?.category || 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Game Selection */}
      {games && games.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Select Game</h2>
          <select
            value={selectedGame}
            onChange={(e) => {
              setSelectedGame(e.target.value)
              setVersion1('')
              setVersion2('')
            }}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {games.map((game: any) => (
              <option key={game.game_id} value={game.game_id}>
                {game.game_name} ({game.package_name})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Version Selection */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Select Versions to Compare</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Base Version (Older)
            </label>
            <select
              value={version1}
              onChange={(e) => setVersion1(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select version...</option>
              {(useDummyData ? DUMMY_VERSIONS : versions || []).map((v: any) => (
                <option key={v.id} value={v.id} disabled={v.id === version2}>
                  {v.version_name || v.name} - {v.uploaded_at ? new Date(v.uploaded_at).toLocaleDateString() : v.releaseDate}
                  {v.version_code && ` (v${v.version_code})`}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Comparison Version (Newer)
            </label>
            <select
              value={version2}
              onChange={(e) => setVersion2(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select version...</option>
              {(useDummyData ? DUMMY_VERSIONS : versions || []).map((v: any) => (
                <option key={v.id} value={v.id} disabled={v.id === version1}>
                  {v.version_name || v.name} - {v.uploaded_at ? new Date(v.uploaded_at).toLocaleDateString() : v.releaseDate}
                  {v.version_code && ` (v${v.version_code})`}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Key Metrics Overview - Real Database Fields */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          Comparison Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {/* Bugs Fixed */}
          <div className="bg-green-900/20 rounded-lg p-4 border border-green-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Bug className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-300">Bugs Fixed</span>
            </div>
            <div className="text-3xl font-bold text-green-400 mb-1">
              {!useDummyData && comparisonData?.bugs_fixed_count !== undefined
                ? comparisonData.bugs_fixed_count
                : data?.bugsFixed?.length || 0}
            </div>
            <div className="text-xs text-green-300">Improvements</div>
          </div>

          {/* Bugs Introduced */}
          <div className="bg-red-900/20 rounded-lg p-4 border border-red-700/50">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-slate-300">New Issues</span>
            </div>
            <div className="text-3xl font-bold text-red-400 mb-1">
              {!useDummyData && comparisonData?.bugs_introduced_count !== undefined
                ? comparisonData.bugs_introduced_count
                : data?.bugsIntroduced?.length || 0}
            </div>
            <div className="text-xs text-red-300">Regressions</div>
          </div>

          {/* Regression Bugs */}
          {!useDummyData && comparisonData?.regression_bugs_count !== undefined && (
            <div className="bg-orange-900/20 rounded-lg p-4 border border-orange-700/50">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <span className="text-sm text-slate-300">Regression Bugs</span>
              </div>
              <div className="text-3xl font-bold text-orange-400 mb-1">
                {comparisonData.regression_bugs_count}
              </div>
              <div className="text-xs text-orange-300">Critical Issues</div>
            </div>
          )}

          {/* Performance Change */}
          {!useDummyData && comparisonData?.performance_change_percent !== undefined && comparisonData.performance_change_percent !== null && (
            <div className="bg-blue-900/20 rounded-lg p-4 border border-blue-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-slate-300">Performance</span>
              </div>
              <div className="text-3xl font-bold text-blue-400 mb-1 flex items-center gap-2">
                <TrendIcon value={comparisonData.performance_change_percent} />
                <ChangeText value={comparisonData.performance_change_percent} />
              </div>
              <div className="text-xs text-blue-300">Change</div>
            </div>
          )}

          {/* Crash Rate Change */}
          {!useDummyData && comparisonData?.crash_rate_change_percent !== undefined && comparisonData.crash_rate_change_percent !== null && (
            <div className="bg-purple-900/20 rounded-lg p-4 border border-purple-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Crash className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-slate-300">Crash Rate</span>
              </div>
              <div className="text-3xl font-bold text-purple-400 mb-1 flex items-center gap-2">
                <TrendIcon value={comparisonData.crash_rate_change_percent} />
                <ChangeText value={comparisonData.crash_rate_change_percent} inverse />
              </div>
              <div className="text-xs text-purple-300">Change</div>
            </div>
          )}

          {/* Difficulty Change */}
          {!useDummyData && comparisonData?.difficulty_change_percent !== undefined && comparisonData.difficulty_change_percent !== null && (
            <div className="bg-yellow-900/20 rounded-lg p-4 border border-yellow-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-slate-300">Difficulty</span>
              </div>
              <div className="text-3xl font-bold text-yellow-400 mb-1 flex items-center gap-2">
                <TrendIcon value={comparisonData.difficulty_change_percent} />
                <ChangeText value={comparisonData.difficulty_change_percent} />
              </div>
              <div className="text-xs text-yellow-300">Change</div>
            </div>
          )}

          {/* Retention Change */}
          {!useDummyData && comparisonData?.retention_change_percent !== undefined && comparisonData.retention_change_percent !== null && (
            <div className="bg-teal-900/20 rounded-lg p-4 border border-teal-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-teal-400" />
                <span className="text-sm text-slate-300">Retention</span>
              </div>
              <div className="text-3xl font-bold text-teal-400 mb-1 flex items-center gap-2">
                <TrendIcon value={comparisonData.retention_change_percent} />
                <ChangeText value={comparisonData.retention_change_percent} />
              </div>
              <div className="text-xs text-teal-300">Change</div>
            </div>
          )}
        </div>

        {/* Level Difficulty Summary */}
        {!useDummyData && (comparisonData?.levels_easier || comparisonData?.levels_harder) && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="w-4 h-4 text-green-400" />
                <span className="text-sm text-slate-300">Levels Easier</span>
              </div>
              <div className="text-2xl font-bold text-green-400">{comparisonData.levels_easier || 0}</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-red-400" />
                <span className="text-sm text-slate-300">Levels Harder</span>
              </div>
              <div className="text-2xl font-bold text-red-400">{comparisonData.levels_harder || 0}</div>
            </div>
          </div>
        )}
      </div>

      {/* Summary and Recommendations */}
      {!useDummyData && (comparisonData?.summary || comparisonData?.recommendations) && (
        <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-lg border border-blue-500/30 p-6">
          {comparisonData.summary && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-white mb-2">Summary</h3>
              <p className="text-slate-300">{comparisonData.summary}</p>
            </div>
          )}
          {comparisonData.recommendations && comparisonData.recommendations.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Recommendations</h3>
              <ul className="space-y-2">
                {comparisonData.recommendations.map((rec: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2 text-slate-300">
                    <span className="text-blue-400">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Fallback to old progression metrics for dummy data */}
      {useDummyData && data?.progressionChanges && (
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Progression Metrics (Demo Data)
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-slate-400">Avg Completion Time</span>
            </div>
            <div className="text-2xl font-bold text-white mb-1">
              {data.progressionChanges.avgCompletionTime.v2.toFixed(1)}s
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendIcon value={data.progressionChanges.avgCompletionTime.change} />
              <ChangeText value={data.progressionChanges.avgCompletionTime.change} inverse />
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-400">Success Rate</span>
            </div>
            <div className="text-2xl font-bold text-white mb-1">
              {data.progressionChanges.successRate.v2.toFixed(1)}%
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendIcon value={data.progressionChanges.successRate.change} />
              <ChangeText value={data.progressionChanges.successRate.change} />
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-purple-400" />
              <span className="text-sm text-slate-400">Actions Per Level</span>
            </div>
            <div className="text-2xl font-bold text-white mb-1">
              {data.progressionChanges.avgActionsPerLevel.v2.toFixed(1)}
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendIcon value={data.progressionChanges.avgActionsPerLevel.change} />
              <ChangeText value={data.progressionChanges.avgActionsPerLevel.change} inverse />
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-orange-400" />
              <span className="text-sm text-slate-400">Hints Used</span>
            </div>
            <div className="text-2xl font-bold text-white mb-1">
              {data.progressionChanges.hintsUsed.v2.toFixed(1)}
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendIcon value={data.progressionChanges.hintsUsed.change} />
              <ChangeText value={data.progressionChanges.hintsUsed.change} inverse />
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Level Difficulty Comparison */}
      {useDummyData && data?.levelDifficulty && (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-purple-400" />
          Level Difficulty Changes
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Level</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">{v1Name}</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">{v2Name}</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Change</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Assessment</th>
              </tr>
            </thead>
            <tbody>
              {data.levelDifficulty.map((item: any, idx: number) => (
                <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-3 px-4 text-white font-semibold">Level {item.level}</td>
                  <td className="py-3 px-4 text-slate-300">{item.v1.toFixed(1)} / 10</td>
                  <td className="py-3 px-4 text-slate-300">{item.v2.toFixed(1)} / 10</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <TrendIcon value={item.change} />
                      <ChangeText value={item.change} />
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      item.label.includes('Easier') ? 'bg-green-900/30 text-green-300' :
                      item.label.includes('Harder') ? 'bg-red-900/30 text-red-300' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {item.label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Bugs Fixed and Introduced */}
      {useDummyData && data?.bugsFixed && data?.bugsIntroduced && (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bugs Fixed */}
        <div className="bg-green-900/10 rounded-lg border border-green-500/30 p-6">
          <h2 className="text-lg font-semibold text-green-300 mb-4 flex items-center gap-2">
            <Bug className="w-5 h-5" />
            Bugs Fixed ({data.bugsFixed.length})
          </h2>
          <div className="space-y-3">
            {data.bugsFixed.map((bug: any) => (
              <div key={bug.id} className={`rounded-lg p-3 border ${getSeverityColor(bug.severity)}`}>
                <div className="flex items-start justify-between mb-1">
                  <span className="text-xs font-semibold uppercase">{bug.severity}</span>
                  <span className="text-xs text-slate-400">Level {bug.level}</span>
                </div>
                <p className="text-sm">{bug.description}</p>
              </div>
            ))}
            {data.bugsFixed.length === 0 && (
              <p className="text-slate-400 text-sm">No bugs fixed in this version</p>
            )}
          </div>
        </div>

        {/* Bugs Introduced */}
        <div className="bg-red-900/10 rounded-lg border border-red-500/30 p-6">
          <h2 className="text-lg font-semibold text-red-300 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            New Issues ({data.bugsIntroduced.length})
          </h2>
          <div className="space-y-3">
            {data.bugsIntroduced.map((bug: any) => (
              <div key={bug.id} className={`rounded-lg p-3 border ${getSeverityColor(bug.severity)}`}>
                <div className="flex items-start justify-between mb-1">
                  <span className="text-xs font-semibold uppercase">{bug.severity}</span>
                  <span className="text-xs text-slate-400">Level {bug.level}</span>
                </div>
                <p className="text-sm">{bug.description}</p>
              </div>
            ))}
            {data.bugsIntroduced.length === 0 && (
              <p className="text-slate-400 text-sm">No new issues detected</p>
            )}
          </div>
        </div>
      </div>
      )}

      {/* Note about data source */}
      {useDummyData ? (
      <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
        <p className="text-sm text-blue-300">
          <strong>Note:</strong> This is demonstration data. 
          Real comparison data will be generated from actual AI gameplay sessions once multiple versions are tested.
        </p>
      </div>
      ) : (
      <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
        <p className="text-sm text-green-300">
          <strong>✓ Real Data:</strong> This comparison is based on actual gameplay data collected from AI testing sessions.
        </p>
      </div>
      )}
    </div>
  )
}
