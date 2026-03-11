import { Link } from 'react-router-dom';
import './Footer.css';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-content">
        {/* Brand Section */}
        <div className="footer-section footer-brand">
          <h3 className="footer-logo">📚 ComicCraft AI</h3>
          <p className="footer-tagline">
            Tạo truyện tranh, manga chuyên nghiệp từ ảnh với công nghệ AI tiên tiến
          </p>
          <div className="footer-social">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="social-link">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
            </a>
            <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" className="social-link">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
            </a>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="social-link">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
              </svg>
            </a>
            <a href="mailto:support@comiccraft.ai" className="social-link">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
              </svg>
            </a>
          </div>
        </div>

        {/* Quick Links */}
        <div className="footer-section">
          <h4 className="footer-title">Tính Năng</h4>
          <ul className="footer-links">
            <li><Link to="/comic">🎨 Comic Generator</Link></li>
            <li><Link to="/dashboard">📊 Dashboard</Link></li>
            <li><Link to="/upload">📚 Quản Lý Dự Án</Link></li>
            <li><Link to="/activity">📜 Lịch Sử</Link></li>
          </ul>
        </div>

        {/* Account Links */}
        <div className="footer-section">
          <h4 className="footer-title">Tài Khoản</h4>
          <ul className="footer-links">
            <li><Link to="/profile">👤 Profile</Link></li>
            <li><Link to="/settings">⚙️ Cài Đặt</Link></li>
            <li><Link to="/login">🔐 Đăng Nhập</Link></li>
          </ul>
        </div>

        {/* Resources */}
        <div className="footer-section">
          <h4 className="footer-title">Tài Nguyên</h4>
          <ul className="footer-links">
            <li><a href="http://localhost:60074/docs" target="_blank" rel="noopener noreferrer">📖 API Docs</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>📝 Hướng Dẫn</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>❓ FAQ</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>💬 Hỗ Trợ</a></li>
          </ul>
        </div>

        {/* Legal */}
        <div className="footer-section">
          <h4 className="footer-title">Pháp Lý</h4>
          <ul className="footer-links">
            <li><a href="#" onClick={(e) => e.preventDefault()}>📋 Điều Khoản</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>🔒 Chính Sách</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>🍪 Cookies</a></li>
            <li><a href="#" onClick={(e) => e.preventDefault()}>ℹ️ Về Chúng Tôi</a></li>
          </ul>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="footer-bottom">
        <div className="footer-bottom-content">
          <p className="footer-copyright">
            © {currentYear} ComicCraft AI. All rights reserved.
          </p>
          <p className="footer-tech">
            Built with ❤️ using React, FastAPI & AI
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
