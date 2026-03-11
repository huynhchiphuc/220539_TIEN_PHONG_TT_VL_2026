import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import Upload from './pages/Upload';
import ComicGenerator from './pages/ComicGenerator';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
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
    <Router>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route 
              path="/upload" 
              element={
                <ProtectedRoute>
                  <Upload />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/comic" 
              element={
                <ProtectedRoute>
                  <ComicGenerator />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/profile" 
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/settings" 
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
