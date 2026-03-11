import './Settings.css';

const Settings = () => {
  return (
    <div className="settings-container">
      <div className="settings-card">
        <h1 className="settings-title">⚙️ Cài Đặt</h1>
        
        <div className="settings-section">
          <h2 className="settings-section-title">Tài khoản</h2>
          <div className="settings-item">
            <label>Thay đổi mật khẩu</label>
            <button className="settings-btn">Đổi mật khẩu</button>
          </div>
          <div className="settings-item">
            <label>Cập nhật thông tin</label>
            <button className="settings-btn">Chỉnh sửa</button>
          </div>
        </div>

        <div className="settings-section">
          <h2 className="settings-section-title">Giao diện</h2>
          <div className="settings-item">
            <label>Chế độ tối</label>
            <input type="checkbox" defaultChecked className="settings-toggle" />
          </div>
          <div className="settings-item">
            <label>Ngôn ngữ</label>
            <select className="settings-select">
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>

        <div className="settings-section">
          <h2 className="settings-section-title">API Keys</h2>
          <div className="settings-item">
            <label>Quản lý API Keys</label>
            <button className="settings-btn">Xem API Keys</button>
          </div>
        </div>

        <div className="settings-section danger-zone">
          <h2 className="settings-section-title">Vùng nguy hiểm</h2>
          <div className="settings-item">
            <label>Xóa tài khoản</label>
            <button className="settings-btn-danger">Xóa tài khoản</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
