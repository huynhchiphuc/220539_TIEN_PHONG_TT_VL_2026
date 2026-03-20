import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <section className="home-hero">
        <div className="home-hero-content">
          <span className="home-badge">COMICCRAFT AI STUDIO</span>
          <h1 className="home-hero-title">Biến bộ ảnh thành truyện tranh có bố cục chuẩn studio</h1>
          <p className="home-description">
            Upload ảnh để tạo comic đầy đủ hoặc tạo khung tự động không cần upload. Hệ thống hỗ trợ bố cục thông minh, preview nhanh và xuất PDF trong một luồng làm việc liền mạch.
          </p>
          <div className="home-hero-actions">
            <Link to="/comic" className="home-cta-btn home-cta-primary">
              Tạo truyện tranh
            </Link>
            <Link to="/auto-frames" className="home-cta-btn home-cta-secondary">
              Tạo khung tự động
            </Link>
          </div>
          <div className="home-hero-metrics">
            <div className="home-metric">
              <strong>2 Chế độ</strong>
              <span>Full Comic và Auto Frame</span>
            </div>
            <div className="home-metric">
              <strong>Cloud + PDF</strong>
              <span>Lưu triển khai và tải xuống ngay</span>
            </div>
            <div className="home-metric">
              <strong>Theme Sync</strong>
              <span>Tối ưu cả dark và light</span>
            </div>
          </div>
        </div>
      </section>

      <section className="home-highlights">
        <article className="highlight-card">
          <h3>Tạo truyện từ ảnh</h3>
          <p>Upload bộ ảnh và để AI tự động sắp xếp panel, phân loại cảnh và xuất thành bộ truyện có bố cục sử dụng được ngay.</p>
        </article>
        <article className="highlight-card">
          <h3>Auto Frames Engine</h3>
          <p>Khởi tạo khung đệ quy với nhiều biến thể bố cục, giữ gutter đồng đều và tỉ lệ khung cân bằng cho mỗi lần tạo.</p>
        </article>
        <article className="highlight-card">
          <h3>Workflow liền mạch</h3>
          <p>Lưu dự án, mở preview và tải PDF trong cùng một trang, giúp bạn test nhanh và ra file để in hoặc chia sẻ.</p>
        </article>
      </section>

      <section className="features">
        <div className="feature-card feature-card-highlight">
          <div className="feature-icon">AI</div>
          <h3>AI Comic Generator</h3>
          <p>Upload nhiều ảnh, AI tự động phân tích và sắp xếp layout. Hỗ trợ 2 chế độ Simple và Advanced, xuất PDF có bìa chuyên nghiệp.</p>
          <Link to="/comic" className="feature-link">Bắt đầu tạo comic</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">FX</div>
          <h3>Auto Frame Generator</h3>
          <p>Tạo bộ khung không cần upload ảnh. Tùy chỉnh số khung, độ ngẫu nhiên, tỉ lệ trang và lưu kết quả chỉ với một chạm.</p>
          <Link to="/auto-frames" className="feature-link">Tạo frame ngay</Link>
        </div>
        <div className="feature-card">
          <div className="feature-icon">ID</div>
          <h3>Google OAuth 2.0</h3>
          <p>Đăng nhập bảo mật với tài khoản Google. Mỗi user có dữ liệu riêng biệt, theo dõi dự án và quản lý tài nguyên theo phiên.</p>
          <Link to="/profile" className="feature-link">Quản lý tài khoản</Link>
        </div>
      </section>
    </div>
  );
};

export default Home;
