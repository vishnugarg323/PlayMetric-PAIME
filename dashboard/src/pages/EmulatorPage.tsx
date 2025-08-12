import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  Paper,
} from '@mui/material';
import {
  PlayArrow,
  SmartToy,
  Phone,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import EmulatorViewer from '../components/EmulatorViewer';
import { api } from '../services/api';

export default function EmulatorPage() {
  const [selectedGameId, setSelectedGameId] = useState<string>('');

  const { data: games = [] } = useQuery({
    queryKey: ['games'],
    queryFn: api.getGames,
  });

  const selectedGame = games.find((game: any) => game.game_id === selectedGameId);

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          <Phone sx={{ mr: 2, verticalAlign: 'middle' }} />
          Live Game Emulator
        </Typography>
        <Typography color="text.secondary" gutterBottom>
          Watch AI play games in real-time, monitor performance, and observe gameplay mechanics.
        </Typography>
      </Box>

      {/* Game Selection */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Select Game to Test
          </Typography>
          
          <Box display="flex" gap={3} alignItems="center" flexWrap="wrap">
            <Box flex={1} minWidth="300px">
              <FormControl fullWidth>
                <InputLabel>Choose Game</InputLabel>
                <Select
                  value={selectedGameId}
                  onChange={(e) => setSelectedGameId(e.target.value)}
                  label="Choose Game"
                >
                  <MenuItem value="">
                    <em>Select a game...</em>
                  </MenuItem>
                  {games.map((game: any) => (
                    <MenuItem key={game.game_id} value={game.game_id}>
                      {game.game_name} ({game.package_name})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
            
            <Box flex={1} minWidth="300px">
              {selectedGame && (
                <Box display="flex" alignItems="center" gap={2}>
                  <SmartToy color="primary" />
                  <Box>
                    <Typography variant="body1" fontWeight="bold">
                      {selectedGame.game_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Version: {selectedGame.version} | Status: {selectedGame.status || 'Ready'}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Instructions */}
      {!selectedGameId && (
        <Alert severity="info" sx={{ mb: 4 }}>
          <Typography variant="body2">
            <strong>How to use the emulator:</strong>
          </Typography>
          <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
            <li>Select a game from the dropdown above</li>
            <li>Click "Connect Emulator" to establish connection</li>
            <li>Use "Start" to begin AI gameplay testing</li>
            <li>Monitor real-time performance metrics and AI decisions</li>
            <li>Use fullscreen mode for better visibility</li>
          </Box>
        </Alert>
      )}

      {/* Main Emulator Display */}
      {selectedGameId ? (
        <Box display="flex" gap={3} flexWrap="wrap">
          <Box flex="1 1 500px">
            <Paper elevation={3} sx={{ p: 2 }}>
              <EmulatorViewer
                gameId={selectedGameId}
                gameName={selectedGame?.game_name}
                autoStart={true}
                showControls={true}
                compact={false}
              />
            </Paper>
          </Box>
          
          <Box flex="0 0 350px" minWidth="300px">
            <Box display="flex" flexDirection="column" gap={2}>
              {/* Game Info Panel */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Game Information
                  </Typography>
                  
                  <Box mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      Package Name
                    </Typography>
                    <Typography variant="body1">
                      {selectedGame?.package_name}
                    </Typography>
                  </Box>
                  
                  <Box mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      Version
                    </Typography>
                    <Typography variant="body1">
                      {selectedGame?.version}
                    </Typography>
                  </Box>
                  
                  <Box mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      Upload Time
                    </Typography>
                    <Typography variant="body1">
                      {selectedGame?.upload_time 
                        ? new Date(selectedGame.upload_time).toLocaleString()
                        : 'N/A'
                      }
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {/* Testing Status */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Testing Status
                  </Typography>
                  
                  <Box textAlign="center" py={2}>
                    <PlayArrow sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                    <Typography variant="body1" gutterBottom>
                      AI Testing in Progress
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      The AI agent is analyzing gameplay patterns, detecting bugs, and evaluating performance metrics.
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Quick Actions
                  </Typography>
                  
                  <Box display="flex" flexDirection="column" gap={2}>
                    <Button
                      variant="outlined"
                      onClick={() => window.open(`/games/${selectedGameId}`, '_blank')}
                      fullWidth
                    >
                      View Full Game Details
                    </Button>
                    
                    <Button
                      variant="outlined"
                      onClick={() => window.open(`/analytics`, '_blank')}
                      fullWidth
                    >
                      View Analytics Dashboard
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          </Box>
        </Box>
      ) : (
        <Box textAlign="center" py={8}>
          <SmartToy sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Select a game to start emulator testing
          </Typography>
          <Typography color="text.secondary">
            Choose from the available games above to begin real-time AI testing
          </Typography>
        </Box>
      )}
    </Box>
  );
}
