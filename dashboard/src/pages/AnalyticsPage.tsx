import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';
import BugReportIcon from '@mui/icons-material/BugReport';
import GamepadIcon from '@mui/icons-material/Gamepad';
import SpeedIcon from '@mui/icons-material/Speed';
import MemoryIcon from '@mui/icons-material/Memory';

interface AnalyticsData {
  bugsByType: { name: string; value: number }[];
  bugsBySeverity: { name: string; value: number }[];
  sessionsOverTime: { date: string; count: number }[];
  performanceMetrics: {
    avgFps: number;
    avgCpuUsage: number;
    avgMemoryUsage: number;
  };
  summary: {
    totalBugs: number;
    totalSessions: number;
    activeGames: number;
  };
}

interface Game {
  game_id: string;
  game_name: string;
  version?: string;
  game_version?: string;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedGame, setSelectedGame] = useState<string>('all');
  const [selectedVersion, setSelectedVersion] = useState<string>('all');

  // Fetch games for filtering
  const { data: games } = useQuery<Game[]>({
    queryKey: ['games'],
    queryFn: api.getGames,
  });

  // Get unique versions for selected game
  const getVersionsForGame = (gameId: string) => {
    if (!games || gameId === 'all') return [];
    return games
      .filter(game => game.game_id === gameId)
      .map(game => game.version || game.game_version)
      .filter(Boolean)
      .filter((version, index, self) => self.indexOf(version) === index); // Remove duplicates
  };

  const handleGameChange = (event: SelectChangeEvent<string>) => {
    setSelectedGame(event.target.value);
    setSelectedVersion('all'); // Reset version when game changes
  };

  const handleVersionChange = (event: SelectChangeEvent<string>) => {
    setSelectedVersion(event.target.value);
  };

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        // Build query parameters for filtering
        const params = new URLSearchParams();
        if (selectedGame !== 'all') {
          params.append('game_id', selectedGame);
        }
        if (selectedVersion !== 'all') {
          params.append('version', selectedVersion);
        }

        const response = await fetch(`/api/analytics?${params.toString()}`);
        const analyticsData = await response.json();
        setData(analyticsData);
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    // Refresh data every 5 minutes
    const interval = setInterval(fetchAnalytics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [selectedGame, selectedVersion]); // Re-fetch when filters change

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Analytics Dashboard
      </Typography>

      {/* Filter Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Filters
        </Typography>
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: {
            xs: '1fr',
            sm: '1fr 1fr',
            md: '300px 300px'
          },
          gap: 2
        }}>
          <FormControl fullWidth>
            <InputLabel id="game-select-label">Game</InputLabel>
            <Select
              labelId="game-select-label"
              value={selectedGame}
              label="Game"
              onChange={handleGameChange}
            >
              <MenuItem value="all">All Games</MenuItem>
              {games?.map((game) => (
                <MenuItem key={game.game_id} value={game.game_id}>
                  {game.game_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth disabled={selectedGame === 'all'}>
            <InputLabel id="version-select-label">Version</InputLabel>
            <Select
              labelId="version-select-label"
              value={selectedVersion}
              label="Version"
              onChange={handleVersionChange}
            >
              <MenuItem value="all">All Versions</MenuItem>
              {getVersionsForGame(selectedGame).map((version) => (
                <MenuItem key={version} value={version}>
                  {version}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Summary Cards */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: {
          xs: '1fr',
          sm: '1fr 1fr',
          md: 'repeat(4, 1fr)'
        },
        gap: 3,
        mb: 3
      }}>
        <Card sx={{ bgcolor: '#e3f2fd' }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <BugReportIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Total Bugs</Typography>
            </Box>
            <Typography variant="h4">{data?.summary.totalBugs}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ bgcolor: '#e8f5e9' }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <GamepadIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Active Games</Typography>
            </Box>
            <Typography variant="h4">{data?.summary.activeGames}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ bgcolor: '#fff3e0' }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <SpeedIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Avg FPS</Typography>
            </Box>
            <Typography variant="h4">{data?.performanceMetrics.avgFps}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ bgcolor: '#fce4ec' }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <MemoryIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Memory Usage</Typography>
            </Box>
            <Typography variant="h4">{data?.performanceMetrics.avgMemoryUsage}MB</Typography>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          md: '1fr 1fr'
        },
        gap: 3
      }}>
        {/* Bugs by Type Chart */}
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Bugs by Type
          </Typography>
            <Box height={300}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data?.bugsByType}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Paper>

        {/* Bug Severity Distribution Chart */}
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Bug Severity Distribution
          </Typography>
          <Box height={300} display="flex" justifyContent="center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data?.bugsBySeverity}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {data?.bugsBySeverity.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        </Paper>
      </Box>

      {/* Sessions Over Time Chart */}
      <Box sx={{ mt: 3 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Testing Sessions Over Time
          </Typography>
          <Box height={300}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data?.sessionsOverTime}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date"
                  tickFormatter={(date) => new Date(date).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => new Date(date).toLocaleString()}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#82ca9d" 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </Paper>
      </Box>
    </Box>
  )
}