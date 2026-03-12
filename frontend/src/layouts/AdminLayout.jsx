import { Outlet, Link, useLocation } from 'react-router-dom';
import './AdminLayout.css';

const AdminLayout = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;

  const menuItems = [
    { to: '/admin', label: 'Admin Dashboard', icon: '🛡️' },
    { to: '/admin/users', label: 'Quản lý Users', icon: '👥' },
    { to: '/admin/projects', label: 'Quản lý Projects', icon: '📚' },
    { to: '/admin/logs', label: 'Activity Logs', icon: '📋' },
    { to: '/', label: 'Back to Home', icon: '🏠', divider: true },
  ];

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <nav className="admin-nav">
          {menuItems.map(({ to, label, icon, divider }) => (
            <div key={to}>
              {divider && <div className="admin-nav-divider" />}
              <Link
                to={to}
                className={`admin-nav-item ${isActive(to) ? 'active' : ''}`}
              >
                <span className="admin-nav-icon">{icon}</span>
                <span className="admin-nav-label">{label}</span>
              </Link>
            </div>
          ))}
        </nav>
      </aside>
      <div className="admin-main">
        <Outlet />
      </div>
    </div>
  );
};

export default AdminLayout;
