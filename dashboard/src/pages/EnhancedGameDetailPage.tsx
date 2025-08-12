import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Tabs,
  Tab,
  Paper,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  SmartToy,
  Memory,
  Speed,
  BugReport,
  Timeline,
  Assessment
} from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import EmulatorViewer from '../components/EmulatorViewer';

interface GameAnalysis {
  session_id: string;
  category_primary: string;
  category_secondary: string[];
  difficulty_score: number;
  mechanics: string[];
  levels_discovered: any[];
  performance_summary: any;
}

interface EmulatorStream {
  image: string;
  game_state: any;
  timestamp: string;
}

export default function EnhancedGameDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState(0);
  const [isTestingActive, setIsTestingActive] = useState(false);
  const [emulatorStream, setEmulatorStream] = useState<EmulatorStream | null>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  // Fetch game data
  const { data: game, isLoading: gameLoading } = useQuery({
    queryKey: ['game', id],
    queryFn: () => api.getGame(id!),
    enabled: !!id,
  });

  const { data: sessions } = useQuery({
    queryKey: ['game-sessions', id],
    queryFn: () => api.getGameSessions(id!),
    enabled: !!id,
  });

  const { data: analysis } = useQuery<GameAnalysis>({
    queryKey: ['game-analysis', id],
    queryFn: () => api.getGameAnalysis(id!),
    enabled: !!id,
  });

  const { data: bugs } = useQuery({
    queryKey: ['game-bugs', id],
    queryFn: () => api.getGameBugs(id!),
    enabled: !!id,
  });

  // WebSocket connection for real-time emulator streaming
  useEffect(() => {
    if (isTestingActive && !wsConnection) {
      const ws = new WebSocket(`ws://localhost:5555/ws`);
      
      ws.onopen = () => {
        console.log('Connected to emulator stream');
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'game_update') {
            setEmulatorStream({
              image: data.screenshot,
              game_state: data.game_state,
              timestamp: data.timestamp
            });
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from emulator stream');
        setWsConnection(null);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      return () => {
        ws.close();
      };
    }
  }, [isTestingActive, wsConnection]);

  const startTesting = async () => {
    try {
      await api.startGameTesting(id!);
      setIsTestingActive(true);
    } catch (error) {
      console.error('Error starting test:', error);
    }
  };

  const stopTesting = async () => {
    try {
      await api.stopGameTesting(id!);
      setIsTestingActive(false);
      if (wsConnection) {
        wsConnection.close();
        setWsConnection(null);
      }
    } catch (error) {
      console.error('Error stopping test:', error);
    }
  };

  if (gameLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="80vh">
        <Typography>Loading game details...</Typography>
      </Box>
    );
  }

  if (!game) {
    return (
      <Box p={3}>
        <Alert severity="error">Game not found</Alert>
      </Box>
    );
  }

  const getDifficultyColor = (score: number) => {
    if (score < 1.5) return 'success';
    if (score < 2.5) return 'warning';
    if (score < 3.5) return 'error';
    return 'error';
  };

  const getDifficultyLabel = (score: number) => {
    if (score < 1.5) return 'Easy';
    if (score < 2.5) return 'Medium';
    if (score < 3.5) return 'Hard';
    return 'Extreme';
  };

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            {game.game_name}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {game.package_name}
          </Typography>
        </Box>
        
        <Box display="flex" gap={2}>
          {!isTestingActive ? (
            <IconButton
              color="primary"
              onClick={startTesting}
              size="large"
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                '&:hover': { bgcolor: 'primary.dark' }
              }}
            >
              <PlayArrow />
            </IconButton>
          ) : (
            <IconButton
              color="error"
              onClick={stopTesting}
              size="large"
              sx={{
                bgcolor: 'error.main',
                color: 'white',
                '&:hover': { bgcolor: 'error.dark' }
              }}
            >
              <Stop />
            </IconButton>
          )}
          
          <IconButton onClick={() => window.location.reload()}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Real-time Emulator View */}
      {isTestingActive && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Live Emulator View
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'row', gap: 3, flexWrap: 'wrap' }}>
              <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
                <Box
                  sx={{
                    border: '2px solid #ddd',
                    borderRadius: 2,
                    overflow: 'hidden',
                    bgcolor: '#000',
                    aspectRatio: '9/16',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {emulatorStream?.image ? (
                    <img
                      src={`data:image/jpeg;base64,${emulatorStream.image}`}
                      alt="Live emulator view"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '100%',
                        objectFit: 'contain'
                      }}
                    />
                  ) : (
                    <Typography color="white">
                      Waiting for emulator stream...
                    </Typography>
                  )}
                </Box>
              </Box>
              
              <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
                <Typography variant="h6" gutterBottom>
                  Live Game State
                </Typography>
                
                {emulatorStream?.game_state && (
                  <Box sx={{ display: 'flex', flexDirection: 'row', gap: 2, flexWrap: 'wrap' }}>
                    <Box sx={{ flex: '1 1 150px' }}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" color="primary">
                          {emulatorStream.game_state.score}
                        </Typography>
                        <Typography variant="caption">Score</Typography>
                      </Paper>
                    </Box>
                    
                    <Box sx={{ flex: '1 1 150px' }}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" color="secondary">
                          {emulatorStream.game_state.level}
                        </Typography>
                        <Typography variant="caption">Level</Typography>
                      </Paper>
                    </Box>
                    
                    <Box sx={{ flex: '1 1 100%' }}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Game Phase
                        </Typography>
                        <Chip 
                          label={emulatorStream.game_state.phase} 
                          color={emulatorStream.game_state.phase === 'gameplay' ? 'success' : 'default'}
                        />
                      </Paper>
                    </Box>
                    
                    <Box sx={{ flex: '1 1 100%' }}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Performance
                        </Typography>
                        <Box display="flex" gap={1} flexWrap="wrap">
                          <Chip 
                            icon={<Memory />}
                            label={`${(emulatorStream.game_state.performance_metrics?.memory_usage / 1024 / 1024).toFixed(1)}MB`}
                            size="small"
                          />
                          <Chip 
                            icon={<Speed />}
                            label={`${emulatorStream.game_state.performance_metrics?.cpu_usage?.toFixed(1)}% CPU`}
                            size="small"
                          />
                        </Box>
                      </Paper>
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Overview" />
          <Tab label="Live Emulator" />
          <Tab label="Game Analysis" />
          <Tab label="Testing Sessions" />
          <Tab label="Bug Reports" />
          <Tab label="D1 Retention" />
          <Tab label="D7 Retention" />
          <Tab label="Churn Analysis" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'row', gap: 3, flexWrap: 'wrap' }}>
          {/* Game Category & Difficulty */}
          <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <SmartToy color="primary" />
                  <Typography variant="h6">Game Classification</Typography>
                </Box>
                
                {analysis && (
                  <Box>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="subtitle2">Category:</Typography>
                      <Chip 
                        label={analysis.category_primary}
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                    
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="subtitle2">Difficulty:</Typography>
                      <Chip 
                        label={getDifficultyLabel(analysis.difficulty_score)}
                        color={getDifficultyColor(analysis.difficulty_score)}
                      />
                    </Box>
                    
                    <Box mb={2}>
                      <Typography variant="subtitle2" gutterBottom>
                        Difficulty Score: {analysis.difficulty_score.toFixed(1)}/5.0
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={(analysis.difficulty_score / 5) * 100}
                        color={getDifficultyColor(analysis.difficulty_score)}
                      />
                    </Box>
                    
                    {analysis.mechanics && analysis.mechanics.length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Game Mechanics:
                        </Typography>
                        <Box display="flex" gap={1} flexWrap="wrap">
                          {analysis.mechanics.map((mechanic: string, index: number) => (
                            <Chip 
                              key={index}
                              label={mechanic}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </Box>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>

          {/* Level Progress */}
          <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <Timeline color="primary" />
                  <Typography variant="h6">Level Discovery</Typography>
                </Box>
                
                {analysis?.levels_discovered && analysis.levels_discovered.length > 0 ? (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Levels Discovered: {analysis.levels_discovered.length}
                    </Typography>
                    
                    <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                      {analysis.levels_discovered.map((level: any, index: number) => (
                        <Box 
                          key={index}
                          display="flex" 
                          justifyContent="space-between" 
                          alignItems="center"
                          py={1}
                          borderBottom={index < analysis.levels_discovered.length - 1 ? '1px solid #eee' : 'none'}
                        >
                          <Typography variant="body2">
                            Level {level.level_number}
                          </Typography>
                          <Chip 
                            label={getDifficultyLabel(level.difficulty_score)}
                            size="small"
                            color={getDifficultyColor(level.difficulty_score)}
                          />
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ) : (
                  <Typography color="text.secondary">
                    No levels discovered yet. Start testing to explore the game!
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Box>

          {/* Bug Summary */}
          <Box sx={{ flex: '1 1 100%', width: '100%' }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <BugReport color="error" />
                  <Typography variant="h6">Bug Summary</Typography>
                </Box>
                
                {bugs && bugs.length > 0 ? (
                  <Box sx={{ display: 'flex', flexDirection: 'row', gap: 2, flexWrap: 'wrap' }}>
                    {['critical', 'high', 'medium', 'low'].map((severity) => {
                      const count = bugs.filter((bug: any) => bug.severity === severity).length;
                      return (
                        <Box sx={{ flex: '1 1 150px' }} key={severity}>
                          <Paper sx={{ p: 2, textAlign: 'center' }}>
                            <Typography variant="h4" color={
                              severity === 'critical' ? 'error.main' :
                              severity === 'high' ? 'warning.main' :
                              severity === 'medium' ? 'info.main' : 'success.main'
                            }>
                              {count}
                            </Typography>
                            <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                              {severity}
                            </Typography>
                          </Paper>
                        </Box>
                      );
                    })}
                  </Box>
                ) : (
                  <Typography color="text.secondary">
                    No bugs found yet.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Box>
        </Box>
      )}

      {/* Live Emulator Tab */}
      {activeTab === 1 && (
        <Box>
          <EmulatorViewer
            gameId={id}
            gameName={game?.game_name}
            autoStart={true}
            showControls={true}
            compact={false}
          />
        </Box>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Detailed Game Analysis
            </Typography>
            
            {analysis ? (
              <Box sx={{ display: 'flex', flexDirection: 'row', gap: 3, flexWrap: 'wrap' }}>
                <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Game Categories
                    </Typography>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Primary:</Typography>
                      <Chip label={analysis.category_primary} color="primary" />
                    </Box>
                    {analysis.category_secondary && analysis.category_secondary.length > 0 && (
                      <Box>
                        <Typography variant="body2" color="text.secondary">Secondary:</Typography>
                        <Box display="flex" gap={1} flexWrap="wrap" mt={1}>
                          {analysis.category_secondary.map((cat: string, index: number) => (
                            <Chip key={index} label={cat} variant="outlined" size="small" />
                          ))}
                        </Box>
                      </Box>
                    )}
                  </Paper>
                </Box>
                
                <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Performance Impact
                    </Typography>
                    {analysis.performance_summary && (
                      <Box>
                        <Typography variant="body2">
                          Memory Category: {analysis.performance_summary.memory_category || 'Unknown'}
                        </Typography>
                        <Typography variant="body2">
                          Memory Usage: {analysis.performance_summary.memory_usage_mb?.toFixed(1) || 'N/A'} MB
                        </Typography>
                      </Box>
                    )}
                  </Paper>
                </Box>
              </Box>
            ) : (
              <Typography color="text.secondary">
                No analysis data available. Start testing to generate analysis.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Testing Sessions
            </Typography>
            
            {sessions && sessions.length > 0 ? (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Session ID</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Start Time</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Max Level</TableCell>
                      <TableCell>Bugs Found</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sessions.map((session: any) => (
                      <TableRow key={session.session_id}>
                        <TableCell>{session.session_id.slice(0, 8)}...</TableCell>
                        <TableCell>
                          <Chip 
                            label={session.status}
                            color={session.status === 'completed' ? 'success' : 
                                   session.status === 'failed' ? 'error' : 'default'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {new Date(session.start_time).toLocaleString()}
                        </TableCell>
                        <TableCell>{session.duration || 'N/A'}</TableCell>
                        <TableCell>{session.max_level_reached || 'N/A'}</TableCell>
                        <TableCell>{session.total_bugs_found || 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography color="text.secondary">
                No testing sessions found.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 4 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Bug Reports
            </Typography>
            
            {bugs && bugs.length > 0 ? (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Session</TableCell>
                      <TableCell>Timestamp</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {bugs.map((bug: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell>
                          <Chip label={bug.bug_type} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={bug.severity}
                            color={
                              bug.severity === 'critical' ? 'error' :
                              bug.severity === 'high' ? 'warning' :
                              bug.severity === 'medium' ? 'info' : 'success'
                            }
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{bug.description}</TableCell>
                        <TableCell>{bug.session_id?.slice(0, 8)}...</TableCell>
                        <TableCell>
                          {new Date(bug.timestamp).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography color="text.secondary">
                No bugs found.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {/* Placeholder tabs for retention and churn analysis */}
      {(activeTab === 5 || activeTab === 6 || activeTab === 7) && (
        <Card>
          <CardContent>
            <Box textAlign="center" py={4}>
              <Assessment sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {activeTab === 5 ? 'D1 Retention Analysis' :
                 activeTab === 6 ? 'D7 Retention Analysis' : 'Churn Analysis'}
              </Typography>
              <Typography color="text.secondary">
                This feature will be available once we have sufficient user data.
                For now, focus on game testing and bug detection.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
