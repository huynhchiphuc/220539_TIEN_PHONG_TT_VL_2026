import { Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  const location = useLocation();

  useEffect(() => {
    if (!token) {
      // Show alert when trying to access protected route without login
      alert('⚠️ Vui lòng đăng nhập để truy cập tính năng này!');
    }
  }, [token]);

  if (!token) {
    // Redirect to home page if not authenticated
    return <Navigate to="/" replace state={{ from: location }} />;
  }

  return children;
};

export default ProtectedRoute;
