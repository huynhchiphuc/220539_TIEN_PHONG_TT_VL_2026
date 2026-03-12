import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './Login.css';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Get the page user was trying to access
  const from = location.state?.from?.pathname || '/dashboard';

  // Redirect if already logged in
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const response = await axios.post('http://localhost:60074/api/v1/auth/login', 
          new URLSearchParams({
            username: formData.email,
            password: formData.password
          }),
          {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          }
        );
        
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('token', response.data.access_token);
        if (response.data.user) {
          localStorage.setItem('user', JSON.stringify(response.data.user));
        }
        navigate(from, { replace: true });
      } else {
        // Register
        if (formData.password !== formData.confirmPassword) {
          setError('Mật khẩu xác nhận không khớp');
          setLoading(false);
          return;
        }

        await axios.post('http://localhost:60074/api/v1/auth/register',
          new URLSearchParams({
            username: formData.username,
            email: formData.email,
            password: formData.password
          }),
          {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          }
        );

        // Auto login after register
        const loginResponse = await axios.post('http://localhost:60074/api/v1/auth/login',
          new URLSearchParams({
            username: formData.email,
            password: formData.password
          }),
          {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          }
        );

        localStorage.setItem('access_token', loginResponse.data.access_token);
        localStorage.setItem('token', loginResponse.data.access_token);
        if (loginResponse.data.user) {
          localStorage.setItem('user', JSON.stringify(loginResponse.data.user));
        }
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Đã có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:60074/api/v1/auth/google/login';
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          {/* Header */}
          <div className="login-header">
            <h1 className="login-logo">📚 ComicCraft AI</h1>
            <p className="login-subtitle">Tạo truyện tranh với AI</p>
          </div>

          {/* Toggle Tabs */}
          <div className="login-tabs">
            <button
              className={`tab-btn ${isLogin ? 'active' : ''}`}
              onClick={() => {
                setIsLogin(true);
                setError('');
                setFormData({ email: '', username: '', password: '', confirmPassword: '' });
              }}
            >
              Đăng Nhập
            </button>
            <button
              className={`tab-btn ${!isLogin ? 'active' : ''}`}
              onClick={() => {
                setIsLogin(false);
                setError('');
                setFormData({ email: '', username: '', password: '', confirmPassword: '' });
              }}
            >
              Đăng Ký
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="login-error">
              ⚠️ {error}
            </div>
          )}

          {/* Form */}
          <form className="login-form" onSubmit={handleSubmit}>
            {!isLogin && (
              <div className="form-group">
                <label htmlFor="username">Username</label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  placeholder="Nhập username"
                  value={formData.username}
                  onChange={handleChange}
                  required={!isLogin}
                  autoComplete="username"
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                placeholder="Nhập email của bạn"
                value={formData.email}
                onChange={handleChange}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Mật khẩu</label>
              <input
                type="password"
                id="password"
                name="password"
                placeholder="Nhập mật khẩu"
                value={formData.password}
                onChange={handleChange}
                required
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
            </div>

            {!isLogin && (
              <div className="form-group">
                <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  placeholder="Nhập lại mật khẩu"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required={!isLogin}
                  autoComplete="new-password"
                />
              </div>
            )}

            {isLogin && (
              <div className="form-footer">
                <a href="#" className="forgot-password" onClick={(e) => e.preventDefault()}>
                  Quên mật khẩu?
                </a>
              </div>
            )}

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? '⏳ Đang xử lý...' : (isLogin ? '🔐 Đăng Nhập' : '✨ Tạo Tài Khoản')}
            </button>
          </form>

          {/* Divider */}
          <div className="login-divider">
            <span>HOẶC</span>
          </div>

          {/* Google Login */}
          <button className="google-btn" onClick={handleGoogleLogin}>
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Tiếp tục với Google
          </button>

          {/* Back to Home */}
          <div className="login-footer">
            <button className="back-btn" onClick={() => navigate('/')}>
              ← Về trang chủ
            </button>
          </div>
        </div>

        {/* Background Decoration */}
        <div className="login-bg-decoration">
          <div className="decoration-circle circle-1"></div>
          <div className="decoration-circle circle-2"></div>
          <div className="decoration-circle circle-3"></div>
        </div>
      </div>
    </div>
  );
};

export default Login;
