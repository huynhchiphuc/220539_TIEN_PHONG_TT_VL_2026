"""
Router ComicCraft AI - Chuyển đổi từ THUC_TAP2/app.py (Flask)
sang chuẩn FastAPI của dự án 220359_TIEN_PHONG_TT_VL_2026
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks, Request, Form
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import List
from dataclasses import dataclass
import importlib.util
import os
import shutil
import json
import io
import math
import random
from PIL import Image
from datetime import datetime
from uuid import uuid4

from app.models.comic import GenerateRequest, AutoFrameRequest
from app.config import settings
from app.security.security import get_current_user
from app.db.mysql_connection import get_mysql_connection
from app.services.comic.session_access import ensure_session_owner
from app.services.comic.file_ops import (
    UPLOAD_FOLDER,
    OUTPUT_FOLDER,
    ALLOWED_EXTENSIONS,
    COVER_TYPES,
    MIN_FILE_SIZE,
    MAX_FILE_SIZE,
    MAX_TOTAL_SIZE,
    allowed_file,
    validate_magic_bytes,
    validate_image_content,
    detect_image_orientation,
    validate_session,
    create_media_access_token,
    ensure_storage_dirs,
)

try:
    from app.services.storage.cloudinary_manager import upload_image, CLOUDINARY_ENABLED
except ImportError:
    CLOUDINARY_ENABLED = False

# ── Lazy init helpers (tránh startup nặng làm Render timeout scan port) ──

DB_AVAILABLE = True
COMIC_ENGINE_AVAILABLE = None
AI_ANALYSIS_AVAILABLE = None
FACE_RECOGNITION_AVAILABLE = False
CLIP_AVAILABLE = False

session_mgr = None
activity_logger = None
ai_analysis_mgr = None
ImageAnalyzer = None


def _check_comic_engine_available() -> bool:
    global COMIC_ENGINE_AVAILABLE
    if COMIC_ENGINE_AVAILABLE is None:
        COMIC_ENGINE_AVAILABLE = (
            importlib.util.find_spec("app.services.comic.comic_book_auto_fill") is not None
            and importlib.util.find_spec("app.services.comic.comic_layout_simple") is not None
        )
    return COMIC_ENGINE_AVAILABLE


def _ensure_db_managers() -> bool:
    global DB_AVAILABLE, session_mgr, activity_logger, ai_analysis_mgr
    if session_mgr is not None and activity_logger is not None and ai_analysis_mgr is not None:
        DB_AVAILABLE = True
        return True

    try:
        from app.db.db_manager import (
            MySQLDatabase,
            SessionManager,
            ActivityLogger,
            AIAnalysisManager,
        )

        db = MySQLDatabase(
            host=settings.HOST,
            port=settings.DB_PORT,
            database=settings.DATABASE,
            user=settings.USER,
            password=settings.PASSWORD,
            ssl_mode=settings.DB_SSL_MODE,
            ssl_ca=settings.DB_SSL_CA,
        )
        session_mgr = SessionManager(db)
        activity_logger = ActivityLogger(db)
        ai_analysis_mgr = AIAnalysisManager(db)
        DB_AVAILABLE = True
        print("✅ Legacy DB managers initialized")
        return True
    except Exception as e:
        DB_AVAILABLE = False
        print(f"⚠️  Legacy DB managers unavailable: {e}")
        return False


def _ensure_ai_modules() -> bool:
    global AI_ANALYSIS_AVAILABLE, FACE_RECOGNITION_AVAILABLE, CLIP_AVAILABLE, ImageAnalyzer
    if ImageAnalyzer is not None:
        AI_ANALYSIS_AVAILABLE = True
        return True

    try:
        from app.services.ai.character_classifier import FACE_RECOGNITION_AVAILABLE as _face_available
        from app.services.ai.scene_classifier import AI_MODEL_AVAILABLE as _clip_available
        from app.services.ai.image_analyzer import ImageAnalyzer as _ImageAnalyzer

        FACE_RECOGNITION_AVAILABLE = _face_available
        CLIP_AVAILABLE = _clip_available
        ImageAnalyzer = _ImageAnalyzer
        AI_ANALYSIS_AVAILABLE = True
        print("✅ AI analysis modules initialized")
        return True
    except Exception as e:
        AI_ANALYSIS_AVAILABLE = False
        FACE_RECOGNITION_AVAILABLE = False
        CLIP_AVAILABLE = False
        print(f"⚠️  AI analysis modules unavailable: {e}")
        return False

try:
    from app.utils.validation import validate_file, validate_session_id, ValidationError
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️  Validation module không có.")


# ── Cấu hình ──────────────────────────────────────────────────────────────────
ensure_storage_dirs()


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/comic", tags=["comic"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def upload_session_to_cloudinary_bg(session_id: str):
    """Background task: Upload generated comic pages to Cloudinary & update database."""
    if not CLOUDINARY_ENABLED:
        print("⚠️ Cloudinary disabled: missing CLOUDINARY_URL or key settings")
        return
        
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_folder):
        return
        
    try:
        pages = (list(Path(output_folder).glob('page_*.png')) +
                 list(Path(output_folder).glob('page_*.jpg')))

        if not pages:
            print(f"⚠️ No pages found for cloud sync session={session_id}")
            return

        project_id = None
        conn = None
        cursor = None
        try:
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM comic_projects WHERE session_id = %s", (session_id,))
            proj = cursor.fetchone()
            if proj:
                project_id = proj['id']
                # Xóa các bản ghi cũ trong DB để tránh trùng lặp khi generate lại
                cursor.execute("DELETE FROM comic_pages WHERE project_id = %s", (project_id,))
                conn.commit()
            else:
                print(f"⚠️ No comic_projects row for session={session_id}, will upload cloud only")
        except Exception as db_open_err:
            print(f"⚠️ DB unavailable for cloud sync session={session_id}: {db_open_err}")
            project_id = None

        for page_idx, page_path in enumerate(sorted(pages), 1):
            file_path_str = str(page_path)
            try:
                # Upload
                res = upload_image(
                    file_path=file_path_str, 
                    folder=f"comic_ai/{session_id}",
                    public_id=f"page_{page_idx}"
                )
                cloud_url = res.get("url")
                if cloud_url and cursor and project_id:
                    # Save to DB
                    # (Simplified insertion as a 'content' page type)
                    cursor.execute(
                        """INSERT INTO comic_pages 
                           (project_id, page_number, page_type, output_image_path)
                           VALUES (%s, %s, %s, %s)
                        """,
                        (project_id, page_idx, 'content', cloud_url)
                    )
                    conn.commit()
            except Exception as e:
                print(f"Cloudinary upload failed for {file_path_str}: {e}")

        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"☁️ Successfully backed up session {session_id} to Cloudinary.")
    except Exception as e:
        print(f"⚠️ Cloudinary background task error: {e}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
@router.post("/sessions/upload")
async def upload_files(files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)):
    """Upload nhiều ảnh với validation đầy đủ. Trả về session_id để dùng cho /generate."""
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Không có file nào được upload")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail=f"Quá nhiều file ({len(files)}). Tối đa 100 ảnh")

    session_id = uuid4().hex
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    uploaded_files = []
    errors = []
    total_size = 0

    for idx, file in enumerate(files, 1):
        if not file or not file.filename:
            continue

        fname = file.filename

        # 1. Kiểm tra extension
        if not allowed_file(fname):
            errors.append(f"{fname}: Định dạng không hỗ trợ")
            continue

        ext = fname.rsplit('.', 1)[1].lower()

        # Đọc nội dung file vào bộ nhớ
        content = await file.read()
        file_size = len(content)

        # 2. Kiểm tra kích thước tối thiểu (< 1KB = rỗng hoặc hỏng)
        if file_size < MIN_FILE_SIZE:
            errors.append(f"{fname}: File quá nhỏ ({file_size} bytes) — có thể bị hỏng")
            continue

        # 3. Kiểm tra kích thước tối đa per-file
        if file_size > MAX_FILE_SIZE:
            errors.append(f"{fname}: File quá lớn ({file_size / 1024 / 1024:.1f} MB, tối đa 50 MB)")
            continue

        # 4. Kiểm tra tổng dung lượng
        total_size += file_size
        if total_size > MAX_TOTAL_SIZE:
            errors.append("Tổng dung lượng vượt quá 500 MB")
            break

        # 5. Kiểm tra magic bytes — xác thực nội dung thực sự là ảnh
        if not validate_magic_bytes(content, ext):
            errors.append(f"{fname}: Nội dung file không khớp với định dạng .{ext} (có thể là file giả mạo)")
            continue

        # 6. Kiểm tra tính toàn vẹn ảnh bằng PIL (hỏng, resolution)
        is_valid, err_msg, img_w, img_h = validate_image_content(content, fname)
        if not is_valid:
            errors.append(f"{fname}: {err_msg}")
            continue

        try:
            # Sanitize filename — giữ extension gốc
            base = fname.rsplit('.', 1)[0]
            safe_base = "".join(c for c in base if c.isalnum() or c in '_-')
            if not safe_base:
                safe_base = f"image_{idx}"
            safe_name = f"{safe_base}.{ext}"

            # Đảm bảo không trùng tên
            if safe_name in uploaded_files:
                safe_name = f"{safe_base}_{idx}.{ext}"

            filepath = os.path.join(session_folder, safe_name)
            with open(filepath, 'wb') as f:
                f.write(content)

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                uploaded_files.append(safe_name)
                print(f"  ✅ [{idx}] {fname} → {safe_name} ({img_w}×{img_h}px, {file_size/1024:.1f}KB)")
            else:
                errors.append(f"{fname}: Lưu file thất bại")
        except Exception as e:
            errors.append(f"{fname}: {str(e)}")

    if len(uploaded_files) == 0:
        try:
            shutil.rmtree(session_folder)
        except Exception:
            pass
        error_msg = "Không có file hợp lệ"
        if errors:
            error_msg += f". Lỗi: {'; '.join(errors[:3])}"
        raise HTTPException(status_code=400, detail=error_msg)

    # ── Save to Database ──
    # Always save session with user_id to enable filtering
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # Insert or update session with user_id
        cursor.execute(
            "INSERT INTO upload_sessions (session_id, user_id, total_images, upload_folder_path, status, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE total_images = %s, user_id = %s",
            (session_id, user.get("id"), len(uploaded_files), session_folder, 'uploaded', datetime.now(), len(uploaded_files), user.get("id"))
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Session {session_id} saved to database with {len(uploaded_files)} images")
    except Exception as e:
        print(f"⚠️  Database save failed (continuing anyway): {e}")
    
    # ── Legacy DB Manager (optional) ──
    if _ensure_db_managers():
        try:
            
            # Add images to session with full metadata
            for idx, filename in enumerate(uploaded_files, start=1):
                filepath = os.path.join(session_folder, filename)
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                
                # Get image dimensions
                width, height = None, None
                try:
                    with Image.open(filepath) as img:
                        width, height = img.size
                except Exception:
                    pass
                
                session_mgr.add_image(
                    session_id=session_id,
                    original_filename=filename,
                    stored_filename=filename,
                    file_path=filepath,
                    file_size=file_size,
                    width=width,
                    height=height,
                    upload_order=idx
                )
            
        except Exception as e:
            print(f"⚠️  Legacy DB logging failed (continuing anyway): {e}")

    # ── Log activity với đúng user_id ──
    try:
        conn_log = get_mysql_connection()
        cur_log = conn_log.cursor()
        cur_log.execute(
            "INSERT INTO activity_logs (user_id, session_id, action, resource_type, details, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (user.get("id"), session_id, 'upload', 'session', f"Uploaded {len(uploaded_files)} images", datetime.now())
        )
        conn_log.commit()
        cur_log.close()
        conn_log.close()
    except Exception as e:
        print(f"⚠️  Activity log failed: {e}")

    result = {
        "success": True,
        "session_id": session_id,
        "files": uploaded_files,
        "count": len(uploaded_files)
    }
    if errors:
        result["warnings"] = errors[:5]
    return result


@router.post("/generate")
@router.post("/sessions/generate")
async def generate_comic(
    data: GenerateRequest, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Tạo comic book từ ảnh đã upload. Cần session_id từ /upload trước."""
    if not _check_comic_engine_available():
        raise HTTPException(status_code=503, detail="Comic engine chưa được cài đặt")

    input_folder = validate_session(data.session_id)
    ensure_session_owner(data.session_id, user)
    if not os.path.exists(input_folder):
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn")

    image_files = list(Path(input_folder).glob('*'))
    if not image_files:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh trong session")

    output_folder = os.path.join(OUTPUT_FOLDER, data.session_id)

    # 🆕 Clear physical output folder
    if os.path.exists(output_folder):
        try:
            shutil.rmtree(output_folder)
        except Exception as e:
            print(f"⚠️  Không xóa được output cũ: {e}")
            # Fallback: cố gắng xóa từng file
            for f in Path(output_folder).glob('*'):
                try: f.unlink()
                except Exception: pass

    os.makedirs(output_folder, exist_ok=True)

    # 🆕 Clear database records for this session immediately to prevent stale previews
    if DB_AVAILABLE:
        try:
            conn_cl = get_mysql_connection()
            cur_cl = conn_cl.cursor()
            # Find project_id
            cur_cl.execute("SELECT id FROM comic_projects WHERE session_id = %s", (data.session_id,))
            proj_data = cur_cl.fetchone()
            if proj_data:
                # Clear existing pages
                cur_cl.execute("DELETE FROM comic_pages WHERE project_id = %s", (proj_data[0],))
                # Reset project status to processing
                cur_cl.execute("UPDATE comic_projects SET status = 'processing' WHERE id = %s", (proj_data[0],))
            conn_cl.commit()
            cur_cl.close()
            conn_cl.close()
        except Exception as db_err:
            print(f"⚠️  Failed to clear stale DB records: {db_err}")

    try:
        from app.services.comic_service import ComicService
        
        # Gọi Service để xử lý pipeline thay vì viết code logic trong file router
        # Inject json payload từ data model cho service
        service_result = ComicService.generate_comic_pipeline(
            input_folder=input_folder,
            output_folder=output_folder,
            file_json_data=data.model_dump(),
            user_id=user.get('id'),
            session_id=data.session_id
        )
        
        pages = [Path(p) for p in service_result["pages"]]
        
    except MemoryError:
        raise HTTPException(status_code=500, detail="Không đủ bộ nhớ. Thử giảm số ảnh hoặc DPI")
    except Exception as gen_error:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo comic: {str(gen_error)}")

    # ── AI Analysis & Save to Database (if enabled) ──
    if _ensure_db_managers() and _ensure_ai_modules() and (data.analyze_shot_type or data.classify_characters):
        try:
            print("🤖 Running AI Analysis on images...")
            analyzer = ImageAnalyzer()
            
            # Get list of uploaded images from database
            uploaded_images = session_mgr.get_session_images(data.session_id)
            
            for img_record in uploaded_images:
                if img_record.get('is_cover'):
                    continue  # Skip cover images
                
                img_path = os.path.join(input_folder, img_record['stored_filename'])
                if not os.path.exists(img_path):
                    continue
                
                try:
                    # Run analysis
                    analysis_result = analyzer.analyze_image(img_path)
                    
                    # Save to database
                    ai_analysis_mgr.save_analysis(
                        image_id=img_record['id'],
                        session_id=data.session_id,
                        analysis_type='full_analysis',
                        shot_type=analysis_result.get('shot_type'),
                        scene_classification=analysis_result.get('scene_type'),
                        characters_detected=analysis_result.get('characters', []),
                        face_count=analysis_result.get('face_count', 0),
                        confidence_score=analysis_result.get('confidence', 0.0),
                        raw_results=analysis_result
                    )
                except Exception as e:
                    print(f"⚠️  AI Analysis failed for {img_record['stored_filename']}: {e}")
            
            print(f"✅ AI Analysis completed for {len(uploaded_images)} images")
        except Exception as e:
            print(f"⚠️  AI Analysis batch failed (continuing anyway): {e}")

    # Cập nhật số trang chính xác từ kết quả thực tế
    if not pages:
        pages = (list(Path(output_folder).glob('page_*.png')) +
                 list(Path(output_folder).glob('page_*.jpg')))

    if not pages:
        raise HTTPException(status_code=500, detail="Không tạo được trang nào. Kiểm tra lại ảnh đầu vào")

    # Trigger Cloudinary upload (First page sync, rest background)
    if CLOUDINARY_ENABLED:
        # Sync upload first page for immediate preview if possible
        if pages:
            try:
                # Cố gắng upload trang 1 trước để user thấy ngay link cloud
                first_page = str(pages[0])
                res = upload_image(first_page, folder=f"comic_ai/{data.session_id}", public_id="page_1")
                print(f"☁️ Synchronous cloud upload for page 1 successful: {res.get('url')}")
            except Exception as e:
                print(f"⚠️ Initial cloud upload failed: {e}")
        
        background_tasks.add_task(upload_session_to_cloudinary_bg, data.session_id)

    # ── Log activity với đúng user_id (lấy từ session trong DB) ──
    try:
        conn_log = get_mysql_connection()
        cur_log = conn_log.cursor(dictionary=True)
        
        # Lấy user_id từ session (vì generate không có token nhưng biết session_id)
        cur_log.execute(
            "INSERT INTO activity_logs (user_id, session_id, action, resource_type, details, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (user.get("id"), data.session_id, 'generate', 'session',
             f"Generated {len(pages)} pages using {data.layout_mode} mode", datetime.now())
        )
        conn_log.commit()
        cur_log.close()
        conn_log.close()
    except Exception as e:
        print(f"⚠️  Activity log failed: {e}")

    return {
        "success": True,
        "session_id": data.session_id,
        "pages": len(pages),
        "layout_mode": data.layout_mode
    }


@router.post("/auto-frames")
@router.post("/sessions/auto-frames")
async def generate_auto_frames(data: AutoFrameRequest, request: Request, user: dict = Depends(get_current_user)):
    """Tạo khung truyện tự động không cần upload ảnh đầu vào."""
    session_id = uuid4().hex
    upload_folder = os.path.join(UPLOAD_FOLDER, session_id)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    resolution_map = {
        "1K": 1000,
        "2K": 2000,
        "4K": 4000,
    }
    aspect_ratio_map = {
        "1:1":  (1, 1),
        "2:3":  (2, 3),
        "3:2":  (3, 2),
        "3:4":  (3, 4),
        "4:3":  (4, 3),
        "4:5":  (4, 5),
        "5:4":  (5, 4),
        "9:16": (9, 16),
        "16:9": (16, 9),
        "21:9": (21, 9),
    }

    base_width = resolution_map.get(data.resolution, 2000)
    ratio_w, ratio_h = aspect_ratio_map.get(data.aspect_ratio, (16, 9))
    page_width  = base_width
    page_height = int(base_width * ratio_h / ratio_w)

    coord_w = 1000.0
    coord_h = max(500.0, coord_w * (ratio_h / ratio_w))
    border_width = max(2, int(page_width * 0.003))
    gutter = max(6.0, min(30.0, 6.0 + 18.0 * data.diagonal_prob))

    # Import hàm layout từ service (tránh code trùng lặp)
    try:
        from app.services.comic.comic_book_auto_fill import create_auto_frame_layout
    except ImportError as _exc:
        raise HTTPException(status_code=500, detail=f"Comic engine unavailable: {_exc}")

    generated_files = []
    pages_layout = []

    for page_idx in range(1, data.pages_count + 1):
        try:
            panels_vertices = create_auto_frame_layout(
                target_count=data.panels_per_page,
                coord_w=coord_w,
                coord_h=coord_h,
                diagonal_prob=data.diagonal_prob,
                gutter=gutter,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Lỗi tạo layout trang {page_idx}: {exc}")

        canvas = Image.new("RGB", (page_width, page_height), "white")

        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(canvas)
            sx = page_width  / coord_w
            sy = page_height / coord_h

            radius = max(10, int(page_width * 0.012 * data.panel_number_font_scale))
            font_size = int(radius * 1.5)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                except IOError:
                    try:
                        font = ImageFont.load_default(size=font_size)
                    except TypeError:
                        font = ImageFont.load_default()

            for panel_idx, vertices in enumerate(panels_vertices, 1):
                pts = [
                    (
                        int(max(0, min(page_width,  x * sx))),
                        int(max(0, min(page_height, y * sy))),
                    )
                    for x, y in vertices
                ]
                if len(pts) >= 3:
                    draw.polygon(pts, fill="white", outline="black", width=border_width)

                    if data.draw_panel_numbers:
                        cx = int(sum(p[0] for p in pts) / len(pts))
                        cy = int(sum(p[1] for p in pts) / len(pts))
                        draw.ellipse(
                            (cx - radius, cy - radius, cx + radius, cy + radius),
                            fill="#111111",
                            outline="white",
                            width=max(1, border_width // 2),
                        )
                        draw.text((cx, cy), str(panel_idx), fill="white", anchor="mm", font=font)

            # Lưu layout metadata theo thứ tự panel đọc trang.
            panel_entries = []
            for panel_idx, vertices in enumerate(panels_vertices, 1):
                scaled_vertices = []
                min_x = float("inf")
                min_y = float("inf")
                max_x = float("-inf")
                max_y = float("-inf")
                for x, y in vertices:
                    px = float(max(0, min(page_width, x * sx)))
                    py = float(max(0, min(page_height, y * sy)))
                    scaled_vertices.append({"x": px, "y": py})
                    min_x = min(min_x, px)
                    min_y = min(min_y, py)
                    max_x = max(max_x, px)
                    max_y = max(max_y, py)

                panel_entries.append(
                    {
                        "panel_id": panel_idx,
                        "panel_order": panel_idx,
                        "page_number": page_idx,
                        "vertices": scaled_vertices,
                        "bbox": {
                            "x": min_x,
                            "y": min_y,
                            "w": max(0.0, max_x - min_x),
                            "h": max(0.0, max_y - min_y),
                        },
                    }
                )

            pages_layout.append(
                {
                    "page_number": page_idx,
                    "width": page_width,
                    "height": page_height,
                    "panels_count": len(panel_entries),
                    "reading_direction": "ltr",
                    "panel_numbering": bool(data.draw_panel_numbers),
                    "panels": panel_entries,
                }
            )

            page_name = f"page_{page_idx:03d}.jpg"
            save_path = os.path.join(output_folder, page_name)
            canvas.save(save_path, quality=95)
            generated_files.append(page_name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Lỗi render trang {page_idx}: {exc}")

    project_id = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO upload_sessions (session_id, user_id, total_images, upload_folder_path, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (session_id, user.get("id"), 0, upload_folder, "completed", datetime.now()),
        )

        cursor.execute(
            """
            INSERT INTO comic_projects
            (session_id, user_id, project_name, layout_mode, panels_per_page, diagonal_prob,
             resolution, aspect_ratio, reading_direction, output_folder_path, total_pages, status,
             processing_completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                user.get("id"),
                f"Auto Frame {session_id[:8]}",
                "advanced",
                data.panels_per_page,
                data.diagonal_prob,
                data.resolution,
                data.aspect_ratio,
                "ltr",
                output_folder,
                len(generated_files),
                "completed",
                datetime.now(),
            ),
        )
        project_id = cursor.lastrowid

        for page_meta, page_name in zip(pages_layout, generated_files):
            cursor.execute(
                """
                INSERT INTO comic_pages
                (project_id, page_number, page_type, panels_count, layout_structure, output_image_path, width, height)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    page_meta["page_number"],
                    "content",
                    page_meta["panels_count"],
                    json.dumps(page_meta, ensure_ascii=False),
                    None,
                    page_meta["width"],
                    page_meta["height"],
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️  Database save failed for auto-frames session: {e}")

    try:
        conn_log = get_mysql_connection()
        cur_log = conn_log.cursor()
        cur_log.execute(
            "INSERT INTO activity_logs (user_id, session_id, action, resource_type, details, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                user.get("id"),
                session_id,
                "auto_frames",
                "session",
                f"Generated {data.pages_count} frame-only pages ({data.panels_per_page} panels/page, diagonal={int(data.diagonal_prob * 100)}%)",
                datetime.now(),
            ),
        )
        conn_log.commit()
        cur_log.close()
        conn_log.close()
    except Exception as e:
        print(f"⚠️  Activity log failed (auto-frames): {e}")

    media_token = create_media_access_token(session_id, user.get("id"), settings.SECRET_KEY)
    base_url = str(request.base_url).rstrip("/")
    page_urls = [
        f"{base_url}/api/v1/comic/sessions/{session_id}/outputs/{name}?st={media_token}"
        for name in generated_files
    ]

    return {
        "success": True,
        "session_id": session_id,
        "pages": page_urls,
        "count": len(page_urls),
        "config": {
            "panels_per_page": data.panels_per_page,
            "diagonal_prob":   data.diagonal_prob,
            "aspect_ratio":    data.aspect_ratio,
            "resolution":      data.resolution,
            "pages_count":     data.pages_count,
            "draw_panel_numbers": data.draw_panel_numbers,
        },
        "project_id": project_id,
    }


@router.get("/sessions/{session_id}/frame-layout")
async def get_auto_frame_layout(session_id: str, user: dict = Depends(get_current_user)):
    """Trả metadata layout khung để phục vụ bước ghép ảnh vào template đã tạo."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT cp.page_number, cp.panels_count, cp.layout_structure, cp.output_image_path
            FROM comic_pages cp
            JOIN comic_projects p ON cp.project_id = p.id
            WHERE p.session_id = %s
            ORDER BY cp.page_number ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể tải layout khung: {e}")

    if not rows:
        return {"success": True, "session_id": session_id, "pages": [], "count": 0}

    pages = []
    for row in rows:
        layout_raw = row.get("layout_structure")
        try:
            parsed = json.loads(layout_raw) if layout_raw else {}
        except Exception:
            parsed = {}

        pages.append(
            {
                "page_number": row.get("page_number"),
                "panels_count": row.get("panels_count", 0),
                "output_image_path": row.get("output_image_path"),
                "layout": parsed,
            }
        )

    return {
        "success": True,
        "session_id": session_id,
        "pages": pages,
        "count": len(pages),
    }


def _prepare_panel_image(file_source, panel_w: int, panel_h: int) -> Image.Image:
    """Resize/crop uploaded image to cover a panel bbox.

    file_source có thể là UploadFile hoặc raw bytes.
    """
    if panel_w <= 0 or panel_h <= 0:
        raise ValueError("Invalid panel size")

    if hasattr(file_source, "file"):
        file_source.file.seek(0)
        with Image.open(file_source.file) as src_img:
            img = src_img.convert("RGB")
    else:
        with Image.open(io.BytesIO(file_source)) as src_img:
            img = src_img.convert("RGB")

    img_aspect = img.width / max(1, img.height)
    panel_aspect = panel_w / max(1, panel_h)

    if img_aspect > panel_aspect:
        crop_w = int(img.height * panel_aspect)
        left = max(0, (img.width - crop_w) // 2)
        img = img.crop((left, 0, left + crop_w, img.height))
    else:
        crop_h = int(img.width / max(1e-6, panel_aspect))
        top = max(0, (img.height - crop_h) // 2)
        img = img.crop((0, top, img.width, top + crop_h))

    return img.resize((panel_w, panel_h), Image.Resampling.LANCZOS)


def _collect_panel_slots(layout_pages: List[dict]) -> List[dict]:
    slots = []
    for page in sorted(layout_pages, key=lambda p: int(p.get("page_number", 0))):
        layout = page.get("layout") if isinstance(page.get("layout"), dict) else {}
        panels = layout.get("panels") if isinstance(layout, dict) else []
        for panel in sorted(panels or [], key=lambda p: int(p.get("panel_order", p.get("panel_id", 0)))):
            bbox = panel.get("bbox") or {}
            vertices = panel.get("vertices") or []
            slots.append(
                {
                    "global_order": len(slots) + 1,
                    "page_number": int(page.get("page_number", 0)),
                    "panel_order": int(panel.get("panel_order", panel.get("panel_id", 0))),
                    "bbox": {
                        "x": int(round(float(bbox.get("x", 0)))),
                        "y": int(round(float(bbox.get("y", 0)))),
                        "w": max(1, int(round(float(bbox.get("w", 1))))),
                        "h": max(1, int(round(float(bbox.get("h", 1))))),
                    },
                    "vertices": [
                        (int(round(float(v.get("x", 0)))), int(round(float(v.get("y", 0)))))
                        for v in vertices
                    ],
                }
            )
    return slots


def _render_filled_pages(session_id: str, slots: List[dict], files: List[UploadFile], mapping: dict) -> List[str]:
    """Apply mapped images to panel polygons and overwrite output pages."""
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Không tìm thấy output folder của session")

    by_page = {}
    for slot in slots:
        by_page.setdefault(slot["page_number"], []).append(slot)

    changed_pages = []
    for page_number, page_slots in sorted(by_page.items(), key=lambda kv: kv[0]):
        page_path_jpg = os.path.join(output_folder, f"page_{page_number:03d}.jpg")
        page_path_png = os.path.join(output_folder, f"page_{page_number:03d}.png")
        page_path = page_path_jpg if os.path.exists(page_path_jpg) else page_path_png

        if not os.path.exists(page_path):
            continue

        with Image.open(page_path) as page_src:
            canvas = page_src.convert("RGBA")
        page_changed = False

        for slot in sorted(page_slots, key=lambda s: s["panel_order"]):
            slot_key = slot["global_order"]
            file_idx = mapping.get(slot_key)
            if file_idx is None or file_idx < 0 or file_idx >= len(files):
                continue

            bbox = slot["bbox"]
            bx, by, bw, bh = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
            panel_img = _prepare_panel_image(files[file_idx], bw, bh)

            local_vertices = []
            for vx, vy in slot["vertices"]:
                local_vertices.append((max(0, vx - bx), max(0, vy - by)))

            mask = Image.new("L", (bw, bh), 0)
            from PIL import ImageDraw
            mdraw = ImageDraw.Draw(mask)
            if len(local_vertices) >= 3:
                mdraw.polygon(local_vertices, fill=255)
            else:
                mdraw.rectangle((0, 0, bw, bh), fill=255)

            patch = panel_img.convert("RGBA")
            canvas.paste(patch, (bx, by), mask)
            page_changed = True

            # Giải phóng sớm object ảnh để giảm peak RAM trên request lớn.
            patch.close()
            panel_img.close()
            mask.close()

        if page_changed:
            out_rgb = canvas.convert("RGB")
            out_rgb.save(page_path_jpg, quality=95)
            out_rgb.close()
            changed_pages.append(os.path.basename(page_path_jpg))

        canvas.close()

    return changed_pages


@router.post("/sessions/{session_id}/fill-panels/auto")
async def fill_panels_auto(
    session_id: str,
    request: Request,
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    """Ghép ảnh tự động theo thứ tự panel đã lưu (1→N)."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    layout_result = await get_auto_frame_layout(session_id, user)
    pages = layout_result.get("pages", [])
    if not pages:
        raise HTTPException(status_code=404, detail="Không tìm thấy layout khung để ghép ảnh")

    slots = _collect_panel_slots(pages)
    if not slots:
        raise HTTPException(status_code=400, detail="Layout khung không có panel hợp lệ")

    valid_files = [f for f in files if f and f.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="Không có ảnh hợp lệ để ghép")

    max_assign = min(len(slots), len(valid_files))
    mapping = {slot_idx: slot_idx - 1 for slot_idx in range(1, max_assign + 1)}

    changed_pages = _render_filled_pages(session_id, slots, valid_files, mapping)

    media_token = create_media_access_token(session_id, user.get("id"), settings.SECRET_KEY)
    base_url = str(request.base_url).rstrip("/")
    page_urls = [
        f"{base_url}/api/v1/comic/sessions/{session_id}/outputs/{name}?st={media_token}"
        for name in sorted(changed_pages)
    ]

    return {
        "success": True,
        "session_id": session_id,
        "mode": "auto",
        "assigned_panels": max_assign,
        "total_panels": len(slots),
        "updated_pages": page_urls,
    }


@router.post("/sessions/{session_id}/fill-panels/manual")
async def fill_panels_manual(
    session_id: str,
    request: Request,
    mapping_json: str = Form(...),
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    """Ghép ảnh thủ công theo mapping panel_order → file_index."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    try:
        raw_mapping = json.loads(mapping_json)
    except Exception:
        raise HTTPException(status_code=400, detail="mapping_json không hợp lệ")

    if not isinstance(raw_mapping, dict) or not raw_mapping:
        raise HTTPException(status_code=400, detail="mapping_json phải là object có dữ liệu")

    layout_result = await get_auto_frame_layout(session_id, user)
    pages = layout_result.get("pages", [])
    if not pages:
        raise HTTPException(status_code=404, detail="Không tìm thấy layout khung để ghép ảnh")

    slots = _collect_panel_slots(pages)
    if not slots:
        raise HTTPException(status_code=400, detail="Layout khung không có panel hợp lệ")

    valid_files = [f for f in files if f and f.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="Không có ảnh hợp lệ để ghép")

    mapping = {}
    for k, v in raw_mapping.items():
        try:
            panel_order = int(k)
            file_idx = int(v)
        except Exception:
            continue
        mapping[panel_order] = file_idx

    if not mapping:
        raise HTTPException(status_code=400, detail="Không có mapping hợp lệ")

    changed_pages = _render_filled_pages(session_id, slots, valid_files, mapping)

    media_token = create_media_access_token(session_id, user.get("id"), settings.SECRET_KEY)
    base_url = str(request.base_url).rstrip("/")
    page_urls = [
        f"{base_url}/api/v1/comic/sessions/{session_id}/outputs/{name}?st={media_token}"
        for name in sorted(changed_pages)
    ]

    return {
        "success": True,
        "session_id": session_id,
        "mode": "manual",
        "assigned_panels": len(mapping),
        "total_panels": len(slots),
        "updated_pages": page_urls,
    }


@router.delete("/clear/{session_id}")
@router.delete("/sessions/{session_id}/clear")
async def clear_session(session_id: str, user: dict = Depends(get_current_user)):
    """Xóa session (upload + output)."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    try:
        upload_folder = os.path.join(UPLOAD_FOLDER, session_id)
        output_folder = os.path.join(OUTPUT_FOLDER, session_id)

        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_cover/{session_id}")
@router.post("/sessions/{session_id}/covers/upload")
async def upload_cover(session_id: str, cover_type: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload ảnh bìa (front/back/thank_you) cho một session."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)

    if cover_type not in COVER_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"cover_type phải là: {', '.join(COVER_TYPES)}"
        )

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File trống")

    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Định dạng không hỗ trợ")

    covers_folder = os.path.join(OUTPUT_FOLDER, session_id, 'covers')
    os.makedirs(covers_folder, exist_ok=True)

    ext = file.filename.rsplit('.', 1)[1].lower()
    save_name = f'{cover_type}.{ext}'
    save_path = os.path.join(covers_folder, save_name)

    content = await file.read()
    with open(save_path, 'wb') as f:
        f.write(content)

    return {
        "success": True,
        "cover_type": cover_type,
        "url": f"/api/v1/comic/sessions/{session_id}/covers/{save_name}?st={create_media_access_token(session_id, user.get('id'), settings.SECRET_KEY)}"
    }


@router.get("/sessions/{session_id}/covers")
async def get_covers(session_id: str, user: dict = Depends(get_current_user)):
    """Lấy danh sách bìa đã upload."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    covers_folder = os.path.join(OUTPUT_FOLDER, session_id, 'covers')

    if not os.path.exists(covers_folder):
        return {"success": True, "covers": {}}

    covers = {}
    media_token = create_media_access_token(session_id, user.get("id"), settings.SECRET_KEY)
    for cover_type in COVER_TYPES:
        for ext in ALLOWED_EXTENSIONS:
            path = os.path.join(covers_folder, f'{cover_type}.{ext}')
            if os.path.exists(path):
                covers[cover_type] = f"/api/v1/comic/sessions/{session_id}/covers/{cover_type}.{ext}?st={media_token}"
                break

    return {"success": True, "covers": covers}


@router.get("/ai_capabilities")
@router.get("/capabilities")
async def ai_capabilities():
    """Kiểm tra các AI features và trạng thái của chúng."""
    ai_ready = _ensure_ai_modules()
    comic_ready = _check_comic_engine_available()
    return {
        "ai_analysis_available": ai_ready,
        "comic_engine_available": comic_ready,
        "features": {
            "character_classification": {
                "available": ai_ready,
                "description": "Phân loại nhân vật (Primary/Secondary/Background)"
            },
            "face_recognition": {
                "available": FACE_RECOGNITION_AVAILABLE,
                "description": "Nhận diện tên nhân vật từ database",
                "requires_install": not FACE_RECOGNITION_AVAILABLE
            },
            "scene_classification": {
                "available": ai_ready,
                "description": "Phân loại cảnh (close_up, action, dialogue, group, normal)",
                "methods": ["rule_based", "ai_model", "hybrid"]
            },
            "smart_crop": {
                "available": True,
                "description": "Crop thông minh giữ vùng quan trọng"
            }
        },
        "recommendations": [] if ai_ready else [
            "Install: pip install ultralytics opencv-python Pillow"
        ]
    }


