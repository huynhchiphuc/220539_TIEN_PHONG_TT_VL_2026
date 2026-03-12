import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './AdminUsers.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';

function AdminUsers() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [editingUser, setEditingUser] = useState(null);

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

    fetchUsers();
  }, [navigate, page, search, roleFilter]);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({ page, limit: 20 });
      if (search) params.append('search', search);
      if (roleFilter) params.append('role', roleFilter);

      const response = await axios.get(`${API_BASE_URL}/admin/users?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setUsers(response.data.users);
      setTotalPages(response.data.total_pages);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching users:', error);
      setError(error.response?.data?.detail || 'Failed to load users');
      setLoading(false);
    }
  };

  const handleUpdateUser = async (userId, updates) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_BASE_URL}/admin/users/${userId}`, updates, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      alert('✅ User updated successfully!');
      setEditingUser(null);
      fetchUsers();
    } catch (error) {
      console.error('Error updating user:', error);
      alert(`❌ ${error.response?.data?.detail || 'Failed to update user'}`);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`⚠️ Are you sure you want to delete user "${username}"?`)) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/admin/users/${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      alert('✅ User deleted successfully!');
      fetchUsers();
    } catch (error) {
      console.error('Error deleting user:', error);
      alert(`❌ ${error.response?.data?.detail || 'Failed to delete user'}`);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('vi-VN');
  };

  if (loading) {
    return <div className="admin-users"><div className="loading">Đang tải...</div></div>;
  }

  if (error) {
    return <div className="admin-users"><div className="error">❌ {error}</div></div>;
  }

  return (
    <div className="admin-users">
      <div className="admin-header">
        <h1>👥 User Management</h1>
        <button onClick={() => navigate('/admin')}>⬅️ Back to Dashboard</button>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="🔍 Search by username or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
        <select 
          value={roleFilter} 
          onChange={(e) => setRoleFilter(e.target.value)}
          className="role-filter"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>
                  {user.avatar_url && <img src={user.avatar_url} alt="" className="user-avatar" />}
                  {user.username}
                </td>
                <td>{user.email}</td>
                <td>
                  <span className={`role-badge ${user.role}`}>
                    {user.role === 'admin' ? '👑' : '👤'} {user.role}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                    {user.is_active ? '✅ Active' : '❌ Inactive'}
                  </span>
                </td>
                <td>{formatDate(user.created_at)}</td>
                <td>{formatDate(user.last_login)}</td>
                <td className="actions">
                  <button 
                    onClick={() => setEditingUser(user)}
                    className="btn-edit"
                  >
                    ✏️ Edit
                  </button>
                  <button 
                    onClick={() => handleDeleteUser(user.id, user.username)}
                    className="btn-delete"
                  >
                    🗑️ Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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

      {editingUser && (
        <div className="modal-overlay" onClick={() => setEditingUser(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>✏️ Edit User: {editingUser.username}</h2>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              handleUpdateUser(editingUser.id, {
                username: formData.get('username'),
                email: formData.get('email'),
                role: formData.get('role'),
                is_active: formData.get('is_active') === 'true'
              });
            }}>
              <div className="form-group">
                <label>Username</label>
                <input 
                  name="username" 
                  defaultValue={editingUser.username}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input 
                  name="email" 
                  type="email"
                  defaultValue={editingUser.email}
                  required
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select name="role" defaultValue={editingUser.role}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select name="is_active" defaultValue={editingUser.is_active ? 'true' : 'false'}>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-save">💾 Save</button>
                <button type="button" onClick={() => setEditingUser(null)} className="btn-cancel">
                  ❌ Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminUsers;
