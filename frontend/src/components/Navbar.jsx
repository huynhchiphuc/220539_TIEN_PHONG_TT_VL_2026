import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from '../services/api';
import { useTheme } from '../context/ThemeContext';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/auth/me');
      setUserInfo(response.data);
      localStorage.setItem('user', JSON.stringify(response.data));
    } catch (err) {
      if (err.response && err.response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setIsLoggedIn(false);
      }
    }
  };

  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        setIsLoggedIn(true);
        // Load cached user instantly to prevent empty flash
        const cachedUser = localStorage.getItem('user');
        if (cachedUser) {
          try { setUserInfo(JSON.parse(cachedUser)); } catch (e) {}
        }
        fetchUserInfo();
      } else {
        setIsLoggedIn(false);
        setUserInfo(null);
      }
    };
    
    checkAuth();

    // Listen for custom login events from Login page or other tabs
    window.addEventListener('storage', checkAuth);
    window.addEventListener('userLogin', checkAuth);
    return () => {
      window.removeEventListener('storage', checkAuth);
      window.removeEventListener('userLogin', checkAuth);
    };
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    setShowDropdown(false);
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsLoggedIn(false);
    setUserInfo(null);
    setShowDropdown(false);
    setMenuOpen(false);
    window.location.href = '/';
  };

  useEffect(() => {
    if (!showDropdown) return;
    const close = (e) => { if (!e.target.closest('.user-menu')) setShowDropdown(false); };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [showDropdown]);

  // Khóa scroll body khi mobile menu mở
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  const navLinks = [
    { to: '/', label: '🏠 Trang chủ' },
    { to: '/dashboard', label: '📊 Dashboard' },
    { to: '/comic', label: '🎨 Tạo Comic', highlight: true },
    { to: '/upload', label: '📚 Dự Án' },
  ];

  // Auth section — dùng chung cả desktop lẫn mobile drawer
  const AuthSection = ({ mobile = false }) => (
    <div className={mobile ? 'drawer-auth' : 'navbar-auth-desktop'}>
      {isLoggedIn && userInfo ? (
        <div className="user-menu">
          <button onClick={() => setShowDropdown(!showDropdown)} className="user-menu-btn">
            {userInfo.avatar_url ? (
              <img src={userInfo.avatar_url} alt="Avatar" className="user-avatar" />
            ) : (
              <div className="user-avatar-placeholder">
                {(userInfo.username?.[0] || userInfo.email?.[0] || 'U').toUpperCase()}
              </div>
            )}
            <span className="user-name">
              {userInfo.username || userInfo.email?.split('@')[0]}
            </span>
            <svg className="dropdown-icon" width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <path d="M6 9L1 4h10z" />
            </svg>
          </button>
          {showDropdown && (
            <div className="user-dropdown">
              <div className="user-dropdown-header">
                <div className="user-dropdown-email">{userInfo.email}</div>
                <div className="user-dropdown-id">ID: {userInfo.id}</div>
              </div>
              <div className="user-dropdown-divider" />
              <Link to="/profile" className="user-dropdown-item" onClick={() => { setShowDropdown(false); setMenuOpen(false); }}>
                <span>👤</span> Hồ sơ
              </Link>
              <Link to="/settings" className="user-dropdown-item" onClick={() => { setShowDropdown(false); setMenuOpen(false); }}>
                <span>⚙️</span> Cài đặt
              </Link>
              {userInfo.role === 'admin' && (
                <>
                  <div className="user-dropdown-divider" />
                  <Link to="/admin" className="user-dropdown-item admin-link" onClick={() => { setShowDropdown(false); setMenuOpen(false); }}>
                    <span>👑</span> Admin Panel
                  </Link>
                </>
              )}
              <div className="user-dropdown-divider" />
              <button onClick={handleLogout} className="user-dropdown-item user-dropdown-logout">
                <span>🚪</span> Đăng xuất
              </button>
            </div>
          )}
        </div>
      ) : (
        <Link to="/login" className="navbar-btn navbar-btn-login" onClick={() => setMenuOpen(false)}>
          🔐 Đăng nhập
        </Link>
      )}
    </div>
  );

  return (
    <>
      {/* ── NAVBAR BAR ── */}
      <nav className="navbar">
        <div className="navbar-container">
          {/* Logo */}
          <Link to="/" className="navbar-logo">📚 TiênPhong AI</Link>

          {/* Desktop nav links (ẩn trên mobile) */}
          <ul className="navbar-menu-desktop">
            {navLinks.map(({ to, label, highlight }) => (
              <li key={to} className="navbar-item">
                <Link
                  to={to}
                  className={[
                    'navbar-link',
                    highlight ? 'navbar-link-highlight' : '',
                    isActive(to) ? 'active' : '',
                  ].join(' ').trim()}
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>

          {/* Desktop auth + hamburger */}
          <div className="navbar-right">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="theme-toggle-btn"
              aria-label={theme === 'dark' ? 'Chuyển sang sáng' : 'Chuyển sang tối'}
              title={theme === 'dark' ? '☀️ Sáng' : '🌙 Tối'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>

            <AuthSection mobile={false} />
            {/* Hamburger — chỉ hiển thị trên mobile */}
            <button
              className={`navbar-hamburger${menuOpen ? ' open' : ''}`}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label={menuOpen ? 'Đóng menu' : 'Mở menu'}
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </div>
      </nav>

      {/* ── MOBILE DRAWER — NGOÀI <nav>, tránh stacking context ── */}
      <aside className={`mobile-drawer${menuOpen ? ' open' : ''}`} aria-hidden={!menuOpen}>
        <ul className="mobile-drawer-links">
          {navLinks.map(({ to, label, highlight }) => (
            <li key={to}>
              <Link
                to={to}
                className={[
                  'navbar-link',
                  highlight ? 'navbar-link-highlight' : '',
                  isActive(to) ? 'active' : '',
                ].join(' ').trim()}
                onClick={() => setMenuOpen(false)}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>
        
        <div className="mobile-drawer-divider" />
        
        {/* Theme toggle in mobile */}
        <button
          onClick={toggleTheme}
          className="mobile-theme-toggle"
          aria-label={theme === 'dark' ? 'Chuyển sang sáng' : 'Chuyển sang tối'}
        >
          <span className="theme-toggle-icon">{theme === 'dark' ? '☀️' : '🌙'}</span>
          <span className="theme-toggle-text">
            {theme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối'}
          </span>
        </button>
        
        <div className="mobile-drawer-divider" />
        <AuthSection mobile={true} />
      </aside>

      {/* ── OVERLAY BACKDROP ── */}
      <div
        className={`navbar-overlay${menuOpen ? ' open' : ''}`}
        onClick={() => setMenuOpen(false)}
      />
    </>
  );
};

export default Navbar;
