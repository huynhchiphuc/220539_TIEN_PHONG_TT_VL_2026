# 🎨 ComicCraft AI

**ComicCraft AI** là một ứng dụng Web Full-stack giúp người dùng tự động tạo trang truyện tranh (comic) từ các hình ảnh riêng lẻ một cách nhanh chóng và thông minh nhờ sự hỗ trợ của AI. Dự án bao gồm Frontend (React + Vite) trực quan và Backend mạnh mẽ (FastAPI + Python).

---

## ✨ Tính năng chính

- **Tự động tạo Layout Truyện Tranh:** Hỗ trợ sắp xếp ảnh thành các trang truyện với Layout tuỳ chỉnh (Grid, Tự động - Advanced Mode).
- **Tuỳ chỉnh linh hoạt:** 
  - Chọn số lượng khung ảnh (panels) mỗi trang (3-8 panels).
  - Hỗ trợ đa dạng độ phân giải (HD, 2K, 4K).
  - Tỉ lệ khung hình (Aspect Ratio) tuỳ chọn: 16:9, 4:3, A4, hoặc Auto.
- **Tích hợp AI (Optional):** Phân tích góc máy, ánh sáng và tự động phân loại nhân vật (cần cài đặt thêm thư viện máy học).
- **Chỉnh sửa trực tiếp:** Hỗ trợ kéo thả, thay đổi hoặc tải thêm ảnh trực tiếp tại các panel trong lúc chỉnh sửa.
- **Xuất file dễ dàng:** Xem trước các trang truyện, tải xuống dưới định dạng `.ZIP` hoặc xuất `.PDF` nguyên bộ kèm tuỳ biến ảnh bìa trước/sau.
- **Theo dõi dữ liệu:** Tích hợp tùy chọn với cơ sở dữ liệu MySQL để lưu lại các phiên upload, lịch sử tạo truyện, và log hệ thống.

---

## 🛠 Công nghệ sử dụng

**Frontend:**
- **React 19 & Vite 8:** UI động, render siêu tốc và build cực nhanh.
- **Axios:** Xử lý HTTP requests.
- **React Router DOM:** Quản lý điều hướng mượt mà (Login, Dashboard, Admin, ComicGenerator...).

**Backend:**
- **FastAPI (Python):** RESTful API hiệu suất cao.
- **Pillow & OpenCV:** Xử lý ảnh máy tính (cắt, ghép, áp dụng filter layout).
- **MySQL (XAMPP - Tuỳ chọn):** Lưu trữ metadata, session log (qua `mysql-connector-python`).
- Các công cụ AI: Tùy biến với `face-recognition` và `transformers`.

---

## 📂 Cấu trúc dự án

```text
220359_TIEN_PHONG_TT_VL_2026/
├── frontend/               # Giao diện người dùng Web (React + Vite)
│   ├── src/                # Chứa source code Components, Pages (Dashboard, Login, ComicGenerator,...)
│   └── package.json        # Chứa thông tin thư viện frontend
├── backend/                # Logic máy chủ và xử lý API (FastAPI)
│   ├── api_base_public/    # Root thư mục backend chính
│   │   ├── app/            # Source code API (routers/, models/, utils/)
│   │   ├── uploads/        # Thư mục lưu ảnh người dùng tải lên
│   │   └── outputs/        # Thư mục chứa truyện tranh đã tạo
├── database/               # Scripts SQL (schema_mysql.sql) & Database Manager
├── DOCS/                   # Tài liệu chi tiết dự án
├── QUICK_START.md          # Hướng dẫn chạy nhanh
├── SETUP_COMPLETE.md       # Chi tiết cấu hình đã setup xong
└── README.md               # File thông tin chung này
```

---

## 🚀 Hướng dẫn cài đặt và chạy ứng dụng

### 1. Khởi động Backend (FastAPI)

1. Mở Terminal / PowerShell và di chuyển vào thư mục backend:
   ```bash
   cd backend/api_base_public
   ```
2. Cài đặt các thư viện Python (yêu cầu Python 3.9+):
   ```bash
   pip install -r requirements.txt
   ```
   *(Cài thêm AI tính năng: `pip install face-recognition transformers torch` - Tuỳ chọn)*
3. Chạy server (Port mặc định `60074`):
   ```bash
   python run_api.py
   # API Backend sẽ chạy tại: http://localhost:60074/api/v1/
   ```

### 2. Khởi động Frontend (React + Vite)

1. Mở Terminal mới và di chuyển vào thư mục frontend:
   ```bash
   cd frontend
   ```
2. Cài đặt các modules:
   ```bash
   npm install
   ```
3. Chạy môi trường phát triển (Port mặc định `5173`):
   ```bash
   npm run dev
   # App sẽ chạy tại: http://localhost:5173/
   ```

### 3. Cấu hình Cơ sở dữ liệu MySQL (Tuỳ chọn)

Hệ thống vẫn **hoạt động bình thường** sử dụng File Storage (lưu file trực tiếp trên ổ cứng) nếu không có MySQL. Tính năng này dùng để log history.

1. Cài đặt XAMPP và khởi động dịch vụ **MySQL**.
2. Mở MySQL Command Line hoặc phpMyAdmin và tạo CSDL từ file script:
   ```bash
   mysql -u root -p < database/schema_mysql.sql
   ```
   *(Sẽ tự động tạo database `comiccraft_ai` và các cấu trúc tables)*
3. Backend sẽ tự nhận diện kết nối thông qua file biến môi trường hoặc trong file `mysql_manager.py`.

---

## 🎯 Hướng dẫn sử dụng cơ bản

1. Truy cập App tại `http://localhost:5173/`.
2. Click **"Bắt đầu tạo truyện tranh"**.
3. **Upload ảnh**: Tải lên các file ảnh (JPEG, PNG, WebP) muốn tạo truyện.
4. **Cấu hình Layout**: Bảng bên tay phải cấu hình các settings: Mode (Simple/Advanced), Aspect Ratio, Số panel/trang,...
5. Nhấn **"GENERATE COMIC BOOK"**.
6. Hệ thống sẽ gộp và chia layout ảnh tự động. Cuối cùng bạn có thể Download từng trang, hoặc tải nguyên bộ bằng `.ZIP` / `.PDF`.

---

## 📖 API Documentation

Khi Backend đã được khởi chạy, OpenAPI (Swagger UI) sẽ được tự động generate tại:
👉 **[http://localhost:60074/api/v1/docs](http://localhost:60074/api/v1/docs)**

Tại đây bạn có thể kiểm tra danh sách API (`/comic/upload`, `/comic/generate`, `/comic/preview`, ...).

---

## 🐛 Troubleshooting

| Lỗi thường gặp | Giải pháp |
| :--- | :--- |
| Lỗi CORS khi gọi API | Đảm bảo biến `ALLOW_ORIGINS=["*"]` được cấp trong `backend/.env`. |
| Port bị chiếm | Xoá tác vụ trên port bằng PowerShell: <br> `netstat -ano \| findstr :60074` rồi dùng `taskkill /PID <PID> /F` |
| File cấu hình database | Nếu không dùng db, app chỉ ném log (Warning Database logging failed) không gây crash hệ thống chính. |
