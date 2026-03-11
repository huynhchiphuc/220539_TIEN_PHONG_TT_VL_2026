import { useState, useEffect } from 'react';
import api from '../services/api';
import './Dashboard.css';

// Decode JWT token để lấy thông tin user nhanh (không cần gọi API)
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Lấy thông tin user từ token ngay lập tức (không chờ API)
  const token = localStorage.getItem('access_token');
  const tokenPayload = token ? parseJwt(token) : null;
  const localUsername = tokenPayload?.username || tokenPayload?.sub || 'Người dùng';
  const localEmail = tokenPayload?.email || '';

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      // Dùng api instance chuẩn (đã có Authorization header tự động)
      const response = await api.get('/comic/dashboard');
      setStats(response.data);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
      setError('Không thể tải dữ liệu dashboard. Kiểm tra kết nối backend.');
    } finally {
      setLoading(false);
    }
  };

  // Hiển thị skeleton trong khi chờ load
  if (loading) {
    return (
      <div className="dashboard-container">
        <h1 className="dashboard-title">📊 Dashboard</h1>
        <div className="dashboard-summary">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="summary-card skeleton-card">
              <div className="skeleton-block" style={{ width: '40px', height: '40px', borderRadius: '50%' }} />
              <div className="summary-content">
                <div className="skeleton-block" style={{ width: '60px', height: '28px', marginBottom: '8px' }} />
                <div className="skeleton-block" style={{ width: '80px', height: '14px' }} />
              </div>
            </div>
          ))}
        </div>
        <p style={{ textAlign: 'center', color: '#94a3b8', marginTop: '32px' }}>Đang tải dashboard...</p>
      </div>
    );
  }

  // Hiện user info từ token ngay cả khi API lỗi
  const displayUsername = stats?.user_name || localUsername;
  const displayEmail = stats?.user_email || localEmail;
  const displayCreatedAt = stats?.user_created_at
    ? new Date(stats.user_created_at).toLocaleDateString('vi-VN')
    : 'N/A';
  const displayLastLogin = stats?.user_last_login
    ? new Date(stats.user_last_login).toLocaleString('vi-VN')
    : 'N/A';

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-title">📊 Dashboard</h1>
        <button onClick={fetchDashboard} className="dashboard-refresh-btn">
          🔄 Làm mới
        </button>
      </div>

      {error && (
        <div className="dashboard-error">
          ⚠️ {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="dashboard-summary">
        <div className="summary-card">
          <div className="summary-icon">📚</div>
          <div className="summary-content">
            <div className="summary-value">{stats?.total_projects ?? 0}</div>
            <div className="summary-label">Tổng Dự Án</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">📄</div>
          <div className="summary-content">
            <div className="summary-value">{stats?.total_pages ?? 0}</div>
            <div className="summary-label">Tổng Trang</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">💾</div>
          <div className="summary-content">
            <div className="summary-value">
              {stats?.total_size_mb != null ? Number(stats.total_size_mb).toFixed(1) : '0.0'} MB
            </div>
            <div className="summary-label">Dung Lượng</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">⚡</div>
          <div className="summary-content">
            <div className="summary-value">{stats?.total_activities ?? 0}</div>
            <div className="summary-label">Hoạt Động</div>
          </div>
        </div>
      </div>

      {/* Account Info — luôn hiển thị từ token, được làm phong phú bởi API */}
      <div className="dashboard-section">
        <h2 className="section-title">👤 Thông tin tài khoản</h2>
        <div className="account-info">
          <div className="info-row">
            <span className="info-label">Username:</span>
            <span className="info-value">{displayUsername}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Email:</span>
            <span className="info-value">{displayEmail || '—'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Tham gia:</span>
            <span className="info-value">{displayCreatedAt}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Lần đăng nhập cuối:</span>
            <span className="info-value">{displayLastLogin}</span>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="dashboard-section">
        <h2 className="section-title">🕐 Hoạt động gần đây</h2>
        <div className="recent-activities">
          {stats?.recent_activities && stats.recent_activities.length > 0 ? (
            stats.recent_activities.map((activity, idx) => (
              <div key={idx} className="activity-row">
                <span className="activity-type-badge">{activity.action_type}</span>
                <span className="activity-details">{activity.details || '—'}</span>
                <span className="activity-time">
                  {activity.timestamp
                    ? new Date(activity.timestamp).toLocaleString('vi-VN')
                    : '—'}
                </span>
              </div>
            ))
          ) : (
            <p className="no-data">Chưa có hoạt động nào được ghi nhận</p>
          )}
        </div>
      </div>

      {/* Projects Overview */}
      <div className="dashboard-section">
        <h2 className="section-title">🗂️ Dự án gần đây</h2>
        <div className="projects-overview">
          {stats?.recent_projects && stats.recent_projects.length > 0 ? (
            stats.recent_projects.map((project, idx) => (
              <div key={idx} className="project-mini-card">
                <div className="project-mini-header">
                  <span className="project-session" title={project.session_id}>
                    {project.session_id.slice(0, 12)}…
                  </span>
                  <span className="project-pages">{project.page_count} trang</span>
                </div>
                <div className="project-mini-footer">
                  <span>{Number(project.size_mb).toFixed(1)} MB</span>
                  <span>{new Date(project.created_at).toLocaleDateString('vi-VN')}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="no-data">Chưa có dự án nào. Hãy tạo truyện tranh đầu tiên!</p>
          )}
        </div>
      </div>

      {/* Activity Chart */}
      <div className="dashboard-section">
        <h2 className="section-title">📈 Thống kê theo hành động</h2>
        <div className="chart-container">
          {stats?.activity_breakdown && Object.keys(stats.activity_breakdown).length > 0 ? (
            <div className="bar-chart">
              {Object.entries(stats.activity_breakdown).map(([type, count]) => {
                const maxVal = Math.max(...Object.values(stats.activity_breakdown));
                return (
                  <div key={type} className="bar-item">
                    <div className="bar-label">{type}</div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(count / maxVal) * 100}%`,
                          background: getBarColor(type)
                        }}
                      >
                        <span className="bar-value">{count}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="no-data">Chưa có dữ liệu thống kê</p>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function for bar colors
const getBarColor = (type) => {
  const colors = {
    upload: '#3b82f6',
    upload_images: '#3b82f6',
    generate: '#8b5cf6',
    generate_comic: '#8b5cf6',
    export: '#22c55e',
    download_zip: '#22c55e',
    download_pdf: '#10b981',
    delete: '#ef4444',
    view: '#f59e0b'
  };
  return colors[type] || '#6b7280';
};

export default Dashboard;
