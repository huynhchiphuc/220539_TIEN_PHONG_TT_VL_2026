# FastAPI Comic Engine Backend

Dự án này là Backend (lõi xử lý API) của hệ thống tạo truyện tranh tự động. Được xây dựng lại và tối ưu hóa bằng **FastAPI**, tuân thủ nguyên tắc Single Responsibility, tích hợp bảo mật, quản lý file và MySQL.

## ✨ Tính năng chính

- **Xác thực & Bảo mật (Auth):** Hỗ trợ JWT (JSON Web Token) và API Key. Các Endpoint debug và nhạy cảm được bảo vệ bằng quyền Admin.
- **Comic Engine (Lõi xử lý):** Tự động phân tích, chia layout (Grid, Tự động - Advanced Mode) và render trang truyện bằng Pillow & OpenCV.
- **Tích hợp Cloud (Cloudinary):** Tự động đồng bộ và sao lưu dữ liệu hình ảnh lên cloud.
- **Quản lý File & Output:** Xuất truyện tranh kết quả dưới dạng ZIP và PDF, xem trước qua media tokens an toàn.
- **Database Connection Manager:** Quản lý context MySQL an toàn (auto rollback, auto commit) thay vì dùng ORM cồng kềnh.
- **Tài liệu tự động:** Tích hợp Swagger UI (`/docs`).

## 🚀 Công nghệ sử dụng

- Python 3.x
- FastAPI & Uvicorn (ASGI Server)
- MySQL Connector Python (Raw SQL)
- Pydantic (Data validation)
- Pillow, Numpy, OpenCV (Xử lý hình ảnh)
- Python-JOSE & Passlib (JWT & Hashing)

## 📋 Yêu cầu hệ thống

- Đã cài đặt Python (phiên bản 3.8 trở lên).
- Cơ sở dữ liệu MySQL đang hoạt động.

## 🛠️ Hướng dẫn cài đặt

1. **Clone repository:**
   ```bash
   git clone <repository_url>
   cd api_base_public
   ```

2. **Cài đặt các thư viện cần thiết:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình biến môi trường:**
   Tạo file `.env` tại thư mục gốc và cấu hình các thông số sau:
   ```env
   API_KEY=your_api_key_here
   SECRET_KEY=your_secret_key_here
   ALLOW_ORIGINS=["*"]
   TITLE_APP=FastAPI_Base_API
   VERSION_APP=v1

   # Database settings
   HOST=localhost
   DB_PORT=3306
   USER=root
   PASSWORD=your_password
   DATABASE=your_database_name
   DB_SSL_MODE=DISABLED
   DB_SSL_CA=
   ```

## 🏃 Cách chạy dự án

Bạn có thể chạy dự án bằng script `run_api.py`:

```bash
python run_api.py
```

Hoặc sử dụng lệnh uvicorn trực tiếp:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 60074 --reload
```

Deploy trên Render:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Sau khi chạy, bạn có thể truy cập tài liệu API tại:
- Swagger UI: `http://localhost:60074/api/v1/docs`
- ReDoc: `http://localhost:60074/api/v1/redoc`

## 📂 Cấu trúc thư mục

```text
api_base_public/
├── app/
│   ├── config.py         # Quản lý cấu hình dự án (Settings từ .env)
│   ├── main.py           # Điểm khởi đầu của ứng dụng FastAPI
│   ├── db/               # Context manager (query_helpers) kết nối MySQL
│   ├── models/           # DAO Pattern tương tác Database cơ sở (UserDB, BaseDB)
│   ├── routers/          # Các endpoint API (auth, comic, comic_projects, comic_media)
│   ├── security/         # Dependencies bảo mật (JWT, API Key)
│   ├── services/         # Business logic (AutoFrameService, Comic Layout Engine)
│   └── utils/            # Helper functions, log_activity, Validation exception xử lý lỗi
├── .env                  # Cấu hình môi trường (Token exp, Keys, Database)
├── requirements.txt      # Danh sách packages phụ thuộc
├── run_api.py            # Script chạy dev server (.py)
```

## 🛠️ Danh sách API chính

### 🔐 Xác thực & Người dùng (Auth)
- `POST /api/v1/auth/login`: Lấy token JWT.
- `POST /api/v1/auth/register`: Đăng ký tài khoản.

### 🎨 Comic Engine
- `POST /api/v1/comic/upload`: Upload ảnh để xử lý thành session mới.
- `POST /api/v1/comic/generate`: Ra lệnh AI phân tích layout và vẽ truyện.

### 📂 Truy xuất & Download (Media)
- `GET /api/v1/comic/sessions/{session_id}/download-pdf`: Xuất PDF thành phẩm.
- `GET /api/v1/comic/preview/{session_id}`: Xem trước ảnh đã vẽ (serve qua Token `st`).
- `DELETE /api/v1/comic/projects/{session_id}`: Dọn dẹp dự án thừa.

### 📊 Quản lý tài khoản (Dashboard)
- `GET /api/v1/comic/dashboard`: Thống kê số lượng trang, dự án, dung lượng storage.
- `GET /api/v1/comic/activity`: Lịch sử hoạt động (Logs).

## 📄 Giấy phép

Dự án này được phát hành dưới giấy phép MIT.
