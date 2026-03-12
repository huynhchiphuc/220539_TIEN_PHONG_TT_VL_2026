import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from '../services/api';
import { useTheme } from '../context/ThemeContext';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isActive = (path) => location.pathname === path;
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const user = localStorage.getItem('user');
    if (token && user) {
      try {
        setUserInfo(JSON.parse(user));
        setIsLoggedIn(true);
      } catch {
        fetchUserInfo();
      }
    } else if (token) {
      fetchUserInfo();
    }
  }, []);

  useEffect(() => {
    setSidebarOpen(false);
    setShowUserMenu(false);
  }, [location.pathname]);

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/auth/me');
      setUserInfo(response.data);
      localStorage.setItem('user', JSON.stringify(response.data));
      setIsLoggedIn(true);
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      setIsLoggedIn(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setIsLoggedIn(false);
    setUserInfo(null);
    setShowUserMenu(false);
    setSidebarOpen(false);
    navigate('/');
  };

  // Close sidebar when clicking outside on mobile
  useEffect(() => {
    if (!sidebarOpen) return;
    const handleClickOutside = (e) => {
      if (!e.target.closest('.sidebar') && !e.target.closest('.sidebar-toggle')) {
        setSidebarOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [sidebarOpen]);

  const navLinks = [
    { to: '/admin', label: 'Dashboard', icon: '📊' },
    { to: '/admin/users', label: 'Quản lý Users', icon: '👥' },
    { to: '/admin/projects', label: 'Quản lý Projects', icon: '📚' },
    { to: '/admin/logs', label: 'Activity Logs', icon: '📋' },
  ];

  return (
    <>
      {/* Mobile toggle button */}
      <button 
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle sidebar"
      >
        <span className="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </span>
      </button>

      {/* Overlay for mobile */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        {/* Header Section */}
        <div className="sidebar-header">
          <Link to="/admin" className="sidebar-logo" onClick={() => setSidebarOpen(false)}>
            <span className="logo-icon">👑</span>
            <span className="logo-text">Admin Panel</span>
          </Link>
          <button
            onClick={toggleTheme}
            className="theme-toggle"
            aria-label={theme === 'dark' ? 'Chuyển sang sáng' : 'Chuyển sang tối'}
            title={theme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="sidebar-nav">
          <ul className="sidebar-menu">
            {navLinks.map(({ to, label, icon, highlight }) => (
              <li key={to}>
                <Link
                  to={to}
                  className={`sidebar-link ${isActive(to) ? 'active' : ''} ${highlight ? 'highlight' : ''}`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <span className="link-icon">{icon}</span>
                  <span className="link-text">{label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* User Section */}
        <div className="sidebar-footer">
          {isLoggedIn && userInfo ? (
            <div className="user-section">
              <button 
                className="user-profile-btn"
                onClick={() => setShowUserMenu(!showUserMenu)}
              >
                {userInfo.avatar_url ? (
                  <img src={userInfo.avatar_url} alt="Avatar" className="user-avatar" />
                ) : (
                  <div className="user-avatar-placeholder">
                    {(userInfo.username?.[0] || userInfo.email?.[0] || 'U').toUpperCase()}
                  </div>
                )}
                <div className="user-info">
                  <div className="user-name">{userInfo.username || userInfo.email?.split('@')[0]}</div>
                  <div className="user-role">{userInfo.role === 'admin' ? '👑 Admin' : '👤 User'}</div>
                </div>
                <svg className="dropdown-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                  <path d="M6 9L1 4h10z" />
                </svg>
              </button>

              {/* User dropdown menu */}
              {showUserMenu && (
                <div className="user-dropdown">
                  <Link 
                    to="/profile" 
                    className="dropdown-item"
                    onClick={() => { setShowUserMenu(false); setSidebarOpen(false); }}
                  >
                    <span>👤</span> Hồ sơ
                  </Link>
                  <Link 
                    to="/settings" 
                    className="dropdown-item"
                    onClick={() => { setShowUserMenu(false); setSidebarOpen(false); }}
                  >
                    <span>⚙️</span> Cài đặt
                  </Link>
                  <div className="dropdown-divider" />
                  <Link 
                    to="/" 
                    className="dropdown-item"
                    onClick={() => { setShowUserMenu(false); setSidebarOpen(false); }}
                  >
                    <span>🏠</span> Về trang chính
                  </Link>
                  <div className="dropdown-divider" />
                  <button onClick={handleLogout} className="dropdown-item dropdown-logout">
                    <span>🚪</span> Đăng xuất
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link 
              to="/login" 
              className="login-btn"
              onClick={() => setSidebarOpen(false)}
            >
              <span>🔐</span>
              <span>Đăng nhập</span>
            </Link>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
