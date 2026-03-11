import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from '../services/api';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) fetchUserInfo();
  }, []);

  // Đóng menu khi đổi route
  useEffect(() => {
    setMenuOpen(false);
    setShowDropdown(false);
  }, [location.pathname]);

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/auth/me');
      setUserInfo(response.data);
      setIsLoggedIn(true);
    } catch {
      localStorage.removeItem('access_token');
      setIsLoggedIn(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setIsLoggedIn(false);
    setUserInfo(null);
    setShowDropdown(false);
    setMenuOpen(false);
    window.location.href = '/';
  };

  // Đóng dropdown khi click ngoài
  useEffect(() => {
    if (!showDropdown) return;
    const close = (e) => {
      if (!e.target.closest('.user-menu')) setShowDropdown(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [showDropdown]);

  // Khóa scroll khi mobile menu mở
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  const navLinks = [
    { to: '/', label: '🏠 Trang chủ' },
    { to: '/dashboard', label: '📊 Dashboard' },
    { to: '/comic', label: '🎨 Tạo Comic', highlight: true },
    { to: '/upload', label: '📚 Dự Án' },
    { to: '/activity', label: '📜 Lịch Sử' },
  ];

  return (
    <>
      <nav className="navbar">
        <div className="navbar-container">
          {/* Logo */}
          <Link to="/" className="navbar-logo">
            📚 TiênPhong AI
          </Link>

          {/* Desktop + Mobile menu */}
          <ul className={`navbar-menu${menuOpen ? ' open' : ''}`}>
            {navLinks.map(({ to, label, highlight }) => (
              <li key={to} className="navbar-item">
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

            {/* Auth */}
            <li className="navbar-item navbar-auth">
              {isLoggedIn && userInfo ? (
                <div className="user-menu">
                  <button
                    onClick={() => setShowDropdown(!showDropdown)}
                    className="user-menu-btn"
                  >
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
                      <div className="user-dropdown-divider" />
                      <button onClick={handleLogout} className="user-dropdown-item user-dropdown-logout">
                        <span>🚪</span> Đăng xuất
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <Link to="/login" className="navbar-btn navbar-btn-login">
                  🔐 Đăng nhập
                </Link>
              )}
            </li>
          </ul>

          {/* Hamburger button (mobile) */}
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
      </nav>

      {/* Mobile overlay backdrop */}
      <div
        className={`navbar-overlay${menuOpen ? ' open' : ''}`}
        onClick={() => setMenuOpen(false)}
      />
    </>
  );
};

export default Navbar;
