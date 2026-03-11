import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <div className="home-hero">
        <h1 className="home-hero-title">📚 ComicCraft AI</h1>
        <p className="home-description">
          Tạo truyện tranh, manga chuyên nghiệp từ ảnh với AI. Tự động phân tích nhân vật, cảnh, xếp layout thông minh và xuất PDF đẹp mắt.
        </p>
        <Link to="/comic" className="home-cta-btn">
          🚀 Tạo truyện tranh ngay
        </Link>
      </div>

      <div className="features">
        <div className="feature-card feature-card-highlight">
          <div className="feature-icon">🎨</div>
          <h3>AI Comic Generator</h3>
          <p>Upload nhiều ảnh, AI tự động phân tích và sắp xếp layout. Hỗ trợ 2 chế độ: Simple & Advanced. Xuất PDF có bìa chuyên nghiệp.</p>
          <Link to="/comic" className="feature-link">Tạo ngay →</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📚</div>
          <h3>Quản lý Dự Án</h3>
          <p>Lưu trữ và quản lý tất cả truyện tranh đã tạo. Xem preview, tải xuống, xóa dễ dàng.</p>
          <Link to="/upload" className="feature-link">Dự án →</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🔐</div>
          <h3>Google OAuth 2.0</h3>
          <p>Đăng nhập bảo mật với tài khoản Google. Mỗi user có dữ liệu riêng biệt và được bảo vệ.</p>
          <Link to="/profile" className="feature-link">Profile →</Link>
        </div>
      </div>
    </div>
  );
};

export default Home;
