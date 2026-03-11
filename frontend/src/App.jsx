import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import Login from './pages/Login';
import Upload from './pages/Upload';
import ComicGenerator from './pages/ComicGenerator';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  // Handle Google OAuth callback token
  useEffect(() => {
    // 1. Phân tích URL để tìm params 'token'
    const params = new URLSearchParams(window.location.search);
    const tokenFromUrl = params.get('token');
    
    if (tokenFromUrl) {
      // 2. Lưu vào localStorage để dùng cho các request sau
      localStorage.setItem('access_token', tokenFromUrl);
      console.log('✅ Google login success! Token saved.');
      
      // 3. CLEAN UP: Xóa token khỏi URL để link trông gọn gàng và an toàn
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // 4. TODO: Load thông tin profile user nếu cần
      // fetchUserInfo();
    }
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
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
