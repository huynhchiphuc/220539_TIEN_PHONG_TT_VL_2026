# FastAPI Base Public API

Dự án này là một bản mẫu (template) cơ bản cho việc xây dựng API sử dụng FastAPI, tích hợp sẵn các tính năng quan trọng như xác thực người dùng (JWT), quản lý file và kết nối cơ sở dữ liệu MySQL.

## ✨ Tính năng chính

- **Xác thực và phân quyền (Auth):** Hỗ trợ đăng ký, đăng nhập và bảo mật bằng JWT (JSON Web Token) cùng với xác thực qua API Key.
- **Quản lý File:** API upload, download và xem trực tiếp (preview) các tệp tin (hình ảnh, video, audio).
- **Cơ sở dữ liệu:** Tích hợp SQLAlchemy và kết nối MySQL.
- **Cấu trúc Modular:** Phân chia thư mục rõ ràng (routers, models, security, utils) giúp dễ dàng mở rộng.
- **Tài liệu tự động:** Tích hợp sẵn Swagger UI và ReDoc.
- **CORS:** Cấu hình sẵn Middleware xử lý Cross-Origin Resource Sharing.

## 🚀 Công nghệ sử dụng

- Python 3.x
- FastAPI
- Uvicorn (ASGI Server)
- MySQL Connector
- Pydantic (Data validation)
- Python-JOSE (JWT)
- SQLAlchemy

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
│   ├── models/          # Định nghĩa các mô hình dữ liệu (Database & Pydantic)
│   ├── routers/         # Định nghĩa các endpoint API
│   ├── security/        # Xử lý xác thực (JWT, API Key)
│   ├── utils/           # Các công cụ tiện ích (Download, file handling)
│   ├── config.py        # Cấu hình ứng dụng từ .env
│   └── main.py          # Điểm khởi đầu của ứng dụng
├── .env                 # File cấu hình môi trường (không commit lên git)
├── requirements.txt     # Danh sách thư viện phụ thuộc
├── run_api.py           # Script chạy ứng dụng
└── start.sh             # Script khởi động trên Linux
```

## 🛠️ Danh sách API chính

### 🔐 Authentication
- `POST /api/v1/auth/register`: Đăng ký tài khoản mới.
- `POST /api/v1/auth/login`: Đăng nhập lấy token.
- `GET /api/v1/auth/check`: Kiểm tra trạng thái đăng nhập.

### 📁 File Upload
- `POST /api/v1/upload-file/upload/`: Tải tệp lên hệ thống.
- `GET /api/v1/upload-file/download/{filename}`: Tải tệp về máy.
- `GET /api/v1/upload-file/view/{filename}`: Xem trước tệp (hình ảnh, video...).

### ⚙️ Base API
- `POST /api/v1/base/base-url/`: API mẫu sử dụng xác thực JWT.
- `POST /api/v1/base/base-api/`: API mẫu sử dụng xác thực API Key.

## 📄 Giấy phép

Dự án này được phát hành dưới giấy phép MIT.
