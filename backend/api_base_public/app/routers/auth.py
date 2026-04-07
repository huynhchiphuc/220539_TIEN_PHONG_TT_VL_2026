"""
Router xảc thực người dùng: đăng ký, đăng nhập, Google OAuth 2.0.

Module này xử lý:
- Đăng ký / đăng nhập bằng username + password (JWT).
- Đăng nhập bằng Google OAuth 2.0.
- Quản lý API key của user.
- Đổi mật khẩu và cập nhật profile.
- Rate limiting cho endpoint đăng nhập.
"""

from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import httpx
import os
import secrets
import re
import mysql.connector
import threading

from app.config import settings
from app.security.security import get_current_user, get_admin_user
from app.models.base_db import UserDB
from app.db.mysql_connection import get_mysql_connection

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

LOGIN_MAX_ATTEMPTS = settings.LOGIN_MAX_ATTEMPTS
LOGIN_WINDOW_MINUTES = settings.LOGIN_WINDOW_MINUTES
LOGIN_LOCK_MINUTES = settings.LOGIN_LOCK_MINUTES

# In-memory stores for rate limiting and one-time OAuth exchanges.
# Lưu ý: dữ liệu này sẽ mất khi server restart.
LOGIN_ATTEMPTS: dict = {}
OAUTH_EXCHANGE_STORE: dict = {}
AUTH_LOCK = threading.Lock()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1/auth/google/callback",
).strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://huynhchiphuc-comic.vercel.app").strip()

# Khi chạy trên Render, ưu tiên các biến RENDER-specific.
if os.getenv("RENDER"):
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI_RENDER", GOOGLE_REDIRECT_URI)
    FRONTEND_URL = os.getenv("FRONTEND_URL_RENDER", FRONTEND_URL)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# Database connection helper
def get_db_connection():
    """Tạo và trả về kết nối MySQL mới."""
    return get_mysql_connection()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu plain text với hash bcrypt.

    Args:
        plain_password: Mật khẩu gốc người dùng nhập.
        hashed_password: Hash được lưu trong database.

    Returns:
        ``True`` nếu khớp, ``False`` nếu không.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Tạo hash bcrypt từ mật khẩu plain text.

    Args:
        password: Mật khẩu cần hash.

    Returns:
        Chuỗi hash bcrypt.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Tạo JWT access token với thời gian hết hạn cấu hình.

    Args:
        data: Dict payload đưa vào token (ví dụ: ``id``, ``username``, ``role``).

    Returns:
        Chuỗi JWT đã ký.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _login_key(username: str, request: Request) -> str:
    """Tạo khóa duy nhất cho rate limiting dựa trên username + IP.

    Args:
        username: Tên đăng nhập (email hoặc username).
        request: FastAPI Request object để lấy IP.

    Returns:
        Chuỗi ``"username|ip"``.
    """
    ip = request.client.host if request.client else "unknown"
    return f"{username.lower().strip()}|{ip}"


def _is_login_locked(key: str) -> tuple[bool, int]:
    """Kiểm tra xem account có đang bị khóa do quá nhiều lần sai không.

    Args:
        key: Khóa rate limit tạo bởi :func:`_login_key`.

    Returns:
        Tuple ``(is_locked, minutes_remaining)``.
    """
    now = datetime.utcnow()
    entry = LOGIN_ATTEMPTS.get(key)
    if not entry:
        return False, 0

    lock_until = entry.get("lock_until")
    if lock_until and now < lock_until:
        remaining = int((lock_until - now).total_seconds() // 60) + 1
        return True, max(1, remaining)

    if entry.get("window_start") and now - entry["window_start"] > timedelta(minutes=LOGIN_WINDOW_MINUTES):
        LOGIN_ATTEMPTS.pop(key, None)
    return False, 0


def _record_login_failure(key: str) -> None:
    """Ghi nhận lần đăng nhập thất bại và khóa nếu vượt ngưỡng.

    Args:
        key: Khóa rate limit tạo bởi :func:`_login_key`.
    """
    now = datetime.utcnow()
    entry = LOGIN_ATTEMPTS.get(key)
    if not entry or now - entry.get("window_start", now) > timedelta(minutes=LOGIN_WINDOW_MINUTES):
        LOGIN_ATTEMPTS[key] = {
            "count": 1,
            "window_start": now,
            "lock_until": None,
        }
        return

    entry["count"] += 1
    if entry["count"] >= LOGIN_MAX_ATTEMPTS:
        entry["lock_until"] = now + timedelta(minutes=LOGIN_LOCK_MINUTES)


def _clear_login_attempts(key: str) -> None:
    """Xóa thông tin rate limit khi đăng nhập thành công.

    Args:
        key: Khóa rate limit tạo bởi :func:`_login_key`.
    """
    LOGIN_ATTEMPTS.pop(key, None)


def _store_oauth_exchange_token(token: str) -> str:
    """Lưu JWT vào store tạm thời, trả về one-time code để exchange.

    Mã này có hiệu lực 2 phút và chỉ dùng được một lần.

    Args:
        token: JWT cần lưu tạm.

    Returns:
        One-time code để frontend gọi ``/oauth/exchange``.
    """
    code = secrets.token_urlsafe(32)
    with AUTH_LOCK:
        OAUTH_EXCHANGE_STORE[code] = {
            "token": token,
            "expires_at": datetime.utcnow() + timedelta(minutes=2),
        }
    return code


def _consume_oauth_exchange_token(code: str) -> str:
    """Lấy JWT từ store và xóa code (one-time use).

    Args:
        code: One-time code nhận từ ``/oauth/exchange``.

    Returns:
        JWT token đã lưu.

    Raises:
        HTTPException 400: Nếu code không tồn tại hoặc đã hết hạn.
    """
    now = datetime.utcnow()
    with AUTH_LOCK:
        # Opportunistic cleanup to keep memory bounded.
        expired_codes = [k for k, v in OAUTH_EXCHANGE_STORE.items() if v.get("expires_at") and v["expires_at"] <= now]
        for expired in expired_codes:
            OAUTH_EXCHANGE_STORE.pop(expired, None)

        payload = OAUTH_EXCHANGE_STORE.pop(code, None)

    if not payload or payload.get("expires_at") <= now:
        raise HTTPException(status_code=400, detail="Mã xác thực không hợp lệ hoặc đã hết hạn")
    return payload["token"]


@router.post("/register")
def register(username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    # Validate password strength
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 8 ký tự.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 1 chữ hoa.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 1 chữ thường.")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 1 số.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 1 ký tự đặc biệt.")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email đã được sử dụng!")
        
        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại!")
        
        # Hash password and insert user (không có cột oauth_provider cho đăng ký email thường)
        hashed_pw = get_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_pw, datetime.now())
        )
        conn.commit()
        
        # Get newly created user id
        new_user_id = cursor.lastrowid
        
        # Auto-create user_preferences with default settings
        cursor.execute(
            "INSERT INTO user_preferences (user_id, default_layout_settings, default_resolution, default_aspect_ratio, default_panels_per_page, auto_analyze_enabled, auto_save_projects, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (new_user_id, None, '2K', 'auto', 5, 0, 1, datetime.now(), datetime.now())
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"message": "✅ Đăng ký thành công!"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error (register): {str(e)}")


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    login_key = _login_key(username, request)
    with AUTH_LOCK:
        locked, minutes_remaining = _is_login_locked(login_key)
    if locked:
        raise HTTPException(status_code=429, detail=f"Quá nhiều lần đăng nhập sai. Thử lại sau {minutes_remaining} phút")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Try to find user by email or username
        cursor.execute(
            "SELECT * FROM users WHERE email = %s OR username = %s",
            (username, username)
        )
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not user:
            with AUTH_LOCK:
                _record_login_failure(login_key)
            raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")
        
        if not verify_password(password, user["password_hash"]):
            with AUTH_LOCK:
                _record_login_failure(login_key)
            raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")

        with AUTH_LOCK:
            _clear_login_attempts(login_key)
        
        token = create_access_token({
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user.get("role", "user")
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user.get("role", "user")
            }
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error (login): {str(e)}")
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Internal error (login): {str(e)}")


# 🧩 API kiểm tra login
@router.get("/status")
def check_login(user=Depends(get_current_user)):
    return {
        "message": "✅ Token hợp lệ, người dùng đang đăng nhập!",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        },
    }


@router.get("/me")
def get_current_user_info(user=Depends(get_current_user)):
    """Get current logged-in user information from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query fresh data from database
        cursor.execute("SELECT * FROM users WHERE id = %s", (user["id"],))
        db_user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="User không tồn tại!")
        
        return {
            "id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "role": db_user.get("role", "user"),
            "avatar_url": db_user.get("avatar_url"),
            "oauth_provider": db_user.get("oauth_provider"),
            "is_active": db_user.get("is_active", True),
            "created_at": db_user.get("created_at").isoformat() if db_user.get("created_at") else None,
            "last_login": db_user.get("last_login").isoformat() if db_user.get("last_login") else None
        }
    except mysql.connector.Error:
        raise HTTPException(status_code=500, detail="Lỗi hệ thống, vui lòng thử lại sau")


# ========================================
# GOOGLE OAUTH 2.0 LOGIN
# ========================================

@router.get("/google/login")
async def google_login():
    """
    Bước 1: Redirect user đến Google Auth Screen
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth chưa được cấu hình")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    # Tạo URL redirect đến Google
    from urllib.parse import urlencode
    google_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return RedirectResponse(url=google_url)


@router.get("/google/callback")
async def google_callback(code: str):
    """
    Bước 2: Google redirect về với code, đổi code lấy user info
    Bước 3: Tạo user mới hoặc login user có sẵn
    Bước 4: Redirect về frontend với JWT token
    """
    if not code:
        raise HTTPException(status_code=400, detail="Không nhận được code từ Google")
    
    # 1. Đổi code lấy access_token từ Google
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            token_data = token_response.json()
            
            if "error" in token_data:
                raise HTTPException(status_code=400, detail=f"Google OAuth error: {token_data['error']}")
            
            google_access_token = token_data.get("access_token")
            
            # 2. Dùng access_token lấy thông tin user
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"}
            )
            user_info = userinfo_response.json()
            
        except Exception:
            raise HTTPException(status_code=500, detail="Không thể xác thực Google, vui lòng thử lại")
    
    # 3. Lấy email, name, avatar từ Google
    email = user_info.get("email")
    avatar = user_info.get("picture")
    
    if not email:
        raise HTTPException(status_code=400, detail="Không lấy được email từ Google")
    
    # 4. Tạo hoặc cập nhật user trong database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Tìm user theo email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # User đã tồn tại, update avatar và last_login
            cursor.execute(
                "UPDATE users SET avatar_url = %s, last_login = %s WHERE id = %s",
                (avatar, datetime.now(), existing_user["id"])
            )
            conn.commit()
            user = existing_user
        else:
            # Tạo user mới với Google OAuth
            username = email.split("@")[0]  # username từ email
            
            # Tạo password random (Google OAuth không cần password)
            random_password = secrets.token_urlsafe(32)[:72]
            hashed_pw = get_password_hash(random_password)
            
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, avatar_url, created_at) VALUES (%s, %s, %s, %s, %s)",
                (username, email, hashed_pw, avatar, datetime.now())
            )
            conn.commit()
            
            # Get newly created user id
            new_user_id = cursor.lastrowid
            
            # Auto-create user_preferences with default settings
            cursor.execute(
                "INSERT INTO user_preferences (user_id, default_layout_settings, default_resolution, default_aspect_ratio, default_panels_per_page, auto_analyze_enabled, auto_save_projects, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (new_user_id, None, '2K', 'auto', 5, 0, 1, datetime.now(), datetime.now())
            )
            conn.commit()
            
            # Get newly created user
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error (google_callback): {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error (google_callback): {str(e)}")
    
    # 5. Tạo JWT token của hệ thống
    token = create_access_token({
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "user")
    })

    # 6. REDIRECT về frontend với one-time code (không đưa JWT vào URL)
    exchange_code = _store_oauth_exchange_token(token)
    return RedirectResponse(url=f"{FRONTEND_URL}/?code={exchange_code}")


# ========== Pydantic Models ==========

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    username: str
    avatar_url: str = ""


class CreateApiKeyRequest(BaseModel):
    name: str = "API Key"


class OAuthExchangeRequest(BaseModel):
    code: str


@router.get("/debug/config", include_in_schema=False)
def debug_config(_admin: dict = Depends(get_admin_user)):
    """[Admin only] Trả về cấu hình Google OAuth để debug."""
    return {
        "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
        "FRONTEND_URL": FRONTEND_URL,
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID[:5] + "..." if GOOGLE_CLIENT_ID else None,
    }


@router.get("/system/db-status", include_in_schema=False)
def debug_db(_admin: dict = Depends(get_admin_user)):
    """[Admin only] Kiếm tra kết nối và danh sách bảng của DB."""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.execute("SELECT session_id, user_id, status, created_at FROM upload_sessions LIMIT 5")
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"success": True, "tables": tables, "sessions": sessions}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/oauth/exchange")
def oauth_exchange(request: OAuthExchangeRequest):
    """Exchange one-time code nhận từ Google OAuth callback lấy JWT."""
    token = _consume_oauth_exchange_token(request.code)
    return {"access_token": token, "token_type": "bearer"}


# ========== New Settings Endpoints ==========

@router.post("/password/change")
def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """Đổi mật khẩu cho user (chỉ áp dụng cho users đăng ký bằng email/password)"""
    user_db = UserDB()
    
    # Get current user from database
    users = user_db.get_all()
    user = next((u for u in users if u["id"] == current_user["id"]), None)
    
    if not user:
        user_db.close()
        raise HTTPException(status_code=404, detail="User không tồn tại")
    
    # Verify old password
    if not verify_password(request.old_password, user["password_hash"]):
        user_db.close()
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không đúng")
    
    # Update password
    new_hash = get_password_hash(request.new_password)
    
    try:
        cursor = user_db.conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_hash, current_user["id"])
        )
        user_db.conn.commit()
        cursor.close()
        user_db.close()
        
        return {"success": True, "message": "Đổi mật khẩu thành công"}
    except Exception as e:
        user_db.close()
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật database: {str(e)}")


@router.put("/me")
def update_profile(request: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    """Cập nhật thông tin profile (username, avatar)"""
    user_db = UserDB()
    
    try:
        cursor = user_db.conn.cursor()
        cursor.execute(
            "UPDATE users SET username = %s, avatar_url = %s WHERE id = %s",
            (request.username, request.avatar_url, current_user["id"])
        )
        user_db.conn.commit()
        cursor.close()
        user_db.close()
        
        return {"success": True, "message": "Cập nhật thành công"}
    except Exception as e:
        user_db.close()
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật profile: {str(e)}")


@router.get("/api-keys")
def get_api_keys(current_user: dict = Depends(get_current_user)):
    """Lấy danh sách API keys của user"""
    user_db = UserDB()
    
    try:
        cursor = user_db.conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, api_key, key_name as name, is_active, 
               rate_limit, expires_at, last_used_at, created_at 
               FROM api_keys WHERE user_id = %s AND is_active = TRUE
               ORDER BY created_at DESC""",
            (current_user["id"],)
        )
        keys = cursor.fetchall()
        for key in keys:
            raw_key = key.pop("api_key", "")
            if raw_key and len(raw_key) > 8:
                key["key"] = f"{raw_key[:6]}...{raw_key[-4:]}"
            else:
                key["key"] = "****"
        cursor.close()
        user_db.close()
        
        return {"success": True, "keys": keys}
    except Exception:
        user_db.close()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống, vui lòng thử lại sau")


@router.post("/api-keys")
def create_api_key(request: CreateApiKeyRequest, current_user: dict = Depends(get_current_user)):
    """Tạo API key mới"""
    user_db = UserDB()
    
    # Generate random API key
    new_key = f"cca_{secrets.token_urlsafe(32)}"
    
    try:
        cursor = user_db.conn.cursor()
        cursor.execute(
            """INSERT INTO api_keys (user_id, api_key, key_name, is_active, rate_limit) 
               VALUES (%s, %s, %s, TRUE, 100)""",
            (current_user["id"], new_key, request.name)
        )
        user_db.conn.commit()
        key_id = cursor.lastrowid
        cursor.close()
        user_db.close()
        
        return {
            "success": True, 
            "key": {
                "id": key_id,
                "key": new_key,
                "name": request.name,
                "created_at": datetime.utcnow().isoformat()
            }
        }
    except Exception:
        user_db.close()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống, vui lòng thử lại sau")


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """Xóa API key"""
    user_db = UserDB()
    
    try:
        cursor = user_db.conn.cursor()
        
        # Verify ownership
        cursor.execute(
            "SELECT user_id FROM api_keys WHERE id = %s",
            (key_id,)
        )
        result = cursor.fetchone()
        
        if not result or result[0] != current_user["id"]:
            cursor.close()
            user_db.close()
            raise HTTPException(status_code=403, detail="Không có quyền xóa key này")
        
        # Delete key
        cursor.execute("DELETE FROM api_keys WHERE id = %s", (key_id,))
        user_db.conn.commit()
        cursor.close()
        user_db.close()
        
        return {"success": True, "message": "Xóa API key thành công"}
    except HTTPException:
        raise
    except Exception:
        user_db.close()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống, vui lòng thử lại sau")


@router.delete("/me")
def delete_account(current_user: dict = Depends(get_current_user)):
    """Xóa tài khoản vĩnh viễn (cascade delete tất cả dữ liệu liên quan)"""
    user_db = UserDB()
    
    try:
        cursor = user_db.conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (current_user["id"],))
        user_db.conn.commit()
        cursor.close()
        user_db.close()
        
        return {"success": True, "message": "Xóa tài khoản thành công"}
    except Exception:
        user_db.close()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống, vui lòng thử lại sau")
