import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import './Upload.css';

const Projects = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await api.get('/comic/projects');
        setProjects(response.data.projects);
      } catch (err) {
        setError('Không thể tải danh sách dự án');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);



  const handleDelete = async (sessionId) => {
    if (!confirm('Bạn có chắc muốn xóa project này?')) return;

    try {
      const token = localStorage.getItem('access_token');
      await api.delete(`/comic/projects/${sessionId}`);
      // Refresh list
      setProjects(projects.filter(p => p.session_id !== sessionId));
    } catch (err) {
      alert('Lỗi khi xóa project: ' + err.message);
    }
  };

  const handleDownload = (sessionId) => {
    const token = localStorage.getItem('access_token');
    const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
    window.location.href = `${apiBase}/comic/download/${sessionId}?token=${token}`;
  };

  if (loading) {
    return (
      <div className="projects-page">
        <div className="loading-spinner">Đang tải...</div>
      </div>
    );
  }

  return (
    <div className="projects-page">
      <div className="projects-header">
        <h1>📚 Dự Án Của Tôi</h1>
        <p className="projects-subtitle">Quản lý các comic đã tạo</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h3>Chưa có dự án nào</h3>
          <p>Hãy bắt đầu tạo comic đầu tiên của bạn!</p>
          <a href="/comic" className="create-button">Tạo Comic Mới</a>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map(project => (
            <ProjectCard 
              key={project.session_id}
              project={project}
              onDelete={handleDelete}
              onView={(sid) => navigate(`/comic?session=${sid}`)}
              onDownload={handleDownload}
            />
          ))}
        </div>
      )}

      <div className="projects-stats">
        <div className="stat-item">
          <span className="stat-value">{projects.length}</span>
          <span className="stat-label">Tổng dự án</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{projects.reduce((sum, p) => sum + p.page_count, 0)}</span>
          <span className="stat-label">Tổng trang</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{projects.reduce((sum, p) => sum + p.size_mb, 0).toFixed(1)} MB</span>
          <span className="stat-label">Dung lượng</span>
        </div>
      </div>
    </div>
  );
};

const ProjectCard = ({ project, onDelete, onDownload, onView }) => {
  const resolveThumbnailUrl = (thumbnail) => {
    if (!thumbnail) return '';
    if (/^https?:\/\//i.test(thumbnail)) return thumbnail;

    const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
    const origin = apiBase.replace(/\/api\/v1\/?$/i, '');
    if (thumbnail.startsWith('/')) return `${origin}${thumbnail}`;
    return `${origin}/${thumbnail}`;
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="project-card">
      <div className="project-thumbnail">
        {project.thumbnail ? (
          <img src={resolveThumbnailUrl(project.thumbnail)} alt="Thumbnail" />
        ) : (
          <div className="no-thumbnail">📄</div>
        )}
        <div className="project-badge">{project.page_count} trang</div>
      </div>
      
      <div className="project-info">
        <div className="project-id">ID: {project.session_id}</div>
        <div className="project-meta">
          <span>📅 {formatDate(project.created_at)}</span>
          <span>💾 {project.size_mb} MB</span>
        </div>
        {project.has_covers && <div className="project-tag">✨ Có Covers</div>}
      </div>

      <div className="project-actions">
        <button 
          onClick={() => onView(project.session_id)}
          className="action-btn view-btn"
          title="Xem preview"
        >
          👁️ Xem
        </button>
        <button 
          onClick={() => onDownload(project.session_id)}
          className="action-btn download-btn"
          title="Tải xuống ZIP"
        >
          ⬇️ Tải
        </button>
        <button 
          onClick={() => onDelete(project.session_id)}
          className="action-btn delete-btn"
          title="Xóa project"
        >
          🗑️ Xóa
        </button>
      </div>
    </div>
  );
};

export default Projects;
