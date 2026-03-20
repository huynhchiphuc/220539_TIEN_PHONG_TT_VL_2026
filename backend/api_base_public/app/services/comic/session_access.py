from typing import Optional

from fastapi import HTTPException

from app.db.mysql_connection import get_mysql_connection


def get_session_owner(session_id: str) -> Optional[int]:
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM upload_sessions WHERE session_id = %s LIMIT 1", (session_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row.get("user_id") if row else None
    except Exception:
        return None


def ensure_session_owner(session_id: str, user: dict) -> None:
    owner_id = get_session_owner(session_id)
    if owner_id is None or owner_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập session này")
