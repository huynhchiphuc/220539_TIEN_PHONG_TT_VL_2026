"""
Module bảo mật: xác thực JWT và API Key cho ứng dụng.

Cung cấp các Dependency FastAPI để bảo vệ endpoint:
- ``verify_api_key``: Xác thực qua API Key trong header Authorization.
- ``get_current_user``: Xác thực JWT bắt buộc.
- ``get_current_user_optional``: Xác thực JWT tùy chọn (query param hoặc header).
- ``get_admin_user``: Kiểm tra quyền admin từ database.
"""

import mysql.connector

from fastapi import Header, HTTPException, status, Depends, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError

from app.config import settings
from app.db.mysql_connection import get_mysql_connection

# === Config ===
API_KEY = settings.API_KEY
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


# Xác định header `Authorization`
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """Dependency xác thực API Key trong header ``Authorization``.

    Giá trị header phải có dạng ``Bearer <API_KEY>``.

    Returns:
        Chuỗi header nếu hợp lệ.

    Raises:
        HTTPException 403: Nếu API Key không khớp.
    """
    if api_key_header != f"Bearer {settings.API_KEY}":
        raise HTTPException(status_code=403, detail="API Key không hợp lệ!")
    return api_key_header


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_current_user_optional(token: str = None, token_header: str = Depends(oauth2_scheme_optional)) -> dict:
    """Dependency xác thực JWT tùy chọn (query param hoặc header).

    Cho phép truyền ``token`` qua query param để hỗ trợ URL trực tiếp
    (download file, preview ảnh).

    Returns:
        Dict payload JWT nếu hợp lệ.

    Raises:
        HTTPException 401: Nếu không có token hoặc token không hợp lệ.
    """
    actual_token = token or token_header
    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không được cung cấp",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency xác thực JWT bắt buộc từ header ``Authorization: Bearer <token>``.

    Returns:
        Dict payload JWT gồm: ``id``, ``username``, ``email``, ``role``.

    Raises:
        HTTPException 401: Nếu token không hợp lệ hoặc hết hạn.
    """ 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # return payload chứa: sub, role, v.v.
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc hết hạn",
        )


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency kiểm tra quyền admin từ database.

    Xác nhận user hiện tại có ``role = 'admin'`` trong bảng ``users``.

    Returns:
        Dict thông tin user nếu có quyền admin.

    Raises:
        HTTPException 403: Nếu user không có quyền admin.
        HTTPException 500: Nếu xảy ra lỗi database.
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users WHERE id = %s", (current_user["id"],))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user_data or user_data.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="🚫 Bạn không có quyền truy cập trang này! (Cần quyền Admin)"
            )

        return current_user
    except mysql.connector.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {str(exc)}")
