import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './layouts/AdminLayout';
import Home from './pages/Home';
import Login from './pages/Login';
import Upload from './pages/Upload';
import ComicGenerator from './pages/ComicGenerator';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminProjects from './pages/AdminProjects';
import AdminLogs from './pages/AdminLogs';
import './App.css';

function App() {
  // Handle Google OAuth callback one-time code
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const codeFromUrl = params.get('code');
    
    if (!codeFromUrl) {
      return;
    }

    const exchangeCode = async () => {
      try {
        const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
        const response = await fetch(`${apiBase}/auth/oauth/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: codeFromUrl }),
        });

        if (!response.ok) {
          throw new Error('OAuth exchange failed');
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('token', data.access_token);
      } catch (error) {
        console.error('OAuth exchange error:', error);
      } finally {
        // Always clean URL, kể cả khi exchange lỗi.
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    };

    exchangeCode();
  }, []);

  return (
    <ThemeProvider>
      <Router>
        <div className="app">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
              <Route path="/comic" element={<ProtectedRoute><ComicGenerator /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              
              {/* Admin Routes with AdminLayout (Sidebar inside content) */}
              <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="projects" element={<AdminProjects />} />
                <Route path="logs" element={<AdminLogs />} />
              </Route>
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
