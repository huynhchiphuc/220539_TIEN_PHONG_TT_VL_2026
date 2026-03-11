import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;

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
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
