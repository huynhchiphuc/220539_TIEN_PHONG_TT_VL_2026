-- =====================================================
-- DATABASE SCHEMA FOR COMICCRAFT AI
-- Hệ thống tạo Comic/Truyện tranh tự động từ ảnh với AI
-- Project: 220539_TIEN_PHONG_TT_VL_2026
-- =====================================================

-- Tạo database
CREATE DATABASE IF NOT EXISTS comiccraft_ai 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE comiccraft_ai;

-- =====================================================
-- TABLE: users - Quản lý người dùng (Optional - nếu có auth)
-- =====================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) DEFAULT NULL,
    avatar_url VARCHAR(500) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: upload_sessions - Session upload ảnh
-- =====================================================
CREATE TABLE upload_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE, -- Timestamp-based session ID
    user_id INT DEFAULT NULL, -- NULL nếu không có auth
    total_images INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    status ENUM('uploading', 'uploaded', 'processing', 'completed', 'failed', 'expired') DEFAULT 'uploading',
    upload_folder_path VARCHAR(500) DEFAULT NULL,
    expires_at TIMESTAMP NULL, -- Session hết hạn sau 24h
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: uploaded_images - Chi tiết các ảnh đã upload
-- =====================================================
CREATE TABLE uploaded_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    stored_filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size_bytes INT DEFAULT 0,
    width INT DEFAULT NULL,
    height INT DEFAULT NULL,
    aspect_ratio FLOAT DEFAULT NULL,
    orientation ENUM('portrait', 'landscape', 'square') DEFAULT NULL,
    mime_type VARCHAR(100) DEFAULT NULL,
    upload_order INT DEFAULT 0, -- Thứ tự upload
    is_cover BOOLEAN DEFAULT FALSE, -- Có phải ảnh bìa không
    cover_type ENUM('front', 'back', 'thank_you') DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES upload_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_upload_order (upload_order),
    INDEX idx_is_cover (is_cover)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: comic_projects - Dự án comic đã tạo
-- =====================================================
CREATE TABLE comic_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INT DEFAULT NULL,
    project_name VARCHAR(255) DEFAULT NULL,
    
    -- Layout settings (JSON cho detailed config)
    layout_mode ENUM('advanced', 'simple') DEFAULT 'advanced',
    panels_per_page INT DEFAULT 5,
    diagonal_prob FLOAT DEFAULT 0.3,
    adaptive_layout BOOLEAN DEFAULT TRUE,
    smart_crop BOOLEAN DEFAULT FALSE,
    reading_direction ENUM('ltr', 'rtl') DEFAULT 'ltr',
    single_page_mode BOOLEAN DEFAULT FALSE,
    
    -- Resolution & Quality
    resolution VARCHAR(10) DEFAULT '2K', -- 1K, 2K, 4K
    aspect_ratio VARCHAR(20) DEFAULT 'auto', -- auto, 16:9, 9:16, 3:4, etc.
    target_dpi INT DEFAULT 150,
    margin INT DEFAULT 40,
    gap INT DEFAULT 30,
    
    -- AI Analysis settings
    analyze_shot_type BOOLEAN DEFAULT FALSE,
    classify_characters BOOLEAN DEFAULT FALSE,
    classify_scenes BOOLEAN DEFAULT FALSE,
    use_face_recognition BOOLEAN DEFAULT FALSE,
    scene_classification_method VARCHAR(20) DEFAULT 'rule_based', -- rule_based, ai_model, hybrid
    
    -- Output info
    output_folder_path VARCHAR(500) DEFAULT NULL,
    total_pages INT DEFAULT 0,
    output_format VARCHAR(20) DEFAULT 'pdf', -- pdf, zip, images
    
    -- Processing
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    processing_started_at TIMESTAMP NULL,
    processing_completed_at TIMESTAMP NULL,
    processing_time_seconds INT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    
    -- Storage
    result_file_path VARCHAR(1000) DEFAULT NULL,
    result_file_size_bytes BIGINT DEFAULT NULL,
    download_url VARCHAR(1000) DEFAULT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES upload_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: comic_pages - Chi tiết từng trang comic
-- =====================================================
CREATE TABLE comic_pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    page_number INT NOT NULL,
    page_type VARCHAR(20) DEFAULT 'content', -- cover_front, cover_back, thank_you, content
    
    -- Layout info
    panels_count INT DEFAULT 0,
    layout_structure TEXT DEFAULT NULL, -- JSON: [{x, y, w, h, image_id}, ...]
    
    -- Image source
    source_image_ids TEXT DEFAULT NULL, -- JSON array of uploaded_images.id
    
    -- Output
    output_image_path VARCHAR(1000) DEFAULT NULL,
    width INT DEFAULT NULL,
    height INT DEFAULT NULL,
    file_size_bytes INT DEFAULT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES comic_projects(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_page_number (page_number),
    INDEX idx_page_type (page_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: ai_analysis_results - Kết quả phân tích AI
-- =====================================================
CREATE TABLE ai_analysis_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_id INT NOT NULL, -- Tham chiếu uploaded_images
    
    -- Shot Type Analysis
    shot_type VARCHAR(50) DEFAULT NULL, -- close_up, medium_shot, long_shot, extreme_close_up, etc.
    shot_type_confidence FLOAT DEFAULT NULL,
    
    -- Scene Classification
    scene_type VARCHAR(100) DEFAULT NULL, -- indoor, outdoor, action, dialogue, etc.
    scene_confidence FLOAT DEFAULT NULL,
    scene_tags TEXT DEFAULT NULL, -- JSON array
    
    -- Character Detection
    characters_detected INT DEFAULT 0,
    character_info TEXT DEFAULT NULL, -- JSON: [{name, bbox, confidence, face_encodings}, ...]
    
    -- Face Recognition
    faces_detected INT DEFAULT 0,
    face_embeddings TEXT DEFAULT NULL, -- JSON
    
    -- Other metadata
    dominant_colors TEXT DEFAULT NULL, -- JSON
    brightness FLOAT DEFAULT NULL,
    contrast FLOAT DEFAULT NULL,
    
    analysis_method VARCHAR(50) DEFAULT NULL, -- rule_based, ai_model, hybrid
    processing_time_ms INT DEFAULT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (image_id) REFERENCES uploaded_images(id) ON DELETE CASCADE,
    INDEX idx_image_id (image_id),
    INDEX idx_shot_type (shot_type),
    INDEX idx_scene_type (scene_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: user_preferences - Cấu hình mặc định của user
-- =====================================================
CREATE TABLE user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    
    -- Default settings (JSON format)
    default_layout_settings TEXT DEFAULT NULL,
    default_resolution VARCHAR(10) DEFAULT '2K',
    default_aspect_ratio VARCHAR(20) DEFAULT 'auto',
    default_panels_per_page INT DEFAULT 5,
    
    -- Feature preferences
    auto_analyze_enabled BOOLEAN DEFAULT FALSE,
    auto_save_projects BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: activity_logs - Lịch sử hoạt động
-- =====================================================
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    session_id VARCHAR(100) DEFAULT NULL,
    action VARCHAR(100) NOT NULL, -- upload, generate, download, delete, etc.
    resource_type VARCHAR(50) DEFAULT NULL, -- session, project, image
    resource_id INT DEFAULT NULL,
    details TEXT DEFAULT NULL, -- JSON
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: system_stats - Thống kê hệ thống
-- =====================================================
CREATE TABLE system_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,
    total_sessions INT DEFAULT 0,
    total_uploads INT DEFAULT 0,
    total_comics_generated INT DEFAULT 0,
    total_images_processed INT DEFAULT 0,
    total_storage_bytes BIGINT DEFAULT 0,
    active_users INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLE: api_keys - API Key management (nếu cần)
-- =====================================================
CREATE TABLE api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    key_name VARCHAR(100) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit INT DEFAULT 100, -- Request per hour
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_api_key (api_key),
    INDEX idx_user_id (user_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- INSERT SAMPLE DATA
-- =====================================================

-- Insert sample user (for testing)
INSERT INTO users (email, username, password_hash) VALUES
('demo@comiccraft.ai', 'Demo User', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5d/3oW/16pM.u');

-- =====================================================
-- STORED PROCEDURES & TRIGGERS
-- =====================================================

-- Trigger: Auto-update upload_sessions when image uploaded
DELIMITER //

CREATE TRIGGER trg_update_session_on_image_upload
AFTER INSERT ON uploaded_images
FOR EACH ROW
BEGIN
    UPDATE upload_sessions 
    SET total_images = total_images + 1,
        total_size_bytes = total_size_bytes + NEW.file_size_bytes,
        updated_at = CURRENT_TIMESTAMP
    WHERE session_id = NEW.session_id;
END//

DELIMITER ;

-- Stored Procedure: Lấy thống kê project
DELIMITER //

CREATE PROCEDURE sp_get_project_stats(IN p_project_id INT)
BEGIN
    SELECT 
        cp.id,
        cp.project_name,
        cp.status,
        cp.total_pages,
        cp.processing_time_seconds,
        us.total_images,
        us.total_size_bytes,
        COUNT(DISTINCT cpg.id) as actual_pages_count,
        cp.created_at,
        cp.processing_completed_at
    FROM comic_projects cp
    JOIN upload_sessions us ON cp.session_id = us.session_id
    LEFT JOIN comic_pages cpg ON cp.id = cpg.project_id
    WHERE cp.id = p_project_id
    GROUP BY cp.id;
END//

DELIMITER ;

-- Stored Procedure: Cleanup expired sessions
DELIMITER //

CREATE PROCEDURE sp_cleanup_expired_sessions()
BEGIN
    -- Xóa sessions hết hạn (> 24h và không có project completed)
    DELETE us FROM upload_sessions us
    LEFT JOIN comic_projects cp ON us.session_id = cp.session_id
    WHERE us.expires_at < NOW()
    AND (cp.status IS NULL OR cp.status NOT IN ('completed', 'processing'));
END//

DELIMITER ;

-- Event: Auto-cleanup expired sessions
CREATE EVENT IF NOT EXISTS evt_cleanup_expired_sessions
ON SCHEDULE EVERY 6 HOUR
STARTS CURRENT_TIMESTAMP
DO
    CALL sp_cleanup_expired_sessions();

-- Event: Update daily stats
CREATE EVENT IF NOT EXISTS evt_update_daily_stats
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
    INSERT INTO system_stats (
        stat_date,
        total_sessions,
        total_uploads,
        total_comics_generated,
        total_images_processed,
        active_users
    )
    SELECT 
        CURDATE(),
        COUNT(DISTINCT session_id),
        (SELECT COUNT(*) FROM uploaded_images WHERE DATE(created_at) = CURDATE()),
        (SELECT COUNT(*) FROM comic_projects WHERE status = 'completed' AND DATE(processing_completed_at) = CURDATE()),
        (SELECT COUNT(*) FROM uploaded_images WHERE DATE(created_at) = CURDATE()),
        (SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE DATE(created_at) = CURDATE())
    FROM upload_sessions
    WHERE DATE(created_at) = CURDATE()
    ON DUPLICATE KEY UPDATE
        total_sessions = VALUES(total_sessions),
        total_uploads = VALUES(total_uploads),
        total_comics_generated = VALUES(total_comics_generated),
        total_images_processed = VALUES(total_images_processed),
        active_users = VALUES(active_users),
        updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- VIEWS
-- =====================================================

-- View: Project summary với details
CREATE VIEW vw_project_summary AS
SELECT 
    cp.id as project_id,
    cp.project_name,
    cp.session_id,
    u.username,
    u.email,
    cp.layout_mode,
    cp.panels_per_page,
    cp.resolution,
    cp.aspect_ratio,
    cp.status,
    cp.total_pages,
    cp.processing_time_seconds,
    us.total_images,
    us.total_size_bytes,
    cp.result_file_path,
    cp.download_url,
    cp.created_at,
    cp.processing_completed_at,
    TIMESTAMPDIFF(MINUTE, cp.created_at, COALESCE(cp.processing_completed_at, NOW())) as total_minutes
FROM comic_projects cp
JOIN upload_sessions us ON cp.session_id = us.session_id
LEFT JOIN users u ON cp.user_id = u.id;

-- View: Session details
CREATE VIEW vw_session_details AS
SELECT 
    us.id,
    us.session_id,
    us.user_id,
    u.username,
    u.email,
    us.total_images,
    us.total_size_bytes,
    us.status,
    us.created_at,
    us.expires_at,
    COUNT(DISTINCT cp.id) as projects_count,
    MAX(cp.created_at) as last_project_at
FROM upload_sessions us
LEFT JOIN users u ON us.user_id = u.id
LEFT JOIN comic_projects cp ON us.session_id = cp.session_id
GROUP BY us.id;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Composite indexes
CREATE INDEX idx_sessions_user_status ON upload_sessions(user_id, status, created_at);
CREATE INDEX idx_projects_user_status ON comic_projects(user_id, status, created_at);
CREATE INDEX idx_images_session_order ON uploaded_images(session_id, upload_order);
CREATE INDEX idx_pages_project_number ON comic_pages(project_id, page_number);
CREATE INDEX idx_logs_user_created ON activity_logs(user_id, created_at);

-- =====================================================
-- SECURITY
-- =====================================================

-- Tạo user MySQL riêng cho application (recommended)
-- CREATE USER 'comiccraft_app'@'localhost' IDENTIFIED BY 'strong_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON comiccraft_ai.* TO 'comiccraft_app'@'localhost';
-- FLUSH PRIVILEGES;

-- =====================================================
-- END OF SCHEMA
-- =====================================================
