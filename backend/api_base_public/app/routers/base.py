"""
Router cơ bản kiểm tra sức khoẻ API và test xác thực.

Cung cấp các endpoint mẫu để kiểm tra JWT và API Key authentication.
"""

from fastapi import APIRouter, Depends, Form

from app.security.security import verify_api_key, get_current_user

router = APIRouter(prefix="/base", tags=["base"])


@router.post("/base-url/")
def base_url(
    base_data: str = Form(...),
    user_data: dict = Depends(get_current_user),
) -> dict:
    """Endpoint mẫu xác thực bằng JWT Bearer token.

    Args:
        base_data: Dữ liệu form bất kỳ để kiểm tra.
        user_data: Payload JWT của user đang đăng nhập.

    Returns:
        Dict chứa thông tin user và dữ liệu nhận được.
    """
    return {
        "from": user_data.get("username"),
        "role": user_data.get("role"),
        "data": base_data,
    }


@router.post("/base-api/")
def base_api_key(
    base_data: str = Form(...),
    api_key: str = Depends(verify_api_key),
) -> dict:
    """Endpoint mẫu xác thực bằng API Key trong header Authorization.

    Args:
        base_data: Dữ liệu form bất kỳ để kiểm tra.
        api_key: API Key đã được xác thực từ header.

    Returns:
        Dict xác nhận nguồn gốc xác thực và dữ liệu nhận được.
    """
    return {"from": "api_key", "data": base_data}