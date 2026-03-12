from fastapi import APIRouter, Depends
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Request, Form  # noqa: E402, F401
from fastapi.responses import FileResponse  # noqa: E402
from uuid import uuid4
from app.models.file_upload import FileUpload
from app.security.security import verify_api_key
from app.config import settings
from mimetypes import guess_type
from pathlib import Path
import os
import shutil


# Tạo router cho người dùng
router = APIRouter(prefix="/upload-file", tags=["file-upload"])


@router.post("/upload/", response_model=FileUpload)
async def upload_file(
    token: str = Form(""),
    path_image: str = Form(""),
    text: str = Form(""),
    file: UploadFile = File(...),  # Tệp được upload
    api_key: str = Depends(verify_api_key),  # Khóa API để xác thực
):
    try:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        folder_path = os.path.join(os.path.join(settings.DIR_ROOT, "utils", "download"))
        os.makedirs(folder_path) if not os.path.exists(folder_path) else folder_path
        file_path = os.path.join(folder_path, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        download_url = f"{router.prefix}/download/{unique_filename}"
        
        return FileUpload(filename=unique_filename, download_url=download_url)
    except Exception:
        raise HTTPException(status_code=404, detail="upload errors")


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    API để tải xuống tệp.

    Tham số:
    - `filename`: Tên tệp cần tải xuống.

    Trả về:
    - Nếu tệp tồn tại, trả về tệp dưới dạng phản hồi tải xuống.
    - Nếu tệp không tồn tại, trả về lỗi 404 với thông báo "File not found".
    """
    if not filename or '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    base_folder = Path(settings.DIR_ROOT, "utils", "download").resolve()
    file_path = (base_folder / filename).resolve()
    if base_folder not in file_path.parents:
        raise HTTPException(status_code=400, detail="Đường dẫn file không hợp lệ")

    if os.path.exists(file_path):
        return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/view/{filename}")
async def view_file(filename: str):
    """
    API để xem trước file (hình ảnh, video, audio, v.v.)

    Tham số:
    - `filename`: Tên file cần xem.

    Trả về:
    - File với media type phù hợp nếu tồn tại.
    - 404 nếu không tìm thấy file.
    """
    if not filename or '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    base_folder = Path(settings.DIR_ROOT, "utils", "download").resolve()
    file_path = (base_folder / filename).resolve()
    if base_folder not in file_path.parents:
        raise HTTPException(status_code=400, detail="Đường dẫn file không hợp lệ")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    media_type, _ = guess_type(str(file_path))
    media_type = media_type or "application/octet-stream"  # fallback nếu không đoán được

    return FileResponse(
        path=str(file_path), media_type=media_type, filename=filename, headers={"Content-Disposition": f"inline; filename={filename}"}
    )
