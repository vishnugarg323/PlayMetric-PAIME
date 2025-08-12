import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  IconButton,
  Paper,
  Alert,
  Dialog,
  DialogContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  Fullscreen,
  FullscreenExit,
  SmartToy,
  Memory,
  Speed,
  Phone,
  Visibility,
} from '@mui/icons-material';

interface EmulatorState {
  image: string;
  game_state: {
    phase: string;
    score: number;
    level: number;
    game_running: boolean;
    performance_metrics: {
      fps: number;
      memory_usage: number;
      cpu_usage: number;
    };
  } | null;
  timestamp: string;
}

interface EmulatorViewerProps {
  gameId?: string;
  gameName?: string;
  autoStart?: boolean;
  showControls?: boolean;
  compact?: boolean;
}

export default function EmulatorViewer({
  gameId,
  gameName,
  autoStart = false,
  showControls = true,
  compact = false
}: EmulatorViewerProps) {
  const [emulatorState, setEmulatorState] = useState<EmulatorState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [emulatorQuality, setEmulatorQuality] = useState<'high' | 'medium' | 'low'>('high');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connectToEmulator = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket('ws://localhost:5555/ws');
      
      ws.onopen = () => {
        console.log('Connected to emulator');
        setIsConnected(true);
        
        if (gameId) {
          ws.send(JSON.stringify({
            type: 'load_game',
            game_id: gameId,
            quality: emulatorQuality
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'game_update') {
            setEmulatorState({
              image: data.image,
              game_state: data.game_state,
              timestamp: data.timestamp
            });
          } else if (data.type === 'live_screenshot') {
            setEmulatorState((prev) => prev ? {
              ...prev,
              image: data.screenshot
            } : {
              image: data.screenshot,
              game_state: null,
              timestamp: ''
            });
          }
        } catch (error) {
          console.error('Error parsing emulator data:', error);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from emulator');
        setIsConnected(false);
        wsRef.current = null;
        
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connectToEmulator();
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('Emulator connection error:', error);
        setIsConnected(false);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect to emulator:', error);
      setIsConnected(false);
    }
  };

  const disconnectFromEmulator = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setEmulatorState(null);
  };

  const sendEmulatorCommand = (command: string, data?: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: command,
        ...data
      }));
    }
  };

  const startGame = () => {
    sendEmulatorCommand('start_game', { game_id: gameId });
  };

  const stopGame = () => {
    sendEmulatorCommand('stop_game');
  };

  const restartGame = () => {
    sendEmulatorCommand('restart_game');
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  useEffect(() => {
    if (autoStart) {
      connectToEmulator();
    }

    return () => {
      disconnectFromEmulator();
    };
  }, [autoStart, gameId]);

  useEffect(() => {
    if (isConnected && emulatorQuality) {
      sendEmulatorCommand('set_quality', { quality: emulatorQuality });
    }
  }, [emulatorQuality, isConnected]);

  const EmulatorScreen = () => (
    <Paper
      elevation={3}
      sx={{
        position: 'relative',
        background: '#000',
        borderRadius: 2,
        overflow: 'hidden',
        aspectRatio: '9/16',
        maxWidth: compact ? 300 : 400,
        mx: 'auto'
      }}
    >
      {emulatorState?.image ? (
        <Box
          component="img"
          src={`data:image/png;base64,${emulatorState.image}`}
          alt="Emulator Screen"
          sx={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            display: 'block'
          }}
        />
      ) : (
        <Box
          display="flex"
          alignItems="center"
          justifyContent="center"
          height="100%"
          flexDirection="column"
          color="white"
        >
          <Phone sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
          <Typography variant="h6" color="inherit">
            {isConnected ? 'Waiting for game...' : 'Emulator Disconnected'}
          </Typography>
          <Typography variant="body2" color="inherit" sx={{ opacity: 0.7, mt: 1 }}>
            {isConnected ? 'Starting emulator...' : 'Click connect to start'}
          </Typography>
        </Box>
      )}

      {/* Connection Status Indicator */}
      <Chip
        label={isConnected ? 'Connected' : 'Disconnected'}
        color={isConnected ? 'success' : 'error'}
        size="small"
        sx={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 1
        }}
      />

      {/* Fullscreen Button */}
      {showControls && (
        <IconButton
          onClick={toggleFullscreen}
          sx={{
            position: 'absolute',
            bottom: 8,
            right: 8,
            color: 'white',
            bgcolor: 'rgba(0,0,0,0.5)',
            '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' }
          }}
        >
          {isFullscreen ? <FullscreenExit /> : <Fullscreen />}
        </IconButton>
      )}
    </Paper>
  );

  const GameStats = () => (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Live Game Stats
        </Typography>
        
        {emulatorState?.game_state && (
          <Box>
            <Box display="flex" justifyContent="space-around" mb={2}>
              <Box textAlign="center">
                <Typography variant="h5" color="primary">
                  {emulatorState.game_state.score}
                </Typography>
                <Typography variant="caption">Score</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="h5" color="secondary">
                  {emulatorState.game_state.level}
                </Typography>
                <Typography variant="caption">Level</Typography>
              </Box>
            </Box>
            
            <Box mb={2}>
              <Typography variant="body2" gutterBottom>
                Phase: <Chip label={emulatorState.game_state.phase} size="small" />
              </Typography>
            </Box>

            {emulatorState.game_state.performance_metrics && (
              <Box display="flex" justifyContent="space-around" mt={2}>
                <Box textAlign="center">
                  <Memory color="action" />
                  <Typography variant="caption" display="block">
                    {emulatorState.game_state.performance_metrics.memory_usage}MB
                  </Typography>
                </Box>
                <Box textAlign="center">
                  <Speed color="action" />
                  <Typography variant="caption" display="block">
                    {emulatorState.game_state.performance_metrics.cpu_usage}%
                  </Typography>
                </Box>
                <Box textAlign="center">
                  <Typography variant="h6">
                    {emulatorState.game_state.performance_metrics.fps}
                  </Typography>
                  <Typography variant="caption">FPS</Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );

  if (isFullscreen) {
    return (
      <Dialog
        open={isFullscreen}
        onClose={toggleFullscreen}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: 'black',
            maxHeight: '90vh'
          }
        }}
      >
        <DialogContent sx={{ p: 2 }}>
          <Box position="relative">
            <EmulatorScreen />
            <IconButton
              onClick={toggleFullscreen}
              sx={{
                position: 'absolute',
                top: 8,
                right: 8,
                color: 'white',
                bgcolor: 'rgba(0,0,0,0.5)',
                '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' }
              }}
            >
              <FullscreenExit />
            </IconButton>
          </Box>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Box>
      {/* Connection Alert */}
      {!isConnected && (
        <Alert 
          severity="warning" 
          sx={{ mb: 2 }}
          action={
            <Button onClick={connectToEmulator} size="small">
              Connect
            </Button>
          }
        >
          Emulator not connected. Make sure the emulator service is running on port 5555.
        </Alert>
      )}

      {/* Game Header */}
      {gameName && (
        <Typography variant="h6" gutterBottom>
          <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
          {gameName} - Live Emulator
        </Typography>
      )}

      {/* Emulator Screen */}
      <EmulatorScreen />

      {/* Control Panel */}
      {showControls && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Box display="flex" flexDirection="column" gap={2}>
              <Box display="flex" gap={1} justifyContent="center">
                {!isConnected ? (
                  <Button
                    variant="contained"
                    onClick={connectToEmulator}
                    startIcon={<Visibility />}
                  >
                    Connect Emulator
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      onClick={startGame}
                      startIcon={<PlayArrow />}
                      disabled={!gameId}
                    >
                      Start
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={stopGame}
                      startIcon={<Stop />}
                    >
                      Stop
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={restartGame}
                      startIcon={<Refresh />}
                    >
                      Restart
                    </Button>
                  </>
                )}
              </Box>
              
              <Box display="flex" justifyContent="center">
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Quality</InputLabel>
                  <Select
                    value={emulatorQuality}
                    onChange={(e) => setEmulatorQuality(e.target.value as any)}
                    label="Quality"
                  >
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Live Stats */}
      {!compact && emulatorState && <GameStats />}
    </Box>
  );
}
