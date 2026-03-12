import { useState, useEffect } from 'react';
import api from '../services/api';
import './Profile.css';

const Profile = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.get('/auth/me');
      setUserInfo(response.data);
    } catch (error) {
      console.error('Failed to fetch user info:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="profile-container"><div className="loading">Đang tải...</div></div>;
  }

  if (!userInfo) {
    return <div className="profile-container"><div className="error">Không thể tải thông tin người dùng</div></div>;
  }

  return (
    <div className="profile-container">
      <div className="profile-card">
        <h1 className="profile-title">Hồ Sơ Người Dùng</h1>
        
        <div className="profile-avatar-section">
          {userInfo.avatar_url ? (
            <img src={userInfo.avatar_url} alt="Avatar" className="profile-avatar" />
          ) : (
            <div className="profile-avatar-placeholder">
              {userInfo.username?.[0]?.toUpperCase() || userInfo.email?.[0]?.toUpperCase() || 'U'}
            </div>
          )}
        </div>

        <div className="profile-info">
          <div className="profile-field">
            <label>ID:</label>
            <span>{userInfo.id}</span>
          </div>
          <div className="profile-field">
            <label>Username:</label>
            <span>{userInfo.username}</span>
          </div>
          <div className="profile-field">
            <label>Email:</label>
            <span>{userInfo.email}</span>
          </div>
          <div className="profile-field">
            <label>Trạng thái:</label>
            <span className={userInfo.is_active ? 'status-active' : 'status-inactive'}>
              {userInfo.is_active ? '✅ Hoạt động' : '❌ Không hoạt động'}
            </span>
          </div>
          <div className="profile-field">
            <label>Ngày tạo:</label>
            <span>{userInfo.created_at ? new Date(userInfo.created_at).toLocaleString('vi-VN') : 'N/A'}</span>
          </div>
          <div className="profile-field">
            <label>Đăng nhập gần nhất:</label>
            <span>{userInfo.last_login ? new Date(userInfo.last_login).toLocaleString('vi-VN') : 'Chưa có'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
