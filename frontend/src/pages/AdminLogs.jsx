import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './AdminLogs.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:60074/api/v1';

function AdminLogs() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
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

    fetchLogs();
  }, [navigate, page]);

  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/admin/logs/activities?page=${page}&limit=50`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setLogs(response.data.logs);
      setTotalPages(response.data.total_pages);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching logs:', error);
      setError(error.response?.data?.detail || 'Failed to load activity logs');
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('vi-VN');
  };

  const getActionIcon = (actionType) => {
    const iconMap = {
      'login': '🔐',
      'logout': '🚪',
      'register': '📝',
      'create_project': '📚',
      'delete_project': '🗑️',
      'upload_image': '📤',
      'generate_comic': '🎨',
      'update_profile': '👤',
      'update_settings': '⚙️'
    };
    return iconMap[actionType] || '📋';
  };

  const getActionBadge = (actionType) => {
    const typeMap = {
      'login': 'success',
      'logout': 'info',
      'register': 'success',
      'create_project': 'primary',
      'delete_project': 'danger',
      'upload_image': 'primary',
      'generate_comic': 'primary',
      'update_profile': 'info',
      'update_settings': 'info'
    };
    const badgeClass = typeMap[actionType] || 'default';
    return (
      <span className={`action-badge ${badgeClass}`}>
        {getActionIcon(actionType)} {actionType.replace(/_/g, ' ')}
      </span>
    );
  };

  if (loading) {
    return <div className="admin-logs"><div className="loading">Đang tải...</div></div>;
  }

  if (error) {
    return <div className="admin-logs"><div className="error">❌ {error}</div></div>;
  }

  return (
    <div className="admin-logs">
      <div className="admin-header">
        <h1>📋 Activity Logs</h1>
        <button onClick={() => navigate('/admin')}>⬅️ Back to Dashboard</button>
      </div>

      <div className="logs-info">
        <div className="info-card">
          <span className="info-icon">📊</span>
          <span>Showing {logs.length} logs</span>
        </div>
      </div>

      <div className="logs-table-container">
        <table className="logs-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>User</th>
              <th>Description</th>
              <th>IP Address</th>
              <th>User Agent</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: '#999' }}>
                  📭 No activity logs found
                </td>
              </tr>
            ) : (
              logs.map(log => (
                <tr key={log.id}>
                  <td className="time-cell">{formatDate(log.created_at)}</td>
                  <td>{getActionBadge(log.action)}</td>
                  <td>
                    {log.username ? (
                      <div className="user-info">
                        <div className="user-name">{log.username}</div>
                        <div className="user-email">{log.email}</div>
                      </div>
                    ) : (
                      <span className="anonymous">Anonymous</span>
                    )}
                  </td>
                  <td className="description-cell">{log.details || '-'}</td>
                  <td className="ip-cell">{log.ip_address || '-'}</td>
                  <td className="agent-cell">
                    <div className="agent-truncate" title={log.user_agent}>
                      {log.user_agent ? log.user_agent.substring(0, 50) + '...' : '-'}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            ⬅️ Previous
          </button>
          <span>Page {page} of {totalPages}</span>
          <button 
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next ➡️
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminLogs;
