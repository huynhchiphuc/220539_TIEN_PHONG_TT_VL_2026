import { useState, useEffect } from 'react';
import api from '../services/api';
import './Settings.css';

const Settings = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [darkMode, setDarkMode] = useState(localStorage.getItem('darkMode') === 'true');
  const [language, setLanguage] = useState(localStorage.getItem('language') || 'vi');
  
  // Modals
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showApiKeysModal, setShowApiKeysModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  
  // Forms
  const [passwordForm, setPasswordForm] = useState({ oldPassword: '', newPassword: '', confirmPassword: '' });
  const [editForm, setEditForm] = useState({ username: '', avatar_url: '' });
  const [apiKeys, setApiKeys] = useState([]);
  const [message, setMessage] = useState({ text: '', type: '' });

  useEffect(() => {
    fetchUserInfo();
    fetchApiKeys();
  }, []);

  useEffect(() => {
    document.body.classList.toggle('dark-mode', darkMode);
  }, [darkMode]);

  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.get('/auth/me');
      setUserInfo(response.data);
      setEditForm({ username: response.data.username, avatar_url: response.data.avatar_url || '' });
    } catch (error) {
      showMessage('Không thể tải thông tin người dùng', 'error');
    }
  };

  const fetchApiKeys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.get('/auth/api-keys');
      setApiKeys(response.data.keys || []);
    } catch (error) {
      console.log('No API keys yet');
    }
  };

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  const handleDarkModeToggle = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', newMode);
  };

  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    setLanguage(newLang);
    localStorage.setItem('language', newLang);
    showMessage('Đã đổi ngôn ngữ (tính năng đang phát triển)', 'success');
  };

  const handleChangePassword = async () => {
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      showMessage('Mật khẩu xác nhận không khớp', 'error');
      return;
    }
    try {
      const token = localStorage.getItem('access_token');
      await api.post('/auth/change-password', {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword
      });
      showMessage('Đổi mật khẩu thành công', 'success');
      setShowPasswordModal(false);
      setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' });
    } catch (error) {
      showMessage(error.response?.data?.detail || 'Đổi mật khẩu thất bại', 'error');
    }
  };

  const handleUpdateProfile = async () => {
    try {
      const token = localStorage.getItem('access_token');
      await api.put('/auth/me', editForm);
      showMessage('Cập nhật thông tin thành công', 'success');
      setShowEditModal(false);
      fetchUserInfo();
    } catch (error) {
      showMessage(error.response?.data?.detail || 'Cập nhật thất bại', 'error');
    }
  };

  const handleCreateApiKey = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.post('/auth/api-keys', {
        name: `Key ${apiKeys.length + 1}`
      });
      showMessage('Tạo API Key thành công', 'success');
      fetchApiKeys();
    } catch (error) {
      showMessage('Tạo API Key thất bại', 'error');
    }
  };

  const handleDeleteApiKey = async (keyId) => {
    try {
      const token = localStorage.getItem('access_token');
      await api.delete(`/auth/api-keys/${keyId}`);
      showMessage('Xóa API Key thành công', 'success');
      fetchApiKeys();
    } catch (error) {
      showMessage('Xóa API Key thất bại', 'error');
    }
  };

  const handleDeleteAccount = async () => {
    try {
      const token = localStorage.getItem('access_token');
      await api.delete('/auth/me');
      localStorage.removeItem('access_token');
      window.location.href = '/';
    } catch (error) {
      showMessage('Xóa tài khoản thất bại', 'error');
    }
  };

  if (!userInfo) {
    return <div className="settings-container"><div className="loading">Đang tải...</div></div>;
  }

  return (
    <div className="settings-container">
      {message.text && (
        <div className={`settings-message ${message.type}`}>{message.text}</div>
      )}
      
      <div className="settings-card">
        <h1 className="settings-title">⚙️ Cài Đặt</h1>
        
        <div className="settings-section">
          <h2 className="settings-section-title">Tài khoản</h2>
          {!userInfo.google_id && (
            <div className="settings-item">
              <label>Thay đổi mật khẩu</label>
              <button className="settings-btn" onClick={() => setShowPasswordModal(true)}>Đổi mật khẩu</button>
            </div>
          )}
          <div className="settings-item">
            <label>Cập nhật thông tin</label>
            <button className="settings-btn" onClick={() => setShowEditModal(true)}>Chỉnh sửa</button>
          </div>
        </div>

        <div className="settings-section">
          <h2 className="settings-section-title">Giao diện</h2>
          <div className="settings-item">
            <label>Chế độ tối</label>
            <input 
              type="checkbox" 
              checked={darkMode} 
              onChange={handleDarkModeToggle}
              className="settings-toggle" 
            />
          </div>
          <div className="settings-item">
            <label>Ngôn ngữ</label>
            <select 
              className="settings-select"
              value={language}
              onChange={handleLanguageChange}
            >
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>

        <div className="settings-section">
          <h2 className="settings-section-title">API Keys</h2>
          <div className="settings-item">
            <label>Quản lý API Keys</label>
            <button className="settings-btn" onClick={() => setShowApiKeysModal(true)}>Xem API Keys ({apiKeys.length})</button>
          </div>
        </div>

        <div className="settings-section danger-zone">
          <h2 className="settings-section-title">Vùng nguy hiểm</h2>
          <div className="settings-item">
            <label>Xóa tài khoản</label>
            <button className="settings-btn-danger" onClick={() => setShowDeleteModal(true)}>Xóa tài khoản</button>
          </div>
        </div>
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Đổi mật khẩu</h2>
            <input
              type="password"
              placeholder="Mật khẩu cũ"
              value={passwordForm.oldPassword}
              onChange={(e) => setPasswordForm({...passwordForm, oldPassword: e.target.value})}
              className="modal-input"
            />
            <input
              type="password"
              placeholder="Mật khẩu mới"
              value={passwordForm.newPassword}
              onChange={(e) => setPasswordForm({...passwordForm, newPassword: e.target.value})}
              className="modal-input"
            />
            <input
              type="password"
              placeholder="Xác nhận mật khẩu mới"
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm({...passwordForm, confirmPassword: e.target.value})}
              className="modal-input"
            />
            <div className="modal-actions">
              <button className="modal-btn" onClick={handleChangePassword}>Đổi mật khẩu</button>
              <button className="modal-btn-cancel" onClick={() => setShowPasswordModal(false)}>Hủy</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Profile Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Chỉnh sửa thông tin</h2>
            <input
              type="text"
              placeholder="Username"
              value={editForm.username}
              onChange={(e) => setEditForm({...editForm, username: e.target.value})}
              className="modal-input"
            />
            <input
              type="text"
              placeholder="Avatar URL"
              value={editForm.avatar_url}
              onChange={(e) => setEditForm({...editForm, avatar_url: e.target.value})}
              className="modal-input"
            />
            <div className="modal-actions">
              <button className="modal-btn" onClick={handleUpdateProfile}>Lưu</button>
              <button className="modal-btn-cancel" onClick={() => setShowEditModal(false)}>Hủy</button>
            </div>
          </div>
        </div>
      )}

      {/* API Keys Modal */}
      {showApiKeysModal && (
        <div className="modal-overlay" onClick={() => setShowApiKeysModal(false)}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <h2>Quản lý API Keys</h2>
            <button className="modal-btn" onClick={handleCreateApiKey}>+ Tạo API Key mới</button>
            <div className="api-keys-list">
              {apiKeys.length === 0 ? (
                <p>Chưa có API Key nào</p>
              ) : (
                apiKeys.map((key) => (
                  <div key={key.id} className="api-key-item">
                    <div>
                      <div className="api-key-name">{key.name}</div>
                      <code className="api-key-value">{key.key}</code>
                      <div className="api-key-date">Tạo: {new Date(key.created_at).toLocaleDateString('vi-VN')}</div>
                    </div>
                    <button className="api-key-delete" onClick={() => handleDeleteApiKey(key.id)}>Xóa</button>
                  </div>
                ))
              )}
            </div>
            <div className="modal-actions">
              <button className="modal-btn-cancel" onClick={() => setShowApiKeysModal(false)}>Đóng</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>⚠️ Xác nhận xóa tài khoản</h2>
            <p>Hành động này không thể hoàn tác. Tất cả dữ liệu của bạn sẽ bị xóa vĩnh viễn.</p>
            <div className="modal-actions">
              <button className="modal-btn-danger" onClick={handleDeleteAccount}>Xóa vĩnh viễn</button>
              <button className="modal-btn-cancel" onClick={() => setShowDeleteModal(false)}>Hủy</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
