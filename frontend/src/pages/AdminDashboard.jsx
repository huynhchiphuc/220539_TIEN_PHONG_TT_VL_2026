import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import './AdminDashboard.css';

function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if user is admin
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    
    if (!token || !userStr) {
      navigate('/login');
      return;
    }

    const user = JSON.parse(userStr);
    if (user.role !== 'admin') {
      alert('🚫 Bạn không có quyền truy cập trang này!');
      navigate('/dashboard');
      return;
    }

    fetchStats();
  }, [navigate]);

  const fetchStats = async () => {
    try {
      const response = await api.get('/admin/stats/dashboard');
      setStats(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching stats:', error);
      setError(error.response?.data?.detail || 'Failed to load dashboard stats');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="loading">Đang tải...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-dashboard">
        <div className="error">❌ {error}</div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
      </div>

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">👥</div>
              <div className="stat-content">
                <div className="stat-value">{stats.overview.total_users}</div>
                <div className="stat-label">Total Users</div>
                <div className="stat-detail">
                  +{stats.overview.monthly_users} this month
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">✅</div>
              <div className="stat-content">
                <div className="stat-value">{stats.overview.active_users}</div>
                <div className="stat-label">Active Users</div>
                <div className="stat-detail">Last 7 days</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📚</div>
              <div className="stat-content">
                <div className="stat-value">{stats.overview.total_projects}</div>
                <div className="stat-label">Total Projects</div>
                <div className="stat-detail">
                  +{stats.overview.monthly_projects} this month
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🖼️</div>
              <div className="stat-content">
                <div className="stat-value">{stats.overview.total_images}</div>
                <div className="stat-label">Uploaded Images</div>
                <div className="stat-detail">All time</div>
              </div>
            </div>
          </div>

          <div className="charts-section">
            <div className="chart-card">
              <h2>👥 User Growth (Last 6 Months)</h2>
              <div className="simple-chart">
                {stats.growth.users.map((item, index) => (
                  <div key={index} className="chart-bar">
                    <div className="bar-label">{item.month}</div>
                    <div className="bar-container">
                      <div 
                        className="bar-fill" 
                        style={{ width: `${(item.count / Math.max(...stats.growth.users.map(u => u.count))) * 100}%` }}
                      >
                        {item.count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="chart-card">
              <h2>📚 Project Growth (Last 6 Months)</h2>
              <div className="simple-chart">
                {stats.growth.projects.map((item, index) => (
                  <div key={index} className="chart-bar">
                    <div className="bar-label">{item.month}</div>
                    <div className="bar-container">
                      <div 
                        className="bar-fill project" 
                        style={{ width: `${(item.count / Math.max(...stats.growth.projects.map(p => p.count))) * 100}%` }}
                      >
                        {item.count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminDashboard;
