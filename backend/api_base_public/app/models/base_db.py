import mysql.connector
from mysql.connector import Error
from app.config import settings
import os
from app.db.mysql_connection import get_mysql_connection


class BaseDB:
    def __init__(self):
        try:
            self.conn = get_mysql_connection()
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Kết nối thành công!")
        except Error as e:
            print(f"❌ Lỗi kết nối: {e}")
            self.conn = None

    def get_all_pictures(self):
        query = "SELECT * FROM `base`"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("🔒 Đã đóng kết nối.")


class UserDB:
    """Database operations for users table"""
    def __init__(self):
        try:
            self.conn = get_mysql_connection()
            self.cursor = self.conn.cursor(dictionary=True)
        except Error as e:
            print(f"❌ Lỗi kết nối UserDB: {e}")
            self.conn = None

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
        except Error as e:
            print(f"❌ Lỗi tạo user: {e}")
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
        except Error as e:
            print(f"❌ Lỗi update last_login: {e}")
            return False

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
