"""
Tiện ích helper chung dùng trong toàn bộ ứng dụng.

Module này cung cấp context manager quản lý kết nối DB,
hàm logging helper và các tiện ích nhỏ dùng chung.
"""

import logging
from contextlib import contextmanager

from app.db.mysql_connection import get_mysql_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_db_cursor(dictionary: bool = True):
    """Context manager quản lý kết nối và cursor MySQL.

    Tự động commit khi thành công, rollback khi có lỗi,
    và đảm bảo cursor + connection luôn được đóng sau khi dùng.

    Args:
        dictionary: Nếu ``True``, cursor trả về dict thay vì tuple.

    Yields:
        Tuple ``(connection, cursor)`` để sử dụng trong khối ``with``.

    Raises:
        Exception: Bất kỳ exception nào từ câu lệnh SQL sẽ được re-raise
                   sau khi rollback.

    Example::

        with get_db_cursor() as (conn, cursor):
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
    """
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_activity(
    user_id: int,
    session_id: str,
    action: str,
    resource_type: str,
    details: str,
) -> None:
    """Ghi activity log vào bảng ``activity_logs``.

    Không raise exception — lỗi DB chỉ được log ở mức WARNING
    để không làm gián đoạn luồng chính.

    Args:
        user_id: ID của người dùng thực hiện hành động.
        session_id: Session ID liên quan.
        action: Tên hành động (ví dụ: ``'upload'``, ``'generate'``).
        resource_type: Loại tài nguyên (ví dụ: ``'session'``).
        details: Mô tả chi tiết (ghi ngắn gọn).
    """
    from datetime import datetime

    try:
        with get_db_cursor(dictionary=False) as (conn, cursor):
            cursor.execute(
                "INSERT INTO activity_logs "
                "(user_id, session_id, action, resource_type, details, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, session_id, action, resource_type, details, datetime.now()),
            )
    except Exception as exc:
        logger.warning("Activity log failed [%s/%s]: %s", action, session_id, exc)
