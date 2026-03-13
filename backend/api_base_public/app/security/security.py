# app/security/security.py

from fastapi import Header, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.config import settings
from app.utils.mysql_connection import get_mysql_connection

from fastapi import Security  # noqa: E402
from fastapi.security import APIKeyHeader  # noqa: E402

# === Config ===
API_KEY = settings.API_KEY
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


# Xác định header `Authorization`
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header != f"Bearer {settings.API_KEY}":
        raise HTTPException(status_code=403, detail="API Key không hợp lệ!")
    return api_key_header


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


# ✅ Xác định user từ Query parameter hoặc Header (dành cho file download, URL direct)
def get_current_user_optional(token: str = None, token_header: str = Depends(oauth2_scheme_optional)):
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


# ✅ Xác thực JWT (dù có đăng nhập hay không)
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # return payload chứa: sub, role, v.v.
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc hết hạn",
        )


# ✅ Kiểm tra quyền admin (dùng cho admin routes)
def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Verify user has admin role"""
    import mysql.connector
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
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
