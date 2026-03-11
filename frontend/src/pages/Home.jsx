import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <h1>Welcome to File Upload App</h1>
      <p className="home-description">
        This is a simple file upload application built with React and FastAPI.
      </p>
      <div className="features">
        <div className="feature-card">
          <h3>📁 File Upload</h3>
          <p>Upload files easily and securely</p>
        </div>
        <div className="feature-card">
          <h3>📊 File Management</h3>
          <p>Manage your uploaded files</p>
        </div>
        <div className="feature-card">
          <h3>🔒 Secure</h3>
          <p>Your files are stored safely</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
