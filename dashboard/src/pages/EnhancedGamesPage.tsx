import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  InputAdornment,
  Tabs,
  Tab,
  Chip,
  Button,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Search,
  CloudUpload,
  PlayArrow,
  Assessment,
  SportsEsports,
  Speed,
  Memory,
  SmartToy,
  Timeline,
  BugReport as BugReportIcon,
  Gamepad as GamepadIcon,
  AccessTime as AccessTimeIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

interface Game {
  game_id: string;
  game_name: string;
  package_name: string;
  version?: string;
  game_version?: string;
  file_path?: string;
  upload_time?: string;
  emulator_status: string;
  last_tested?: string;
  created_at: string;
  status: string;
  icon_url?: string;
  total_versions: number;
  total_sessions: number;
  total_bugs_found: number;
  bug_count: number;
  active_bugs: number;
  latest_version?: string;
  latest_version_id?: string;
  category?: string;
  difficulty_score?: number;
  analysis?: any;
}

const gameCategories = [
  { value: 'all', label: 'All Games', icon: <SportsEsports /> },
  { value: 'puzzle', label: 'Puzzle', icon: <SmartToy /> },
  { value: 'action', label: 'Action', icon: <Speed /> },
  { value: 'arcade', label: 'Arcade', icon: <Timeline /> },
  { value: 'strategy', label: 'Strategy', icon: <Assessment /> },
  { value: 'casual', label: 'Casual', icon: <SportsEsports /> },
  { value: 'racing', label: 'Racing', icon: <Speed /> },
  { value: 'adventure', label: 'Adventure', icon: <Timeline /> },
];

export default function EnhancedGamesPage() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: games = [], isLoading, refetch } = useQuery({
    queryKey: ['games'],
    queryFn: api.getGames,
  });

  // Use games data directly without mock enhancements
  const enhancedGames = games.map((game: Game) => ({
    ...game,
    category: game.category || 'casual', // Default category
    difficulty_score: game.difficulty_score || 2, // Default medium difficulty
  }));

  const filteredGames = enhancedGames.filter((game: Game) => {
    const matchesSearch = game.game_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         game.package_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || game.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadError(null);

    try {
      await api.uploadAPK(selectedFile);
      setUploadDialogOpen(false);
      setSelectedFile(null);
      refetch();
    } catch (error: any) {
      setUploadError(error.response?.data?.detail || 'Failed to upload APK');
    } finally {
      setUploading(false);
    }
  };

  const handleStartTesting = async (gameId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/games/${gameId}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ testing_type: 'automated' }),
      });
      
      if (response.ok) {
        const session = await response.json();
        console.log('Session created:', session);
        navigate(`/sessions/${session.session_id}`);
      } else {
        throw new Error('Failed to create session');
      }
    } catch (error) {
      console.error('Failed to start testing:', error);
      alert('Failed to create session. Please try again.');
    }
  };

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

  const getCategoryStats = () => {
    const stats: { [key: string]: number } = {};
    enhancedGames.forEach((game: Game) => {
      stats[game.category!] = (stats[game.category!] || 0) + 1;
    });
    return stats;
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="80vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Game Library</Typography>
        <Button
          variant="contained"
          startIcon={<CloudUpload />}
          onClick={() => setUploadDialogOpen(true)}
        >
          Upload APK
        </Button>
      </Box>

      {/* Category Overview */}
      <Box display="flex" flexWrap="wrap" gap={2} mb={3}>
        {gameCategories.slice(1).map((category) => {
          const count = getCategoryStats()[category.value] || 0;
          return (
            <Box key={category.value} sx={{ minWidth: 150, flex: '1 1 150px' }}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { transform: 'translateY(-2px)', boxShadow: 3 }
                }}
                onClick={() => setSelectedCategory(category.value)}
              >
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Box color="primary.main" mb={1}>
                    {category.icon}
                  </Box>
                  <Typography variant="h6">{count}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {category.label}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          );
        })}
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" flexDirection={{ xs: 'column', md: 'row' }} gap={2} alignItems="center">
            <Box flex={1} minWidth={250}>
              <TextField
                fullWidth
                placeholder="Search games..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Box>
            
            <Box flex={1} minWidth={300}>
              <Tabs
                value={selectedCategory}
                onChange={(_, newValue) => setSelectedCategory(newValue)}
                variant="scrollable"
                scrollButtons="auto"
              >
                {gameCategories.map((category) => (
                  <Tab
                    key={category.value}
                    label={category.label}
                    value={category.value}
                    icon={category.icon}
                    iconPosition="start"
                  />
                ))}
              </Tabs>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Games Grid */}
      <Box display="grid" gridTemplateColumns="repeat(auto-fill, minmax(300px, 1fr))" gap={3}>
        {filteredGames.map((game: Game) => (
          <Card 
            key={game.game_id}
            sx={{ 
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              transition: 'all 0.2s',
              '&:hover': { transform: 'translateY(-2px)', boxShadow: 3 }
            }}
          >
              <CardContent sx={{ flexGrow: 1 }}>
                {/* Game Header */}
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Box flexGrow={1}>
                    <Typography variant="h6" noWrap title={game.game_name}>
                      {game.game_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {game.package_name}
                    </Typography>
                    {(game.version || game.game_version) && (
                      <Typography variant="caption" color="primary" display="block">
                        Version: {game.version || game.game_version}
                      </Typography>
                    )}
                  </Box>
                </Box>

                {/* Category & Status */}
                <Box display="flex" gap={1} mb={2} flexWrap="wrap">
                  <Chip 
                    label={game.category}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  <Chip 
                    label={game.status}
                    size="small"
                    color={game.status === 'active' ? 'success' : 'default'}
                  />
                </Box>

                {/* Difficulty */}
                <Box mb={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body2">Difficulty</Typography>
                    <Chip 
                      label={getDifficultyLabel(game.difficulty_score!)}
                      size="small"
                      color={getDifficultyColor(game.difficulty_score!)}
                    />
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={(game.difficulty_score! / 5) * 100}
                    color={getDifficultyColor(game.difficulty_score!)}
                    sx={{ height: 6, borderRadius: 1 }}
                  />
                </Box>

                {/* Game Statistics */}
                <Box 
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 2,
                    mb: 2
                  }}
                >
                  <Box>
                    <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                      <BugReportIcon color="error" sx={{ fontSize: 16 }} />
                      <Typography variant="caption" color="text.secondary">
                        Total Bugs
                      </Typography>
                    </Box>
                    <Typography variant="h6" color="error">
                      {game.total_bugs_found || game.bug_count || game.active_bugs || 0}
                    </Typography>
                  </Box>
                  
                  <Box>
                    <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                      <GamepadIcon color="primary" sx={{ fontSize: 16 }} />
                      <Typography variant="caption" color="text.secondary">
                        Sessions
                      </Typography>
                    </Box>
                    <Typography variant="h6" color="primary">
                      {game.total_sessions || 0}
                    </Typography>
                  </Box>
                </Box>

                {/* Last Tested */}
                <Box display="flex" alignItems="center" gap={0.5} mb={2}>
                  <AccessTimeIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary">
                    Last tested: {game.last_tested ? new Date(game.last_tested).toLocaleString() : 'Never'}
                  </Typography>
                </Box>

                {/* Performance Indicators */}
                <Box mt={2} display="flex" gap={1} justifyContent="center">
                  <Chip 
                    icon={<Memory />}
                    label={`${game.analysis?.memory_usage || 120}MB`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip 
                    icon={<Speed />}
                    label={`${game.analysis?.cpu_usage || 15}%`}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </CardContent>

              {/* Actions */}
              <Box p={2} pt={0} display="flex" gap={1}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<PlayArrow />}
                  onClick={() => handleStartTesting(game.game_id)}
                  sx={{ flexGrow: 2 }}
                >
                  Create Session
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate(`/games/${game.game_id}`)}
                  sx={{ flexGrow: 1 }}
                >
                  Details
                </Button>
              </Box>
            </Card>
        ))}
      </Box>

      {filteredGames.length === 0 && (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No games found
          </Typography>
          <Typography color="text.secondary">
            Try adjusting your search or category filter
          </Typography>
        </Box>
      )}

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload New Game APK</DialogTitle>
        <DialogContent>
          {uploadError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {uploadError}
            </Alert>
          )}
          
          <Box
            sx={{
              border: '2px dashed #ccc',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': { borderColor: 'primary.main' }
            }}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".apk"
              style={{ display: 'none' }}
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            />
            
            <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              {selectedFile ? selectedFile.name : 'Click to select APK file'}
            </Typography>
            <Typography color="text.secondary">
              Supported format: .apk files only
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleUpload} 
            variant="contained" 
            disabled={!selectedFile || uploading}
          >
            {uploading ? <CircularProgress size={20} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}


