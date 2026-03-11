# ComicCraft AI - Database Overview

## 📊 Tổng quan

Database MySQL cho **ComicCraft AI** - Ứng dụng tạo comic/truyện tranh tự động từ ảnh với AI.

### Dự án: 220539_TIEN_PHONG_TT_VL_2026

## 🎯 Mục đích

ComicCraft AI là ứng dụng web cho phép người dùng:
1. Upload nhiều ảnh (png, jpg, jpeg, gif, bmp, webp)
2. Sử dụng AI để phân tích ảnh (shot type, scene, characters)
3. Tự động tạo layout comic với panels
4. Tùy chỉnh cấu hình (resolution, aspect ratio, panels per page, layout mode)
5. Xuất comic thành PDF hoặc images
6. Quản lý sessions và projects

## 📁 Cấu trúc Files

```
database/
├── schema_mysql.sql          # Full database schema
├── README_DATABASE.md        # Hướng dẫn chi tiết
├── mysql_manager.py          # Python connection manager
├── requirements_database.txt # Python dependencies
├── .env.example              # Environment template
└── DATABASE_OVERVIEW.md      # File này
```

## 🗃️ Database Tables

| Table | Mô tả | Records dự kiến |
|-------|-------|----------------|
| users | Người dùng (optional) | 1K - 100K |
| upload_sessions | Sessions upload | 10K - 1M |
| uploaded_images | Ảnh đã upload | 100K - 10M |
| comic_projects | Dự án comic | 10K - 1M |
| comic_pages | Chi tiết pages | 50K - 10M |
| ai_analysis_results | Kết quả AI | 100K - 10M |
| user_preferences | Cấu hình user | 1K - 100K |
| activity_logs | Lịch sử | 100K - 10M |
| system_stats | Thống kê | 365/year |
| api_keys | API keys | 100 - 10K |

## 🔄 Workflow chính

### 1. Upload & Session Creation
```
User uploads images
    ↓
POST /comic/upload
    ↓
Create upload_sessions (session_id: timestamp)
    ↓
Save files to uploads/{session_id}/
    ↓
Insert uploaded_images records
    ↓
Trigger auto-updates total_images & total_size_bytes
    ↓
Return session_id to frontend
```

### 2. Comic Generation
```
User configures settings & clicks Generate
    ↓
POST /comic/generate (session_id + settings)
    ↓
Create comic_projects (status: pending)
    ↓
Background processing:
    1. Load images from session
    2. AI analysis (if enabled)
        - Save to ai_analysis_results
    3. Generate layout
        - Create comic_pages records
    4. Render pages
    5. Combine to PDF/ZIP
    ↓
Update comic_projects (status: completed, result_file_path)
    ↓
Return download URL
```

### 3. Download & Cleanup
```
User downloads result
    ↓
GET /comic/download/{project_id}
    ↓
Log to activity_logs
    ↓
(Auto cleanup after 24h)
Event cleanup expired sessions
```

## 📊 Storage Estimation

| Item | Size | Formula |
|------|------|---------|
| 1 Image | 2-5 MB | Average 3MB |
| 1 Session | 30-150 MB | ~50 images × 3MB |
| 1 Comic Output | 10-50 MB | Depends on pages & resolution |
| Daily Upload | 1-10 GB | ~100-1000 sessions |
| Monthly | 30-300 GB | × 30 |

**Recommended**: 500GB - 2TB storage cho production

## 🔧 Maintenance Tasks

### Daily
- ✅ Event auto-cleanup expired sessions
- ✅ Event update daily stats

### Weekly
- 📊 Review storage usage
- 🧹 Manual cleanup old files if needed

### Monthly
- 💾 Full database backup
- 📈 Analytics review
- 🔄 Optimize tables if needed

## 🚀 Quick Start

### 1. Install MySQL
```bash
# Windows: Download từ https://dev.mysql.com/downloads/mysql/
# Ubuntu/Debian:
sudo apt install mysql-server

# macOS:
brew install mysql
```

### 2. Create Database
```bash
mysql -u root -p < database/schema_mysql.sql
```

### 3. Verify
```sql
USE comiccraft_ai;
SHOW TABLES;
-- Should show 10 tables

SELECT * FROM vw_session_details;
-- Should return 0 rows (empty)
```

### 4. Setup Backend
```bash
# Copy env template
cp database/.env.example backend/.env

# Edit với credentials thực
nano backend/.env

# Install Python dependencies
pip install mysql-connector-python
```

### 5. Test Connection
```bash
cd database
python mysql_manager.py
```

## 📈 Performance Tips

### Indexes được tạo sẵn
- upload_sessions: session_id, user_id, status, created_at
- uploaded_images: session_id, upload_order
- comic_projects: session_id, user_id, status, created_at
- comic_pages: project_id, page_number
- activity_logs: user_id, session_id, action, created_at

### Query Tips
```sql
-- ✅ Tốt: Dùng index
SELECT * FROM upload_sessions WHERE session_id = '1710142800000';

-- ❌ Chậm: Full table scan
SELECT * FROM uploaded_images WHERE original_filename LIKE '%test%';

-- ✅ Tốt: Dùng view đã optimize
SELECT * FROM vw_project_summary WHERE status = 'completed';
```

### Connection Pooling
- Default pool size: 10 connections
- Tăng lên nếu có nhiều concurrent users
- Config trong `.env`: `DB_POOL_SIZE=20`

## 🔐 Security Checklist

- [x] Use parameterized queries (防 SQL injection)
- [x] Create dedicated MySQL user (không dùng root)
- [x] Set proper file permissions
- [x] Enable MySQL SSL (production)
- [x] Regular backups
- [x] Monitor slow queries
- [ ] Implement rate limiting
- [ ] API authentication

## 🆘 Troubleshooting

### Connection refused
```bash
# Check MySQL running
sudo systemctl status mysql

# Start if not running
sudo systemctl start mysql
```

### Access denied
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON comiccraft_ai.* TO 'user'@'localhost';
FLUSH PRIVILEGES;
```

### Event scheduler not running
```sql
SET GLOBAL event_scheduler = ON;
```

### Out of disk space
```bash
# Check usage
du -sh /var/lib/mysql/comiccraft_ai/

# Cleanup old sessions manually
mysql -u root -p comiccraft_ai -e "CALL sp_cleanup_expired_sessions();"
```

## 📚 Resources

- [Database Schema](./schema_mysql.sql)
- [Detailed Guide](./README_DATABASE.md)
- [Python Manager](./mysql_manager.py)
- [MySQL Docs](https://dev.mysql.com/doc/)
- [FastAPI + MySQL](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/huynhchiphuc/220539_TIEN_PHONG_TT_VL_2026/issues)
- Email: support@comiccraft.ai (example)

---
**Version**: 1.0.0  
**Last Updated**: 2026-03-11  
**Database**: MySQL 8.0+  
**Charset**: utf8mb4_unicode_ci
