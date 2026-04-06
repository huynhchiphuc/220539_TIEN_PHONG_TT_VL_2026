"""
MySQL Database Manager for ComicCraft AI
Simple connection pool and CRUD operations
"""

import os
from typing import Optional, Dict, Any, List
import mysql.connector
from mysql.connector import pooling, Error
from contextlib import contextmanager
import logging
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MySQLDatabase:
    """MySQL Connection Pool Manager"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "comiccraft_ai",
        user: str = "root",
        password: str = "",
        ssl_mode: str = "DISABLED",
        ssl_ca: str = "",
        pool_size: int = 10
    ):
        try:
            pool_kwargs = {
                "pool_name": "comiccraft_pool",
                "pool_size": pool_size,
                "pool_reset_session": True,
                "host": host,
                "port": port,
                "database": database,
                "user": user,
                "password": password,
                "charset": 'utf8mb4',
                "collation": 'utf8mb4_unicode_ci',
                "autocommit": False,
            }

            if str(ssl_mode).upper() not in ("DISABLED", "OFF", "NONE"):
                pool_kwargs["ssl_disabled"] = False

                if ssl_ca and os.path.exists(ssl_ca):
                    pool_kwargs["ssl_ca"] = ssl_ca
            else:
                pool_kwargs["ssl_disabled"] = True

            self.connection_pool = pooling.MySQLConnectionPool(
                **pool_kwargs
            )
            logger.info(f"✅ MySQL Pool created: comiccraft_pool (size: {pool_size})")
        except Error as e:
            logger.error(f"❌ Error creating pool: {e}")
            raise
    
    @contextmanager
    def get_cursor(self, dictionary=True):
        """Context manager cho cursor"""
        connection = None
        cursor = None
        try:
            connection = self.connection_pool.get_connection()
            cursor = connection.cursor(dictionary=dictionary)
            yield cursor
            connection.commit()
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()


class SessionManager:
    """Quản lý upload sessions"""
    
    def __init__(self, db: MySQLDatabase):
        self.db = db
    
    def create_session(self, session_id: str, user_id: Optional[int] = None) -> int:
        """Tạo session mới"""
        with self.db.get_cursor() as cursor:
            sql = """
                INSERT INTO upload_sessions 
                (session_id, user_id, expires_at)
                VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))
            """
            cursor.execute(sql, (session_id, user_id))
            return cursor.lastrowid
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin session"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM upload_sessions WHERE session_id = %s",
                (session_id,)
            )
            return cursor.fetchone()
    
    def update_session_status(self, session_id: str, status: str):
        """Cập nhật status"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE upload_sessions SET status = %s WHERE session_id = %s",
                (status, session_id)
            )
    
    def add_image(
        self,
        session_id: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
        upload_order: int = 0,
        is_cover: bool = False,
        cover_type: Optional[str] = None
    ) -> int:
        """Thêm ảnh vào session"""
        with self.db.get_cursor() as cursor:
            aspect_ratio = None
            orientation = None
            if width and height:
                aspect_ratio = width / height
                if aspect_ratio < 0.95:
                    orientation = 'portrait'
                elif aspect_ratio > 1.05:
                    orientation = 'landscape'
                else:
                    orientation = 'square'
            
            sql = """
                INSERT INTO uploaded_images 
                (session_id, original_filename, stored_filename, file_path, 
                 file_size_bytes, width, height, aspect_ratio, orientation,
                 upload_order, is_cover, cover_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                session_id, original_filename, stored_filename, file_path,
                file_size, width, height, aspect_ratio, orientation,
                upload_order, is_cover, cover_type
            ))
            return cursor.lastrowid
    
    def get_session_images(self, session_id: str) -> List[Dict[str, Any]]:
        """Lấy danh sách ảnh trong session"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM uploaded_images 
                   WHERE session_id = %s 
                   ORDER BY upload_order""",
                (session_id,)
            )
            return cursor.fetchall()


class ProjectManager:
    """Quản lý comic projects"""
    
    def __init__(self, db: MySQLDatabase):
        self.db = db
    
    def create_project(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> int:
        """Tạo project mới"""
        with self.db.get_cursor() as cursor:
            settings = settings or {}
            sql = """
                INSERT INTO comic_projects 
                (session_id, user_id, layout_mode, panels_per_page, 
                 diagonal_prob, resolution, aspect_ratio, target_dpi,
                 adaptive_layout, smart_crop, reading_direction,
                 analyze_shot_type, classify_characters, classify_scenes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                session_id,
                user_id,
                settings.get('layout_mode', 'advanced'),
                settings.get('panels_per_page', 5),
                settings.get('diagonal_prob', 0.3),
                settings.get('resolution', '2K'),
                settings.get('aspect_ratio', 'auto'),
                settings.get('target_dpi', 150),
                settings.get('adaptive_layout', True),
                settings.get('smart_crop', False),
                settings.get('reading_direction', 'ltr'),
                settings.get('analyze_shot_type', False),
                settings.get('classify_characters', False),
                settings.get('classify_scenes', False)
            ))
            return cursor.lastrowid
    
    def update_project_status(
        self,
        project_id: int,
        status: str,
        **kwargs
    ):
        """Cập nhật status và các fields khác"""
        with self.db.get_cursor() as cursor:
            updates = [f"{key} = %s" for key in kwargs.keys()]
            updates.append("status = %s")
            values = list(kwargs.values()) + [status, project_id]
            
            sql = f"""
                UPDATE comic_projects 
                SET {', '.join(updates)}, updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(sql, values)
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin project"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM comic_projects WHERE id = %s",
                (project_id,)
            )
            return cursor.fetchone()
    
    def get_user_projects(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Lấy danh sách projects của user"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM vw_project_summary 
                   WHERE user_id = %s 
                   ORDER BY created_at DESC 
                   LIMIT %s""",
                (user_id, limit)
            )
            return cursor.fetchall()
    
    def add_page(
        self,
        project_id: int,
        page_number: int,
        page_type: str = 'content',
        panels_count: int = 0,
        layout_structure: Optional[Dict] = None,
        source_image_ids: Optional[List[int]] = None
    ) -> int:
        """Thêm page vào project"""
        with self.db.get_cursor() as cursor:
            sql = """
                INSERT INTO comic_pages 
                (project_id, page_number, page_type, panels_count, 
                 layout_structure, source_image_ids)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                project_id,
                page_number,
                page_type,
                panels_count,
                json.dumps(layout_structure) if layout_structure else None,
                json.dumps(source_image_ids) if source_image_ids else None
            ))
            return cursor.lastrowid


class ActivityLogger:
    """Log hoạt động"""
    
    def __init__(self, db: MySQLDatabase):
        self.db = db
    
    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Ghi log activity"""
        with self.db.get_cursor() as cursor:
            sql = """
                INSERT INTO activity_logs 
                (user_id, session_id, action, resource_type, resource_id, 
                 details, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                user_id,
                session_id,
                action,
                resource_type,
                resource_id,
                json.dumps(details) if details else None,
                ip_address,
                user_agent
            ))


class AIAnalysisManager:
    """Quản lý AI analysis results"""
    
    def __init__(self, db: MySQLDatabase):
        self.db = db
    
    def save_analysis(
        self,
        image_id: int,
        session_id: str,
        analysis_type: str,
        shot_type: Optional[str] = None,
        scene_classification: Optional[str] = None,
        characters_detected: Optional[List[str]] = None,
        face_count: int = 0,
        confidence_score: float = 0.0,
        raw_results: Optional[Dict] = None
    ) -> int:
        """Lưu kết quả AI analysis"""
        with self.db.get_cursor() as cursor:
            payload_common = (
                image_id,
                analysis_type,
                shot_type,
                scene_classification,
                json.dumps(characters_detected) if characters_detected else None,
                face_count,
                confidence_score,
                json.dumps(raw_results) if raw_results else None,
            )

            try:
                sql = """
                    INSERT INTO ai_analysis_results 
                    (image_id, session_id, analysis_type, shot_type, 
                     scene_classification, characters_detected, face_count,
                     confidence_score, raw_results)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    image_id,
                    session_id,
                    analysis_type,
                    shot_type,
                    scene_classification,
                    json.dumps(characters_detected) if characters_detected else None,
                    face_count,
                    confidence_score,
                    json.dumps(raw_results) if raw_results else None,
                ))
            except Error as e:
                # Backward compatibility: một số schema cũ không có cột session_id.
                if getattr(e, 'errno', None) == 1054:
                    sql = """
                        INSERT INTO ai_analysis_results 
                        (image_id, analysis_type, shot_type, 
                         scene_classification, characters_detected, face_count,
                         confidence_score, raw_results)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, payload_common)
                else:
                    raise
            return cursor.lastrowid
    
    def get_session_analysis(self, session_id: str) -> List[Dict[str, Any]]:
        """Lấy tất cả analysis results của session"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM ai_analysis_results 
                   WHERE session_id = %s 
                   ORDER BY created_at""",
                (session_id,)
            )
            return cursor.fetchall()


class UserPreferencesManager:
    """Quản lý user preferences"""
    
    def __init__(self, db: MySQLDatabase):
        self.db = db
    
    def save_preferences(
        self,
        user_id: int,
        preferences: Dict[str, Any]
    ):
        """Lưu hoặc cập nhật preferences"""
        with self.db.get_cursor() as cursor:
            sql = """
                INSERT INTO user_preferences 
                (user_id, default_layout_mode, default_panels_per_page,
                 default_resolution, default_aspect_ratio, default_reading_direction,
                 enable_ai_analysis, auto_save_projects)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    default_layout_mode = VALUES(default_layout_mode),
                    default_panels_per_page = VALUES(default_panels_per_page),
                    default_resolution = VALUES(default_resolution),
                    default_aspect_ratio = VALUES(default_aspect_ratio),
                    default_reading_direction = VALUES(default_reading_direction),
                    enable_ai_analysis = VALUES(enable_ai_analysis),
                    auto_save_projects = VALUES(auto_save_projects),
                    updated_at = NOW()
            """
            cursor.execute(sql, (
                user_id,
                preferences.get('layout_mode', 'advanced'),
                preferences.get('panels_per_page', 5),
                preferences.get('resolution', '2K'),
                preferences.get('aspect_ratio', 'auto'),
                preferences.get('reading_direction', 'ltr'),
                preferences.get('enable_ai_analysis', False),
                preferences.get('auto_save_projects', True)
            ))
    
    def get_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Lấy preferences của user"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_preferences WHERE user_id = %s",
                (user_id,)
            )
            return cursor.fetchone()


def create_database_from_env() -> MySQLDatabase:
    """Tạo DB instance từ environment sử dụng settings chung"""
    from app.config import settings
    return MySQLDatabase(
        host=settings.HOST,
        port=settings.DB_PORT,
        database=settings.DATABASE,
        user=settings.USER,
        password=settings.PASSWORD,
        ssl_mode=settings.DB_SSL_MODE,
        ssl_ca=settings.DB_SSL_CA,
        pool_size=int(os.getenv('DB_POOL_SIZE', 10))
    )


# =====================================================
# EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":
    # Initialize
    db = create_database_from_env()
    
    # Test SessionManager
    session_mgr = SessionManager(db)
    project_mgr = ProjectManager(db)
    activity_log = ActivityLogger(db)
    
    # Create session
    session_id = "1710142800000"
    session_mgr.create_session(session_id)
    print(f"✅ Created session: {session_id}")
    
    # Add images
    image_id = session_mgr.add_image(
        session_id=session_id,
        original_filename="test.jpg",
        stored_filename="abc123.jpg",
        file_path="/uploads/1710142800000/abc123.jpg",
        file_size=1024000,
        width=1920,
        height=1080,
        upload_order=1
    )
    print(f"✅ Added image: {image_id}")
    
    # Create project
    project_id = project_mgr.create_project(
        session_id=session_id,
        settings={
            'layout_mode': 'advanced',
            'panels_per_page': 5,
            'resolution': '2K'
        }
    )
    print(f"✅ Created project: {project_id}")
    
    # Log activity
    activity_log.log(
        action='generate_comic',
        session_id=session_id,
        resource_type='project',
        resource_id=project_id
    )
    print("✅ Logged activity")
