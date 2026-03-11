import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <div className="home-hero">
        <h1 className="home-hero-title">📚 TiênPhong AI Platform</h1>
        <p className="home-description">
          Nền tảng ứng dụng AI thế hệ mới — Tạo truyện tranh tự động từ ảnh với công nghệ AI tiên tiến.
        </p>
        <Link to="/comic" className="home-cta-btn">
          🚀 Bắt đầu tạo truyện tranh
        </Link>
      </div>

      <div className="features">
        <div className="feature-card feature-card-highlight">
          <div className="feature-icon">📚</div>
          <h3>ComicCraft AI</h3>
          <p>Tạo truyện tranh tự động từ ảnh với AI phân tích nhân vật, cảnh và layout thông minh. Hỗ trợ xuất PDF có bìa.</p>
          <Link to="/comic" className="feature-link">Dùng ngay →</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📁</div>
          <h3>Quản lý File</h3>
          <p>Upload và quản lý file dễ dàng, an toàn với API bảo mật theo tiêu chuẩn.</p>
          <Link to="/upload" className="feature-link">Upload →</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🔒</div>
          <h3>Bảo mật API</h3>
          <p>Xác thực API Key, JWT Token — bảo vệ dữ liệu theo chuẩn enterprise.</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
