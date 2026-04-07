"""Utilities for comic file validation, safe path handling, and media tokens."""

import os
import time
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from jose import JWTError, jwt
from PIL import Image

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
COVER_TYPES = {"front", "back", "thank_you"}

MIN_FILE_SIZE = 1024
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TOTAL_SIZE = 500 * 1024 * 1024
MIN_RESOLUTION = 50
MAX_RESOLUTION = 12000
MEDIA_TOKEN_EXPIRE_MINUTES = 30

MAGIC_BYTES = {
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "gif": [b"GIF87a", b"GIF89a"],
    "bmp": [b"BM"],
    "webp": None,
}


def ensure_storage_dirs() -> None:
    """Tạo các thư mục lưu trữ nếu chưa tồn tại."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Kiểm tra phần mở rộng file có được phép upload không.

    Args:
        filename: Tên file cần kiểm tra.

    Returns:
        ``True`` nếu phần mở rộng nằm trong ``ALLOWED_EXTENSIONS``.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_magic_bytes(content: bytes, ext: str) -> bool:
    """Xác nhận nội dung file khớp với magic bytes của định dạng ảnh.

    Chống attack giả mạo: upload file .exe gần đổi thành .jpg.

    Args:
        content: Nội dung thô của file (ít nhất 12 bytes).
        ext: Extension đã lowercase (ví dụ: ``"jpg"``).

    Returns:
        ``True`` nếu magic bytes khớp hoặc không có signature để kiểm tra.
    """
    if len(content) < 12:
        return False
    ext = ext.lower()
    if ext == "webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"

    signatures = MAGIC_BYTES.get(ext)
    if signatures is None:
        return True
    return any(content[: len(sig)] == sig for sig in signatures)


def validate_image_content(content: bytes, filename: str) -> tuple[bool, str, int, int]:
    """Xác thực kích thước và tính toàn vẹn của file ảnh.

    Args:
        content: Nội dung file ảnh.
        filename: Tên file (để log lỗi).

    Returns:
        Tuple (hợp lệ, thông báo lỗi, chiều rộng, chiều cao).
    """
    try:
        with Image.open(BytesIO(content)) as img:
            img.load()
            width, height = img.size

        if width < MIN_RESOLUTION or height < MIN_RESOLUTION:
            return (
                False,
                f"Ảnh quá nhỏ ({width}×{height} px). Tối thiểu {MIN_RESOLUTION}×{MIN_RESOLUTION} px",
                width,
                height,
            )

        if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
            return (
                False,
                f"Ảnh quá lớn ({width}×{height} px). Tối đa {MAX_RESOLUTION} px mỗi chiều",
                width,
                height,
            )

        return True, "", width, height
    except Exception as exc:
        return False, f"File ảnh bị hỏng hoặc không đọc được: {str(exc)[:80]}", 0, 0


def detect_image_orientation(input_folder: str) -> tuple[str, str]:
    try:
        valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif")
        image_files = [
            os.path.join(input_folder, name)
            for name in os.listdir(input_folder)
            if name.lower().endswith(valid_exts)
        ]
        if not image_files:
            return "landscape", "16:9"

        portrait_aspects: list[float] = []
        landscape_aspects: list[float] = []
        sample_files = image_files[: min(20, len(image_files))]

        for img_path in sample_files:
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    aspect = width / height
                    if aspect < 0.95:
                        portrait_aspects.append(aspect)
                    else:
                        landscape_aspects.append(aspect)
            except Exception:
                continue

        all_aspects = portrait_aspects + landscape_aspects
        if not all_aspects:
            return "landscape", "16:9"

        overall_avg_aspect = sum(all_aspects) / len(all_aspects)
        if overall_avg_aspect < 0.95:
            if overall_avg_aspect <= 0.56:
                return "portrait", "9:16"
            if overall_avg_aspect <= 0.67:
                return "portrait", "2:3"
            if overall_avg_aspect <= 0.8:
                return "portrait", "3:4"
            return "portrait", "4:5"

        if overall_avg_aspect > 1.05:
            if overall_avg_aspect >= 2.33:
                return "landscape", "21:9"
            if overall_avg_aspect >= 1.6:
                return "landscape", "16:9"
            if overall_avg_aspect >= 1.4:
                return "landscape", "3:2"
            if overall_avg_aspect >= 1.2:
                return "landscape", "4:3"
            return "landscape", "5:4"

        return "square", "1:1"
    except Exception:
        return "landscape", "16:9"


def validate_session(session_id: str, upload_root: str = UPLOAD_FOLDER) -> str:
    if not session_id or "/" in session_id or "\\" in session_id or ".." in session_id:
        raise HTTPException(status_code=400, detail="session_id khong hop le")

    input_folder = os.path.join(upload_root, session_id)
    if not os.path.abspath(input_folder).startswith(os.path.abspath(upload_root)):
        raise HTTPException(status_code=400, detail="session_id khong hop le (path traversal)")
    return input_folder


def create_media_access_token(
    session_id: str,
    user_id: int,
    secret_key: str,
    expire_minutes: int = MEDIA_TOKEN_EXPIRE_MINUTES,
) -> str:
    payload = {
        "sid": session_id,
        "uid": user_id,
        "type": "media_access",
        "exp": int(time.time()) + expire_minutes * 60,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_media_access_token(session_id: str, token: str, secret_key: str) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="Thieu token truy cap media")

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token media khong hop le hoac het han") from exc

    if payload.get("type") != "media_access" or payload.get("sid") != session_id:
        raise HTTPException(status_code=403, detail="Token media khong hop le")


def resolve_safe_file(base_folder: str, filename: str) -> str:
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Ten file khong hop le")

    base_path = Path(base_folder).resolve()
    target_path = (base_path / filename).resolve()
    if base_path not in target_path.parents:
        raise HTTPException(status_code=400, detail="Duong dan file khong hop le")
    return str(target_path)
