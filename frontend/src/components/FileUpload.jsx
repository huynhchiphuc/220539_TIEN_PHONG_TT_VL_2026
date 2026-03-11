import { useState } from 'react';
import { fileUploadService } from '../services/fileUploadService';
import { FILE_CONFIG, MESSAGES } from '../utils/constants';
import './FileUpload.css';

const FileUpload = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const validateFile = (file) => {
    if (file.size > FILE_CONFIG.MAX_FILE_SIZE) {
      setMessage({ type: 'error', text: MESSAGES.ERROR.FILE_SIZE });
      return false;
    }
    if (!FILE_CONFIG.ALLOWED_FILE_TYPES.includes(file.type)) {
      setMessage({ type: 'error', text: MESSAGES.ERROR.FILE_TYPE });
      return false;
    }
    return true;
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && validateFile(file)) {
      setSelectedFile(file);
      setMessage({ type: '', text: '' });
    } else {
      setSelectedFile(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage({ type: 'error', text: 'Please select a file first' });
      return;
    }

    setUploading(true);
    setMessage({ type: '', text: '' });

    try {
      await fileUploadService.uploadFile(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setMessage({ type: 'success', text: MESSAGES.SUCCESS.UPLOAD });
      setSelectedFile(null);
      setUploadProgress(0);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || MESSAGES.ERROR.UPLOAD,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-upload-container">
      <h2>Upload File</h2>
      
      <div className="file-input-wrapper">
        <input
          type="file"
          onChange={handleFileSelect}
          disabled={uploading}
          className="file-input"
        />
      </div>

      {selectedFile && (
        <div className="file-info">
          <p>Selected file: {selectedFile.name}</p>
          <p>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
      )}

      {uploading && (
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${uploadProgress}%` }}>
            {uploadProgress}%
          </div>
        </div>
      )}

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        className="upload-button"
      >
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
    </div>
  );
};

export default FileUpload;
