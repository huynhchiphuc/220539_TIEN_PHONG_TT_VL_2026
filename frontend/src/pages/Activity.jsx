import { useState, useEffect } from 'react';
import axios from 'axios';
import './Activity.css';

const Activity = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, upload, generate, export

  useEffect(() => {
    fetchActivities();
  }, []);

  const fetchActivities = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('http://localhost:60074/api/v1/comic/activity', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setActivities(response.data.activities || []);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type) => {
    const icons = {
      upload: '📤',
      generate: '🎨',
      export: '📥',
      delete: '🗑️',
      view: '👁️'
    };
    return icons[type] || '📋';
  };

  const getActivityColor = (type) => {
    const colors = {
      upload: '#3b82f6',
      generate: '#8b5cf6',
      export: '#22c55e',
      delete: '#ef4444',
      view: '#f59e0b'
    };
    return colors[type] || '#6b7280';
  };

  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(a => a.action_type === filter);

  if (loading) {
    return (
      <div className="activity-container">
        <div className="loading">Đang tải lịch sử...</div>
      </div>
    );
  }

  return (
    <div className="activity-container">
      <div className="activity-header">
        <h1 className="activity-title">📜 Lịch Sử Hoạt Động</h1>
        <div className="activity-filters">
          <button 
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Tất cả ({activities.length})
          </button>
          <button 
            className={`filter-btn ${filter === 'upload' ? 'active' : ''}`}
            onClick={() => setFilter('upload')}
          >
            📤 Upload ({activities.filter(a => a.action_type === 'upload').length})
          </button>
          <button 
            className={`filter-btn ${filter === 'generate' ? 'active' : ''}`}
            onClick={() => setFilter('generate')}
          >
            🎨 Generate ({activities.filter(a => a.action_type === 'generate').length})
          </button>
          <button 
            className={`filter-btn ${filter === 'export' ? 'active' : ''}`}
            onClick={() => setFilter('export')}
          >
            📥 Export ({activities.filter(a => a.action_type === 'export').length})
          </button>
        </div>
      </div>

      <div className="activity-timeline">
        {filteredActivities.length === 0 ? (
          <div className="no-activity">
            <p>Chưa có hoạt động nào</p>
          </div>
        ) : (
          filteredActivities.map((activity) => (
            <div 
              key={activity.id} 
              className="activity-item"
              style={{ borderLeftColor: getActivityColor(activity.action_type) }}
            >
              <div className="activity-icon" style={{ background: getActivityColor(activity.action_type) }}>
                {getActivityIcon(activity.action_type)}
              </div>
              <div className="activity-content">
                <div className="activity-header-row">
                  <h3 className="activity-action">{activity.action_type.toUpperCase()}</h3>
                  <span className="activity-time">
                    {new Date(activity.timestamp).toLocaleString('vi-VN')}
                  </span>
                </div>
                {activity.session_id && (
                  <div className="activity-session">Session: {activity.session_id}</div>
                )}
                {activity.details && (
                  <div className="activity-details">{activity.details}</div>
                )}
                <div className="activity-meta">
                  {activity.image_count > 0 && (
                    <span className="meta-badge">🖼️ {activity.image_count} ảnh</span>
                  )}
                  {activity.layout_mode && (
                    <span className="meta-badge">📐 {activity.layout_mode}</span>
                  )}
                  {activity.status && (
                    <span className={`meta-badge status-${activity.status}`}>
                      {activity.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Activity;
