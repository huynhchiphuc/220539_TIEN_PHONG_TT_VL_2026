// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1',
  TIMEOUT: 30000,
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

// Comic Configuration
export const COMIC_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024,  // 50MB per image
  MIN_FILE_SIZE: 1024,               // 1KB minimum (too small = corrupted/empty)
  MAX_TOTAL_SIZE: 500 * 1024 * 1024, // 500MB total
  MAX_IMAGES: 100,
  MIN_RESOLUTION: 50,                // 50px minimum (any dimension)
  MAX_RESOLUTION: 12000,             // 12000px maximum (memory bomb prevention)
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'],
};

// Messages
export const MESSAGES = {
  SUCCESS: {
    UPLOAD: 'File tải lên thành công!',
    DELETE: 'File đã xóa thành công!',
  },
  ERROR: {
    UPLOAD: 'Tải file thất bại',
    DELETE: 'Xóa file thất bại',
    NETWORK: 'Lỗi mạng. Vui lòng thử lại.',
    FILE_SIZE: 'Kích thước file vượt quá giới hạn',
    FILE_TYPE: 'Loại file không được hỗ trợ',
  },
};
