// import { useQuery } from '@tanstack/react-query'
import { AlertCircle, AlertTriangle, Info, Bug } from 'lucide-react'
// import { api } from '../services/api'
import { useState } from 'react'

export default function BugsPage() {
  const [activeTab, setActiveTab] = useState<'all' | 'by-game' | 'by-type' | 'by-version'>('all')
  
  // Static fake bugs for demo for all games
  const bugs = [
    // Screw Unscrew
    {
      bug_id: 1,
      bug_type: 'UI glitch',
      severity: 'critical',
      game_name: 'Screw Unscrew',
      description: 'Screw count display flickers when moving to level 2.',
      timestamp: new Date().toISOString()
    },
    {
      bug_id: 2,
      bug_type: 'Logic bug',
      severity: 'high',
      game_name: 'Screw Unscrew',
      description: 'Screw does not register in the box on first attempt in level 2.',
      timestamp: new Date().toISOString()
    },
    // Factory Jam
    {
      bug_id: 3,
      bug_type: 'Sorting error',
      severity: 'critical',
      game_name: 'Factory Jam',
      description: 'Bottle sorting fails when conveyor speed increases.',
      timestamp: new Date().toISOString()
    },
    {
      bug_id: 4,
      bug_type: 'UI freeze',
      severity: 'medium',
      game_name: 'Factory Jam',
      description: 'UI freezes when sorting more than 10 bottles.',
      timestamp: new Date().toISOString()
    },
    // Blocky Knits
    {
      bug_id: 5,
      bug_type: 'Puzzle logic',
      severity: 'high',
      game_name: 'Blocky Knits',
      description: 'Yarn blocks do not align correctly in hard levels.',
      timestamp: new Date().toISOString()
    },
    {
      bug_id: 6,
      bug_type: 'Level stuck',
      severity: 'low',
      game_name: 'Blocky Knits',
      description: 'Player gets stuck after completing level 3.',
      timestamp: new Date().toISOString()
    },
    // Make Them 100!
    {
      bug_id: 7,
      bug_type: 'Bubble count error',
      severity: 'medium',
      game_name: 'Make Them 100!',
      description: 'Bubble count does not reset after popping.',
      timestamp: new Date().toISOString()
    },
    {
      bug_id: 8,
      bug_type: 'Pop animation bug',
      severity: 'low',
      game_name: 'Make Them 100!',
      description: 'Pop animation lags when popping multiple bubbles.',
      timestamp: new Date().toISOString()
    }
  ];
  const bugsByGame = [
    {
      game_id: 'screw_unscrew',
      game_name: 'Screw Unscrew',
      package_name: 'com.screw.unscrew',
      total_bugs: 3,
      critical_bugs: 1,
      high_bugs: 1,
      medium_bugs: 1,
      open_bugs: 3
    },
    {
      game_id: 'factory_jam',
      game_name: 'Factory Jam',
      package_name: 'com.factory.jam',
      total_bugs: 2,
      critical_bugs: 1,
      high_bugs: 0,
      medium_bugs: 1,
      open_bugs: 2
    },
    {
      game_id: 'blocky_knits',
      game_name: 'Blocky Knits',
      package_name: 'com.blocky.knits',
      total_bugs: 2,
      critical_bugs: 0,
      high_bugs: 1,
      medium_bugs: 1,
      open_bugs: 2
    },
    {
      game_id: 'make_them_100',
      game_name: 'Make Them 100!',
      package_name: 'com.make.them100',
      total_bugs: 2,
      critical_bugs: 0,
      high_bugs: 0,
      medium_bugs: 1,
      open_bugs: 2
    }
  ];
  const bugsByType = [
    {
      bug_type: 'UI glitch',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 1,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Logic bug',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 1,
      medium_count: 0,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Performance',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 0,
      medium_count: 1,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Sorting error',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 1,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'UI freeze',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 0,
      medium_count: 1,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Puzzle logic',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 1,
      medium_count: 0,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Level stuck',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 0,
      medium_count: 1,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Bubble count error',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 0,
      medium_count: 1,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    },
    {
      bug_type: 'Pop animation bug',
      affected_games: 1,
      total_bugs: 1,
      critical_count: 0,
      high_count: 0,
      medium_count: 1,
      low_count: 0,
      open_count: 1,
      resolved_count: 0
    }
  ];
  const bugsByVersion = [
    {
      game_id: 'screw_unscrew',
      game_name: 'Screw Unscrew',
      version: '1.0',
      release_date: new Date().toISOString(),
      bugs_introduced: bugs.slice(0, 2),
      bugs_resolved: []
    },
    {
      game_id: 'factory_jam',
      game_name: 'Factory Jam',
      version: '1.0',
      release_date: new Date().toISOString(),
      bugs_introduced: bugs.slice(2, 4),
      bugs_resolved: []
    },
    {
      game_id: 'blocky_knits',
      game_name: 'Blocky Knits',
      version: '1.0',
      release_date: new Date().toISOString(),
      bugs_introduced: bugs.slice(4, 6),
      bugs_resolved: []
    },
    {
      game_id: 'make_them_100',
      game_name: 'Make Them 100!',
      version: '1.0',
      release_date: new Date().toISOString(),
      bugs_introduced: bugs.slice(6, 8),
      bugs_resolved: []
    }
  ];
  const bugsSummary = {
    total_bugs: bugs.length,
    critical_bugs: bugs.filter(b => b.severity === 'critical').length,
    open_bugs: bugs.length,
    bug_types_count: Array.from(new Set(bugs.map(b => b.bug_type))).length
  };
  const isLoading = false;
  
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-50'
      case 'high': return 'border-orange-500 bg-orange-50'
      case 'medium': return 'border-yellow-500 bg-yellow-50'
      default: return 'border-blue-500 bg-blue-50'
    }
  }
  
  if (isLoading) return <div>Loading...</div>
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Bug Reports</h1>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <Bug className="w-4 h-4" />
          <span>Total: {bugsSummary?.total_bugs || 0}</span>
          <span className="text-red-600">Critical: {bugsSummary?.critical_bugs || 0}</span>
        </div>
      </div>
      
      {/* Summary Cards */}
      {bugsSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-gray-900">{bugsSummary.total_bugs}</div>
            <div className="text-sm text-gray-600">Total Bugs</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-red-600">{bugsSummary.critical_bugs}</div>
            <div className="text-sm text-gray-600">Critical</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-orange-600">{bugsSummary.open_bugs}</div>
            <div className="text-sm text-gray-600">Open</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-blue-600">{bugsSummary.bug_types_count}</div>
            <div className="text-sm text-gray-600">Bug Types</div>
          </div>
        </div>
      )}
      
      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('all')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'all'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              All Bugs ({bugs?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('by-game')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'by-game'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              By Game ({bugsByGame?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('by-type')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'by-type'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              By Type ({bugsByType?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('by-version')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'by-version'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Version Tracking ({bugsByVersion?.length || 0})
            </button>
          </nav>
        </div>
        
        <div className="p-6">
          {/* All Bugs Tab */}
          {activeTab === 'all' && (
            <div className="space-y-4">
              {bugs?.map((bug: any) => (
                <div key={bug.bug_id} className={`border-l-4 pl-4 py-3 rounded-r ${getSeverityColor(bug.severity)}`}>
                  <div className="flex items-start">
                    {getSeverityIcon(bug.severity)}
                    <div className="ml-3 flex-1">
                      <div className="flex justify-between">
                        <h3 className="font-semibold">{bug.bug_type}</h3>
                        <span className="text-sm text-gray-500">{bug.game_name}</span>
                      </div>
                      <p className="text-gray-600 mt-1">{bug.description}</p>
                      <div className="flex justify-between items-center mt-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          bug.severity === 'critical' ? 'bg-red-100 text-red-800' :
                          bug.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {bug.severity.toUpperCase()}
                        </span>
                        <p className="text-sm text-gray-500">
                          {new Date(bug.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {!bugs?.length && (
                <div className="text-center py-8 text-gray-500">
                  No bugs found
                </div>
              )}
            </div>
          )}
          
          {/* By Game Tab */}
          {activeTab === 'by-game' && (
            <div className="space-y-4">
              {bugsByGame?.map((gameData: any) => (
                <div key={gameData.game_id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg">{gameData.game_name}</h3>
                      <p className="text-sm text-gray-600">{gameData.package_name}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-gray-900">{gameData.total_bugs}</div>
                      <div className="text-sm text-gray-600">Total Bugs</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-lg font-semibold text-red-600">{gameData.critical_bugs}</div>
                      <div className="text-xs text-gray-600">Critical</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-orange-600">{gameData.high_bugs}</div>
                      <div className="text-xs text-gray-600">High</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-yellow-600">{gameData.medium_bugs}</div>
                      <div className="text-xs text-gray-600">Medium</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-green-600">{gameData.open_bugs}</div>
                      <div className="text-xs text-gray-600">Open</div>
                    </div>
                  </div>
                </div>
              ))}
              {!bugsByGame?.length && (
                <div className="text-center py-8 text-gray-500">
                  No games with bugs found
                </div>
              )}
            </div>
          )}
          
          {/* By Type Tab */}
          {activeTab === 'by-type' && (
            <div className="space-y-4">
              {bugsByType?.map((typeData: any) => (
                <div key={typeData.bug_type} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg capitalize">{typeData.bug_type} Bugs</h3>
                      <p className="text-sm text-gray-600">Affected Games: {typeData.affected_games}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-gray-900">{typeData.total_bugs}</div>
                      <div className="text-sm text-gray-600">Total</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                    <div className="text-center">
                      <div className="text-lg font-semibold text-red-600">{typeData.critical_count}</div>
                      <div className="text-xs text-gray-600">Critical</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-orange-600">{typeData.high_count}</div>
                      <div className="text-xs text-gray-600">High</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-yellow-600">{typeData.medium_count}</div>
                      <div className="text-xs text-gray-600">Medium</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-blue-600">{typeData.low_count}</div>
                      <div className="text-xs text-gray-600">Low</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-green-600">{typeData.open_count}</div>
                      <div className="text-xs text-gray-600">Open</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-gray-600">{typeData.resolved_count}</div>
                      <div className="text-xs text-gray-600">Resolved</div>
                    </div>
                  </div>
                </div>
              ))}
              {!bugsByType?.length && (
                <div className="text-center py-8 text-gray-500">
                  No bug types found
                </div>
              )}
            </div>
          )}

          {/* Version Tracking Tab */}
          {activeTab === 'by-version' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <h3 className="font-semibold text-blue-900 mb-2">Bug Version Tracking</h3>
                <p className="text-sm text-blue-700">
                  Track which bugs were introduced and resolved in different game versions.
                </p>
              </div>
              
              {bugsByVersion?.map((versionData: any) => (
                <div key={`${versionData.game_id}-${versionData.version}`} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">{versionData.game_name}</h3>
                      <p className="text-sm text-gray-600">Version: {versionData.version}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-500">
                        Released: {new Date(versionData.release_date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Bugs Introduced */}
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-red-900">Bugs Introduced</h4>
                        <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded">
                          {versionData.bugs_introduced?.length || 0}
                        </span>
                      </div>
                      {versionData.bugs_introduced?.length > 0 ? (
                        <div className="space-y-2">
                          {versionData.bugs_introduced.map((bug: any) => (
                            <div key={bug.bug_id} className="text-sm">
                              <div className="flex justify-between">
                                <span className="font-medium">{bug.bug_type}</span>
                                <span className={`px-1 py-0.5 rounded text-xs ${
                                  bug.severity === 'critical' ? 'bg-red-200 text-red-800' :
                                  bug.severity === 'high' ? 'bg-orange-200 text-orange-800' :
                                  'bg-yellow-200 text-yellow-800'
                                }`}>
                                  {bug.severity}
                                </span>
                              </div>
                              <p className="text-gray-600 text-xs">{bug.description}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No new bugs introduced</p>
                      )}
                    </div>
                    
                    {/* Bugs Resolved */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-green-900">Bugs Resolved</h4>
                        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded">
                          {versionData.bugs_resolved?.length || 0}
                        </span>
                      </div>
                      {versionData.bugs_resolved?.length > 0 ? (
                        <div className="space-y-2">
                          {versionData.bugs_resolved.map((bug: any) => (
                            <div key={bug.bug_id} className="text-sm">
                              <div className="flex justify-between">
                                <span className="font-medium">{bug.bug_type}</span>
                                <span className="text-xs text-gray-500">
                                  Fixed from v{bug.introduced_version}
                                </span>
                              </div>
                              <p className="text-gray-600 text-xs">{bug.description}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No bugs resolved</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {!bugsByVersion?.length && (
                <div className="text-center py-8 text-gray-500">
                  No version tracking data available
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}