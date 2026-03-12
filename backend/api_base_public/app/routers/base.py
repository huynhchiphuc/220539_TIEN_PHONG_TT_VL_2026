from fastapi import APIRouter
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request, Form  # noqa: E402, F401

from app.security.security import verify_api_key, get_current_user


# Tạo router cho người dùng
router = APIRouter(prefix="/base", tags=["base"])


@router.post("/base-url/")
def base_url(
    base_data: str = Form(...),
    user_data=Depends(get_current_user),  # 👈 xác thực bằng JWT
):
    return {"from": user_data.get("sub"), "role": user_data.get("role"), "data": base_data}


@router.post("/base-api/")
def base_api_key(
    base_data: str = Form(...),
    api_key: str = Depends(verify_api_key),  # 👈 xác thực bằng API key
):
    return {"from": "api_key", "data": base_data}