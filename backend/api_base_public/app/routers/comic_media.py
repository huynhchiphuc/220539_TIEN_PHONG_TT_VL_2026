import io
import os
import time
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image

from app.config import settings
from app.db.query_helpers import execute, fetch_all
from app.security.security import get_current_user, get_current_user_optional
from app.services.comic.session_access import ensure_session_owner
from app.services.comic.file_ops import (
    ALLOWED_EXTENSIONS,
    OUTPUT_FOLDER,
    create_media_access_token,
    resolve_safe_file,
    validate_session,
    verify_media_access_token,
)
from app.services.storage.cloudinary_manager import CLOUDINARY_ENABLED, upload_image

router = APIRouter(prefix="/comic", tags=["comic"])


def _log_download_activity(user_id: int, session_id: str, action: str, details: str):
    try:
        execute(
            "INSERT INTO activity_logs (user_id, session_id, action, resource_type, details, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            (user_id, session_id, action, "comic_output", details),
        )
    except Exception as exc:
        print(f"⚠️ Activity logging failed: {exc}")


def _upload_pages_to_cloudinary(session_id: str):
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    page_files = sorted(
        list(Path(output_folder).glob("page_*.png")) + list(Path(output_folder).glob("page_*.jpg")),
        key=lambda path: path.name,
    )

    if not page_files:
        raise HTTPException(status_code=404, detail="Không có trang nào để lưu cloud")

    cloud_urls = []
    cloud_folder = f"comic_ai/{session_id}"
    for idx, page_path in enumerate(page_files, start=1):
        upload_result = upload_image(
            file_path=str(page_path),
            folder=cloud_folder,
            public_id=f"page_{idx:03d}",
        )
        url = upload_result.get("url")
        if url:
            cloud_urls.append(url)

    return cloud_urls


@router.post("/sessions/{session_id}/save-cloud")
async def save_to_cloud(session_id: str, user: dict = Depends(get_current_user)):
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    if not CLOUDINARY_ENABLED:
        raise HTTPException(status_code=503, detail="Cloudinary chưa được cấu hình")

    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả để lưu")

    try:
        cloud_urls = _upload_pages_to_cloudinary(session_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lưu cloud thất bại: {exc}")

    _log_download_activity(
        user.get("id"),
        session_id,
        "save_cloud",
        f"Saved {len(cloud_urls)} pages to Cloudinary",
    )

    return {
        "success": True,
        "session_id": session_id,
        "saved_count": len(cloud_urls),
        "pages": cloud_urls,
    }


@router.get("/preview/{session_id}")
@router.get("/sessions/{session_id}/preview")
async def preview(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    try:
        rows = fetch_all(
            """
            SELECT cp.output_image_path as image_url
            FROM comic_pages cp
            JOIN comic_projects up ON cp.project_id = up.id
            WHERE up.session_id = %s
            ORDER BY cp.page_number ASC
            """,
            (session_id,),
            dictionary=True,
        )

        if rows:
            timestamp = int(time.time() * 1000)
            page_urls = []
            for row in rows:
                if row.get("image_url"):
                    url = row["image_url"]
                    separator = "&" if "?" in url else "?"
                    page_urls.append(f"{url}{separator}t={timestamp}")

            if page_urls:
                return {"success": True, "pages": page_urls, "timestamp": timestamp}
    except Exception as exc:
        print(f"Error fetching cloudinary urls for preview: {exc}")

    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if os.path.exists(output_folder):
        pages_png = sorted(Path(output_folder).glob("page_*.png"))
        pages_jpg = sorted(Path(output_folder).glob("page_*.jpg"))
        pages = list(pages_png) + list(pages_jpg)

        if pages:
            base_url = str(request.base_url).rstrip("/")
            timestamp = int(time.time() * 1000)
            media_token = create_media_access_token(session_id, user.get("id"), settings.SECRET_KEY)
            page_urls = [
                f"{base_url}/api/v1/comic/sessions/{session_id}/outputs/{page.name}?st={media_token}&t={timestamp}"
                for page in pages
            ]
            return {"success": True, "pages": page_urls, "timestamp": timestamp}

    raise HTTPException(status_code=404, detail="Không tìm thấy kết quả ảnh trên server hoặc cloud.")


@router.get("/sessions/{session_id}/outputs/{filename}")
async def serve_output(session_id: str, filename: str, st: str = Query(...)):
    validate_session(session_id)
    verify_media_access_token(session_id, st, settings.SECRET_KEY)

    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    file_path = resolve_safe_file(output_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại")

    return FileResponse(
        path=file_path,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/sessions/{session_id}/covers/{filename}")
async def serve_cover(session_id: str, filename: str, st: str = Query(...)):
    validate_session(session_id)
    verify_media_access_token(session_id, st, settings.SECRET_KEY)

    covers_folder = os.path.join(OUTPUT_FOLDER, session_id, "covers")
    file_path = resolve_safe_file(covers_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File bìa không tồn tại")

    return FileResponse(path=file_path)


@router.get("/download/{session_id}")
@router.get("/sessions/{session_id}/download")
async def download_zip(session_id: str, token: str = None, user: dict = Depends(get_current_user_optional)):
    _ = token
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả")

    pages_count = len(list(Path(output_folder).glob("page_*.*")))
    _log_download_activity(user.get("id"), session_id, "download_zip", f"Downloaded ZIP with {pages_count} pages")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for page in Path(output_folder).glob("page_*.png"):
            zip_file.write(page, page.name)
        for page in Path(output_folder).glob("page_*.jpg"):
            zip_file.write(page, page.name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=comic_{session_id}.zip"},
    )


@router.get("/download_pdf/{session_id}")
@router.get("/sessions/{session_id}/download-pdf")
async def download_pdf(session_id: str, token: str = None, user: dict = Depends(get_current_user_optional)):
    _ = token
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    _log_download_activity(user.get("id"), session_id, "download_pdf", "Downloaded PDF with covers")

    page_files = sorted(
        list(Path(output_folder).glob("page_*.png"))
        + list(Path(output_folder).glob("page_*.jpg")),
        key=lambda path: path.name,
    )

    if not page_files:
        raise HTTPException(status_code=400, detail="Chưa tạo trang nội dung. Hãy bấm 'Tạo truyện' trước.")

    covers_folder = os.path.join(output_folder, "covers")
    cover_order = ["front", "back", "thank_you"]
    cover_paths = {}
    if os.path.exists(covers_folder):
        for cover_type in cover_order:
            for ext in ALLOWED_EXTENSIONS:
                candidate = os.path.join(covers_folder, f"{cover_type}.{ext}")
                if os.path.exists(candidate):
                    cover_paths[cover_type] = candidate
                    break

    with Image.open(page_files[0]) as ref_image:
        page_width, page_height = ref_image.size

    def fit_to_page(image_path, target_width, target_height, bg_color=(255, 255, 255)):
        image = Image.open(image_path).convert("RGB")
        original_width, original_height = image.size
        scale = min(target_width / original_width, target_height / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_width, target_height), bg_color)
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        canvas.paste(resized, (paste_x, paste_y))
        return canvas

    images_for_pdf = []
    if "front" in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths["front"], page_width, page_height))

    for page in page_files:
        images_for_pdf.append(Image.open(page).convert("RGB"))

    if "back" in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths["back"], page_width, page_height))

    if "thank_you" in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths["thank_you"], page_width, page_height))

    if not images_for_pdf:
        raise HTTPException(status_code=400, detail="Không có trang nào để xuất PDF")

    buffer = io.BytesIO()
    first_image = images_for_pdf[0]
    rest_images = images_for_pdf[1:]
    first_image.save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=rest_images,
        resolution=150,
    )
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comic_{session_id}.pdf"},
    )
