# 🚀 Quick Start Guide - ComicCraft AI

## ✅ ĐANG CHẠY:

- **Backend:** http://localhost:60074/api/v1/
- **Frontend:** http://localhost:5173/
- **API Docs:** http://localhost:60074/api/v1/docs

## 🎯 TEST WORKFLOW (Không cần MySQL):

### 1. Truy cập ứng dụng
```
http://localhost:5173/
```

### 2. Click "Bắt đầu tạo truyện tranh"

### 3. Upload ảnh:
- Drag & drop hoặc click để chọn file
- Hỗ trợ: JPG, PNG, GIF, BMP, WebP
- Nhiều ảnh cùng lúc

### 4. Cấu hình Settings:
```
Layout Mode: 
  - Simple: Layout cơ bản, nhanh
  - Advanced: Layout phức tạp với AI

Panels per Page: 3-8 panels

Resolution:
  - HD (1920x1080)
  - 2K (2560x1440)  
  - 4K (3840x2160)

Aspect Ratio: auto / 16:9 / 4:3 / A4

AI Features (Optional):
  ⚠️ Cần cài thêm: face_recognition, transformers
  - Analyze Shot Type
  - Classify Characters
```

### 5. Click "🎨 GENERATE COMIC BOOK"

### 6. Chờ xử lý:
```
1. Uploading... (10% → 35%)
2. Generating layout... (35% → 80%)
3. Finalizing... (80% → 100%)
```

### 7. Xem Preview & Download:
- Xem từng trang
- Download ZIP (tất cả pages)
- Download PDF (với bìa front/back/thank_you - nếu có upload)

## 📦 Storage hiện tại:

Backend đang dùng **File Storage** (không cần MySQL):
```
backend/api_base_public/
├── uploads/              # Ảnh upload từ user
│   └── {session_id}/
│       ├── image_0001.jpg
│       └── ...
└── outputs/              # Kết quả comic đã tạo
    └── {session_id}/
        ├── comic_page_0001.png
        └── ...
```

## 🗄️ MYSQL (Optional - Chưa tích hợp):

### Hiện trạng:
- ✅ Schema có sẵn: `database/schema_mysql.sql`
- ✅ Python manager: `database/mysql_manager.py`
- ❌ MySQL chưa cài trên máy
- ❌ Backend chưa kết nối MySQL

### Lợi ích khi dùng MySQL:
- Lưu trữ sessions lâu dài
- Tracking user activity
- Project management
- AI analysis results
- Statistics & analytics

### Cài MySQL (nếu muốn):

#### Windows:
```powershell
# 1. Download MySQL Installer
# https://dev.mysql.com/downloads/installer/

# 2. Chạy installer → MySQL Server 8.0

# 3. Thêm vào PATH (hoặc dùng MySQL Command Line Client)
```

#### Sau khi cài:
```bash
# Import schema
mysql -u root -p < database/schema_mysql.sql

# Verify
mysql -u root -p
USE comiccraft_ai;
SHOW TABLES;
```

### Tích hợp vào Backend (cần code thêm):

**File cần sửa:**
- `backend/api_base_public/app/routers/comic.py`
  - Import mysql_manager
  - Lưu session vào DB khi upload
  - Lưu project vào DB khi generate
  - Log activity

**Ví dụ:**
```python
from app.database.mysql_manager import MySQLDatabase, SessionManager

# In upload endpoint:
db = MySQLDatabase()
session_mgr = SessionManager(db)
session_mgr.create_session(session_id, user_id=None)

# In generate endpoint:
project_mgr = ProjectManager(db)
project_mgr.create_project(session_id, user_id, settings)
```

## 🐛 Troubleshooting:

### Backend không chạy:
```bash
cd backend/api_base_public
python run_api.py
```

### Frontend không chạy:
```bash
cd frontend
npm run dev
```

### Port bị chiếm:
```powershell
# Kill process trên port 60074
netstat -ano | findstr :60074
taskkill /PID <PID> /F

# Kill process trên port 5173
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### CORS error:
Check `backend/.env`:
```env
ALLOW_ORIGINS=["*"]
```

### File upload lỗi:
Check quyền write folder:
```
backend/api_base_public/uploads/
backend/api_base_public/outputs/
```

## 📊 Test API trực tiếp:

### Upload:
```bash
curl -X POST "http://localhost:60074/api/v1/comic/upload" \
  -F "files=@test1.jpg" \
  -F "files=@test2.jpg"
```

### Generate:
```bash
curl -X POST "http://localhost:60074/api/v1/comic/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "1710142800000",
    "layout_mode": "simple",
    "panels_per_page": 5,
    "resolution": "2K"
  }'
```

### Preview:
```bash
curl "http://localhost:60074/api/v1/comic/preview/1710142800000"
```

---

**Next Steps:**
1. ✅ Test workflow với file storage
2. 🔧 (Optional) Cài MySQL và tích hợp
3. 🎨 Customize UI/UX
4. 🚀 Deploy to production

**Version:** 1.0.0  
**Date:** March 11, 2026
