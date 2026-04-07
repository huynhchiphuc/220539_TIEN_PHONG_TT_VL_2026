"""
Database model classes cho ứng dụng.

Module này cung cấp các lớp truy xuất dữ liệu (Data Access Object)
cho bảng ``users`` và bảng ``base``. Mỗi lớp quản lý một kết nối
MySQL riêng và cần được đóng (`.close()`) sau khi sử dụng.
"""

import logging

import mysql.connector
from mysql.connector import Error

from app.db.mysql_connection import get_mysql_connection

logger = logging.getLogger(__name__)


class BaseDB:
    """Data Access Object cho bảng ``base``.

    Quản lý kết nối MySQL và cung cấp phương thức truy vấn cơ bản.
    Luôn gọi :meth:`close` sau khi sử dụng để giải phóng kết nối.
    """

    def __init__(self):
        """Khởi tạo kết nối MySQL."""
        try:
            self.conn = get_mysql_connection()
            self.cursor = self.conn.cursor(dictionary=True)
            logger.debug("BaseDB: kết nối thành công")
        except Error as exc:
            logger.error("BaseDB: lỗi kết nối — %s", exc)
            self.conn = None
            self.cursor = None

    def get_all_pictures(self) -> list:
        """Lấy toàn bộ bản ghi từ bảng ``base``.

        Returns:
            Danh sách dict chứa dữ liệu các hàng.
        """
        query = "SELECT * FROM `base`"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def close(self) -> None:
        """Đóng cursor và kết nối MySQL."""
        if self.conn:
            self.cursor.close()
            self.conn.close()
            logger.debug("BaseDB: đã đóng kết nối")


class UserDB:
    """Data Access Object cho bảng ``users``.

    Cung cấp các thao tác CRUD cơ bản với bảng người dùng.
    Luôn gọi :meth:`close` sau khi sử dụng để giải phóng kết nối.
    """

    def __init__(self):
        """Khởi tạo kết nối MySQL."""
        try:
            self.conn = get_mysql_connection()
            self.cursor = self.conn.cursor(dictionary=True)
        except Error as exc:
            logger.error("UserDB: lỗi kết nối — %s", exc)
            self.conn = None
            self.cursor = None

    def get_user_by_username(self, username: str):
        """Get user by username"""
        if not self.conn:
            return None
        query = "SELECT * FROM users WHERE username = %s"
        self.cursor.execute(query, (username,))
        return self.cursor.fetchone()

    def get_all(self):
        """Get all users"""
        if not self.conn:
            return []
        query = "SELECT * FROM users"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_user_by_email(self, email: str):
        """Get user by email"""
        if not self.conn:
            return None
        query = "SELECT * FROM users WHERE email = %s"
        self.cursor.execute(query, (email,))
        return self.cursor.fetchone()

    def create_user(self, username: str, email: str, hashed_password: str, full_name: str = None):
        """Create new user"""
        if not self.conn:
            return None
        try:
            query = """
                INSERT INTO users (username, email, password_hash, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            self.cursor.execute(query, (username, email, hashed_password))
            self.conn.commit()
            return self.cursor.lastrowid
        except Error as exc:
            logger.error("UserDB.create_user: lỗi tạo user — %s", exc)
            self.conn.rollback()
            return None

    def update_user_last_login(self, user_id: int):
        """Update user's last login time"""
        if not self.conn:
            return False
        try:
            query = "UPDATE users SET last_login = NOW() WHERE id = %s"
            self.cursor.execute(query, (user_id,))
            self.conn.commit()
            return True
        except Error as exc:
            logger.error("UserDB.update_user_last_login: %s", exc)
            return False

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
