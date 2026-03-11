import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import axios from 'axios';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUserInfo(token);
    }
  }, []);

  const fetchUserInfo = async (token) => {
    try {
      const response = await axios.get('http://localhost:60074/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUserInfo(response.data);
      setIsLoggedIn(true);
    } catch (error) {
      console.error('Failed to fetch user info:', error);
      // Token invalid, clear it
      localStorage.removeItem('access_token');
      setIsLoggedIn(false);
    }
  };

  const handleGoogleLogin = () => {
    // Redirect to backend Google login endpoint
    window.location.href = 'http://localhost:60074/api/v1/auth/google/login';
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setIsLoggedIn(false);
    setUserInfo(null);
    setShowDropdown(false);
    window.location.href = '/';
  };

  const toggleDropdown = () => {
    setShowDropdown(!showDropdown);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showDropdown && !event.target.closest('.user-menu')) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showDropdown]);

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          📚 TiênPhong AI
        </Link>
        <ul className="navbar-menu">
          <li className="navbar-item">
            <Link to="/" className={`navbar-link${isActive('/') ? ' active' : ''}`}>
              Trang chủ
            </Link>
          </li>
          <li className="navbar-item">
            <Link to="/comic" className={`navbar-link navbar-link-highlight${isActive('/comic') ? ' active' : ''}`}>
              🎨 Comic Generator
            </Link>
          </li>
          <li className="navbar-item">
            <Link to="/upload" className={`navbar-link${isActive('/upload') ? ' active' : ''}`}>
              Upload File
            </Link>
          </li>
          <li className="navbar-item navbar-auth">
            {isLoggedIn && userInfo ? (
              <div className="user-menu">
                <button onClick={toggleDropdown} className="user-menu-btn">
                  {userInfo.avatar_url ? (
                    <img src={userInfo.avatar_url} alt="Avatar" className="user-avatar" />
                  ) : (
                    <div className="user-avatar-placeholder">
                      {userInfo.username?.[0]?.toUpperCase() || userInfo.email?.[0]?.toUpperCase() || 'U'}
                    </div>
                  )}
                  <span className="user-name">{userInfo.username || userInfo.email?.split('@')[0]}</span>
                  <svg className="dropdown-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M6 9L1 4h10z"/>
                  </svg>
                </button>
                {showDropdown && (
                  <div className="user-dropdown">
                    <div className="user-dropdown-header">
                      <div className="user-dropdown-email">{userInfo.email}</div>
                      <div className="user-dropdown-id">ID: {userInfo.id}</div>
                    </div>
                    <div className="user-dropdown-divider"></div>
                    <Link to="/profile" className="user-dropdown-item" onClick={() => setShowDropdown(false)}>
                      <span>👤</span> Hồ sơ
                    </Link>
                    <Link to="/settings" className="user-dropdown-item" onClick={() => setShowDropdown(false)}>
                      <span>⚙️</span> Cài đặt
                    </Link>
                    <div className="user-dropdown-divider"></div>
                    <button onClick={handleLogout} className="user-dropdown-item user-dropdown-logout">
                      <span>🚪</span> Đăng xuất
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button onClick={handleGoogleLogin} className="navbar-btn navbar-btn-google">
                <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"></path>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"></path>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"></path>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"></path>
                </svg>
                Google Login
              </button>
            )}
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
