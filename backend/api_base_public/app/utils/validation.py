"""
Validation và Error Handling utilities cho Comic Book Generator.

Module này cung cấp các hàm validation dùng chung cho FastAPI,
bao gồm validate file upload, session ID, và tham số generate.
"""

import os

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Custom validation error kèm HTTP status code.

    Attributes:
        message: Thông báo lỗi hiển thị cho client.
        status_code: HTTP status code tương ứng (mặc định 400).
    """

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_http_exception(self) -> HTTPException:
        """Chuyển thành FastAPI HTTPException để raise trong endpoint."""
        return HTTPException(status_code=self.status_code, detail=self.message)


# ---------------------------------------------------------------------------
# Session validation
# ---------------------------------------------------------------------------

def validate_session_id(session_id: str, base_folder: str) -> str:
    """Validate session ID an toàn, chống path traversal.

    Args:
        session_id: Chuỗi định danh session cần kiểm tra.
        base_folder: Thư mục gốc chứa các session.

    Returns:
        session_id đã được xác nhận hợp lệ.

    Raises:
        ValidationError: Nếu session ID không hợp lệ hoặc nguy hiểm.
    """
    if not session_id:
        raise ValidationError("Session ID không được để trống")

    if not isinstance(session_id, str):
        raise ValidationError("Session ID phải là chuỗi")

    # Security: Prevent path traversal
    session_path = os.path.abspath(os.path.join(base_folder, session_id))
    base_path = os.path.abspath(base_folder)

    if not session_path.startswith(base_path):
        raise ValidationError("Session ID không hợp lệ", 403)

    return session_id


# ---------------------------------------------------------------------------
# Generate parameters validation
# ---------------------------------------------------------------------------

def validate_generate_params(data: dict) -> dict:
    """Validate và sanitize tham số cho endpoint generate.

    Args:
        data: Dict dữ liệu từ request body.

    Returns:
        Dict tham số đã được validate và chuyển đổi kiểu dữ liệu.

    Raises:
        ValidationError: Nếu bất kỳ tham số nào không hợp lệ.
    """
    if not data:
        raise ValidationError("Request body trống")

    session_id = data.get("session_id")
    if not session_id:
        raise ValidationError("Thiếu session_id")

    try:
        params = {
            "session_id": str(session_id),
            "panels_per_page": int(data.get("panels_per_page", 5)),
            "diagonal_prob": float(data.get("diagonal_prob", 0.3)),
            "target_dpi": int(data.get("target_dpi", 150)),
            "adaptive_layout": bool(data.get("adaptive_layout", True)),
            "use_smart_crop": bool(data.get("use_smart_crop", False)),
            "analyze_shot_type": bool(data.get("analyze_shot_type", False)),
            "classify_characters": bool(data.get("classify_characters", False)),
            "enable_perspective_warp": bool(data.get("enable_perspective_warp", False)),
            "auto_page_size": bool(data.get("auto_page_size", True)),
            "aspect_ratio": str(data.get("aspect_ratio", "9:16")),
            "reading_direction": str(data.get("reading_direction", "ltr")),
        }
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Lỗi chuyển đổi tham số: {str(exc)}")

    # Range validation
    if not (2 <= params["panels_per_page"] <= 10):
        raise ValidationError("panels_per_page phải từ 2–10")

    if not (0.0 <= params["diagonal_prob"] <= 1.0):
        raise ValidationError("diagonal_prob phải từ 0.0–1.0")

    if params["target_dpi"] not in {75, 150, 300, 600}:
        raise ValidationError("target_dpi phải là 75, 150, 300 hoặc 600")

    if params["reading_direction"] not in {"ltr", "rtl"}:
        raise ValidationError("reading_direction phải là 'ltr' hoặc 'rtl'")

    allowed_aspect_ratios = {"auto", "1:1", "2:3", "3:4", "4:5", "9:16"}
    if params["aspect_ratio"] not in allowed_aspect_ratios:
        raise ValidationError("aspect_ratio không hợp lệ")

    return params


# ---------------------------------------------------------------------------
# File validation
# ---------------------------------------------------------------------------

def validate_file(file, max_size_mb: int = 50) -> tuple[bool, str | None]:
    """Validate file ảnh upload từ multipart form.

    Kiểm tra: extension, kích thước, và tính hợp lệ của ảnh bằng PIL.

    Args:
        file: Object file có thuộc tính ``filename``, ``seek``, ``tell``, ``read``.
        max_size_mb: Kích thước file tối đa cho phép (MB).

    Returns:
        Tuple ``(is_valid, error_message)``.
        Nếu hợp lệ, ``error_message`` là ``None``.
    """
    from PIL import Image  # lazy import để tránh circular dependency

    if not file or not file.filename:
        return False, "File không hợp lệ"

    allowed_extensions = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if ext not in allowed_extensions:
        return False, (
            f"Định dạng không hỗ trợ: .{ext}. "
            f"Chấp nhận: {', '.join(sorted(allowed_extensions))}"
        )

    # Kích thước file
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File quá lớn ({file_size / 1024 / 1024:.1f} MB). Tối đa {max_size_mb} MB"

    if file_size == 0:
        return False, "File rỗng"

    # Xác thực ảnh bằng PIL
    try:
        file.seek(0)
        img = Image.open(file)
        img.verify()
        file.seek(0)

        if img.width < 10 or img.height < 10:
            return False, "Ảnh quá nhỏ (tối thiểu 10×10 px)"

        if img.width > 10000 or img.height > 10000:
            return False, "Ảnh quá lớn (tối đa 10000×10000 px)"

    except Exception as exc:
        return False, f"File không phải ảnh hợp lệ: {str(exc)}"

    return True, None
