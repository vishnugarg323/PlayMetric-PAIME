import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import EnhancedGamesPage from './pages/EnhancedGamesPage';
import EnhancedGameDetailPage from './pages/EnhancedGameDetailPage';
import EmulatorPage from './pages/EmulatorPage';
import SessionsPage from './pages/SessionsPage';
import SessionDetailPage from './pages/SessionDetailPage';
import BugsPage from './pages/BugsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import TestPage from './pages/TestPage';
import { theme } from './theme/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/games" element={<EnhancedGamesPage />} />
              <Route path="/games/:id" element={<EnhancedGameDetailPage />} />
              <Route path="/emulator" element={<EmulatorPage />} />
              <Route path="/sessions" element={<SessionsPage />} />
              <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
              <Route path="/bugs" element={<BugsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/test" element={<TestPage />} />
            </Routes>
          </Layout>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
