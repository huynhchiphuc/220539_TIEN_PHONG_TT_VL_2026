// API Configuration
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api/v1',
  TIMEOUT: 10000,
};

// File Upload Configuration
export const FILE_CONFIG = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_FILE_TYPES: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ],
};

// Messages
export const MESSAGES = {
  SUCCESS: {
    UPLOAD: 'File uploaded successfully!',
    DELETE: 'File deleted successfully!',
  },
  ERROR: {
    UPLOAD: 'Failed to upload file',
    DELETE: 'Failed to delete file',
    NETWORK: 'Network error. Please try again.',
    FILE_SIZE: 'File size exceeds maximum limit',
    FILE_TYPE: 'File type not supported',
  },
};
