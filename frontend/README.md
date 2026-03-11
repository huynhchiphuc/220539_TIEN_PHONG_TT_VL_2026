# Frontend React - File Upload App

Ứng dụng React frontend kết nối với FastAPI backend để upload và quản lý files.

## Yêu cầu

- Node.js >= 16
- npm hoặc yarn

## Cấu trúc thư mục

```
frontend/
├── public/              # Static files
├── src/
│   ├── assets/         # Images, fonts, etc.
│   ├── components/     # Reusable components
│   │   ├── FileUpload.jsx
│   │   └── Navbar.jsx
│   ├── pages/          # Page components
│   │   ├── Home.jsx
│   │   └── Upload.jsx
│   ├── services/       # API services
│   │   ├── api.js
│   │   └── fileUploadService.js
│   ├── utils/          # Utility functions
│   │   └── constants.js
│   ├── App.jsx         # Main App component
│   ├── main.jsx        # Entry point
│   └── index.css       # Global styles
├── package.json
└── vite.config.js
```

## Cài đặt

### 1. Cài đặt dependencies (quan trọng!)

**Lưu ý**: Trước tiên, bạn cần dừng dev server nếu đang chạy (Ctrl+C), sau đó chạy:

```bash
cd frontend
npm install axios react-router-dom
```

### 2. Chạy development server

```bash
npm run dev
```

Ứng dụng sẽ chạy tại: http://localhost:5173

## Cấu hình

### API Configuration

Trong file `src/services/api.js`, cấu hình URL backend:

```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

### File Upload Configuration

Trong file `src/utils/constants.js`:

- `MAX_FILE_SIZE`: Kích thước file tối đa (mặc định: 10MB)
- `ALLOWED_FILE_TYPES`: Các loại file được phép upload

## Tính năng

- ✅ Upload file đơn lẻ
- ✅ Hiển thị progress bar khi upload
- ✅ Validate file (size, type)
- ✅ Responsive design
- ✅ Error handling

## Scripts

- `npm run dev` - Chạy development server
- `npm run build` - Build production
- `npm run preview` - Preview production build
- `npm run lint` - Kiểm tra code với ESLint

## Kết nối với Backend

Đảm bảo backend FastAPI đang chạy tại `http://localhost:8000` trước khi sử dụng frontend.

Khởi động backend:
```bash
cd backend/api_base_public
python run_api.py
```

## Công nghệ sử dụng

- **React 19** - UI Library
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client
- **CSS3** - Styling

## Troubleshooting

### Lỗi khi gọi API

- Kiểm tra backend có đang chạy không
- Kiểm tra CORS đã được cấu hình đúng trong backend
- Kiểm tra URL API trong `src/services/api.js`

### Module not found

Chạy lại:
```bash
npm install
```

### Port 5173 đã được sử dụng

Vite sẽ tự động chọn port khác, hoặc bạn có thể cấu hình trong `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    port: 3000
  }
})
```

## License

MIT
