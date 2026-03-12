import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './AdminProjects.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:60074/api/v1';

function AdminProjects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

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

    fetchProjects();
  }, [navigate, page, statusFilter]);

  const fetchProjects = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({ page, limit: 20 });
      if (statusFilter) params.append('status', statusFilter);

      const response = await axios.get(`${API_BASE_URL}/admin/projects?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setProjects(response.data.projects);
      setTotalPages(response.data.total_pages);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setError(error.response?.data?.detail || 'Failed to load projects');
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectId, title) => {
    if (!confirm(`⚠️ Bạn có chắc muốn xóa project "${title}"? Hành động này không thể hoàn tác!`)) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/admin/projects/${projectId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      alert('✅ Project deleted successfully!');
      fetchProjects();
    } catch (error) {
      console.error('Error deleting project:', error);
      alert(`❌ ${error.response?.data?.detail || 'Failed to delete project'}`);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('vi-VN');
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'draft': { label: '📝 Draft', class: 'draft' },
      'processing': { label: '⚙️ Processing', class: 'processing' },
      'completed': { label: '✅ Completed', class: 'completed' },
      'failed': { label: '❌ Failed', class: 'failed' }
    };
    const statusInfo = statusMap[status] || { label: status, class: 'unknown' };
    return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.label}</span>;
  };

  if (loading) {
    return <div className="admin-projects"><div className="loading">Đang tải...</div></div>;
  }

  if (error) {
    return <div className="admin-projects"><div className="error">❌ {error}</div></div>;
  }

  return (
    <div className="admin-projects">
      <div className="admin-header">
        <h1>📚 Project Management</h1>
        <button onClick={() => navigate('/admin')}>⬅️ Back to Dashboard</button>
      </div>

      <div className="filters">
        <select 
          value={statusFilter} 
          onChange={(e) => setStatusFilter(e.target.value)}
          className="status-filter"
        >
          <option value="">All Status</option>
          <option value="draft">📝 Draft</option>
          <option value="processing">⚙️ Processing</option>
          <option value="completed">✅ Completed</option>
          <option value="failed">❌ Failed</option>
        </select>
        <div className="stats-summary">
          Total Projects: <strong>{projects.length}</strong>
        </div>
      </div>

      <div className="projects-table-container">
        <table className="projects-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Pages</th>
              <th>Created</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: '#999' }}>
                  📭 No projects found
                </td>
              </tr>
            ) : (
              projects.map(project => (
                <tr key={project.id}>
                  <td>{project.id}</td>
                  <td className="project-title">
                    <div className="title-main">{project.project_name || 'Untitled'}</div>
                    {project.layout_mode && (
                      <div className="title-meta">
                        {project.layout_mode}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="owner-info">
                      <div className="owner-username">{project.username || 'Unknown'}</div>
                      <div className="owner-email">{project.email}</div>
                    </div>
                  </td>
                  <td>{getStatusBadge(project.status)}</td>
                  <td>
                    <span className="pages-badge">{project.total_pages || 0}</span>
                  </td>
                  <td className="date-cell">{formatDate(project.created_at)}</td>
                  <td className="date-cell">{formatDate(project.updated_at)}</td>
                  <td className="actions">
                    <button 
                      onClick={() => handleDeleteProject(project.id, project.project_name)}
                      className="btn-delete"
                      title="Delete project"
                    >
                      🗑️ Delete
                    </button>
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

export default AdminProjects;
