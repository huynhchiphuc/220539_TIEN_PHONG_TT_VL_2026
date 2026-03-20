"""
Router ComicCraft AI - Chuyển đổi từ THUC_TAP2/app.py (Flask)
sang chuẩn FastAPI của dự án 220359_TIEN_PHONG_TT_VL_2026
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import List
from dataclasses import dataclass
import importlib.util
import os
import shutil
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
        "1:1": (1, 1),
        "2:3": (2, 3),
        "3:2": (3, 2),
        "3:4": (3, 4),
        "4:3": (4, 3),
        "4:5": (4, 5),
        "5:4": (5, 4),
        "9:16": (9, 16),
        "16:9": (16, 9),
        "21:9": (21, 9),
    }

    base_width = resolution_map.get(data.resolution, 2000)
    ratio_w, ratio_h = aspect_ratio_map.get(data.aspect_ratio, (16, 9))
    page_width = base_width
    page_height = int(base_width * ratio_h / ratio_w)

    coord_w = 1000.0
    coord_h = max(500.0, coord_w * (ratio_h / ratio_w))
    border_width = max(2, int(page_width * 0.003))
    gutter = max(6.0, min(30.0, 6.0 + 18.0 * data.diagonal_prob))
    min_panel_w = max(80.0, coord_w * 0.12)
    min_panel_h = max(80.0, coord_h * 0.12)
    ideal_panel_aspect = max(0.55, min(2.1, coord_w / max(1e-6, coord_h)))

    generated_files = []

    @dataclass
    class Point:
        x: float
        y: float

    @dataclass
    class Polygon:
        vertices: List[Point]

        def bbox(self):
            xs = [p.x for p in self.vertices]
            ys = [p.y for p in self.vertices]
            return min(xs), min(ys), max(xs), max(ys)

        def area(self):
            pts = self.vertices
            total = 0.0
            for idx in range(len(pts)):
                p1 = pts[idx]
                p2 = pts[(idx + 1) % len(pts)]
                total += p1.x * p2.y - p2.x * p1.y
            return abs(total) * 0.5

    @dataclass
    class PanelTree:
        polygon: Polygon
        left: "PanelTree | None" = None
        right: "PanelTree | None" = None

    def _lerp(a: Point, b: Point, t: float) -> Point:
        return Point(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)

    def _clamp_point(pt: Point) -> Point:
        return Point(
            max(2.0, min(coord_w - 2.0, pt.x)),
            max(2.0, min(coord_h - 2.0, pt.y)),
        )

    def _offset_cut_edge(a: Point, b: Point, distance: float):
        dx = b.x - a.x
        dy = b.y - a.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return a, b, a, b
        nx = -dy / length
        ny = dx / length
        top_a = _clamp_point(Point(a.x - nx * distance, a.y - ny * distance))
        top_b = _clamp_point(Point(b.x - nx * distance, b.y - ny * distance))
        bottom_a = _clamp_point(Point(a.x + nx * distance, a.y + ny * distance))
        bottom_b = _clamp_point(Point(b.x + nx * distance, b.y + ny * distance))
        return top_a, top_b, bottom_a, bottom_b

    def _can_split(poly: Polygon) -> bool:
        x0, y0, x1, y1 = poly.bbox()
        return (x1 - x0) >= (min_panel_w * 1.3) and (y1 - y0) >= (min_panel_h * 1.3) and poly.area() >= (min_panel_w * min_panel_h)

    def _slice_polygon(poly: Polygon, split_ratio: float = 0.5, force_axis: str | None = None):
        v0, v1, v2, v3 = poly.vertices
        x0, y0, x1, y1 = poly.bbox()
        bbox_w = max(1e-6, x1 - x0)
        bbox_h = max(1e-6, y1 - y0)

        if force_axis is None:
            if bbox_w > bbox_h * 1.25:
                axis = "vertical"
            elif bbox_h > bbox_w * 1.25:
                axis = "horizontal"
            else:
                axis = "horizontal" if random.random() < 0.5 else "vertical"
        else:
            axis = force_axis

        split_ratio = max(0.22, min(0.78, split_ratio))
        skew_jitter = 0.02 + (0.10 * data.diagonal_prob)
        line_tilt = (0.01 + 0.10 * data.diagonal_prob) * (1 if random.random() > 0.5 else -1)
        t1 = max(0.18, min(0.82, split_ratio + random.uniform(-skew_jitter, skew_jitter)))
        t2 = max(0.18, min(0.82, split_ratio + line_tilt + random.uniform(-skew_jitter, skew_jitter)))

        if axis == "horizontal":
            left_cut = _lerp(v0, v3, t1)
            right_cut = _lerp(v1, v2, t2)
            top_left, top_right, bottom_left, bottom_right = _offset_cut_edge(left_cut, right_cut, gutter * 0.5)
            top_poly = Polygon([v0, v1, top_right, top_left])
            bottom_poly = Polygon([bottom_left, bottom_right, v2, v3])
            return top_poly, bottom_poly

        top_cut = _lerp(v0, v1, t1)
        bottom_cut = _lerp(v3, v2, t2)
        side_a_top, side_a_bottom, side_b_top, side_b_bottom = _offset_cut_edge(top_cut, bottom_cut, gutter * 0.5)
        # side_a và side_b nằm 2 phía của đường cắt; với cắt dọc ta gán
        # polygon trái dùng cạnh lệch về trái, polygon phải dùng cạnh lệch về phải để tạo gutter thật.
        left_poly = Polygon([v0, side_b_top, side_b_bottom, v3])
        right_poly = Polygon([side_a_top, v1, v2, side_a_bottom])
        return left_poly, right_poly

    def _panel_badness(poly: Polygon) -> float:
        x0, y0, x1, y1 = poly.bbox()
        w = max(1e-6, x1 - x0)
        h = max(1e-6, y1 - y0)
        ar = w / h
        score = abs(math.log(max(1e-6, ar / ideal_panel_aspect)))
        if ar < 0.45:
            score += (0.45 - ar) * 6.0
        if ar > 2.6:
            score += (ar - 2.6) * 3.0
        if w < min_panel_w:
            score += ((min_panel_w - w) / min_panel_w) * 2.0
        if h < min_panel_h:
            score += ((min_panel_h - h) / min_panel_h) * 2.0
        return score

    def _choose_quota_pair(total_quota: int):
        if total_quota <= 2:
            return 1, max(1, total_quota - 1)
        base_left = total_quota // 2
        base_right = total_quota - base_left
        if total_quota >= 6 and random.random() < 0.35:
            # Cho layout có nhịp điệu nhưng vẫn tránh lệch cực đoan.
            swing = 1 if random.random() < 0.5 else -1
            base_left = max(1, min(total_quota - 1, base_left + swing))
            base_right = total_quota - base_left
        return base_left, base_right

    def _best_split(poly: Polygon, left_quota: int, right_quota: int):
        x0, y0, x1, y1 = poly.bbox()
        bbox_w = max(1e-6, x1 - x0)
        bbox_h = max(1e-6, y1 - y0)
        target_ratio = left_quota / max(1, left_quota + right_quota)

        if bbox_w > bbox_h * 1.2:
            axis_candidates = ["vertical", "horizontal"]
        elif bbox_h > bbox_w * 1.2:
            axis_candidates = ["horizontal", "vertical"]
        else:
            axis_candidates = ["horizontal", "vertical"]

        best = None
        best_score = float("inf")

        for axis in axis_candidates:
            for _ in range(10):
                try:
                    left_poly, right_poly = _slice_polygon(poly, split_ratio=target_ratio, force_axis=axis)
                except Exception:
                    continue

                area_left = max(1e-6, left_poly.area())
                area_right = max(1e-6, right_poly.area())
                actual_ratio = area_left / (area_left + area_right)
                area_balance_penalty = abs(actual_ratio - target_ratio) * 8.0

                quota_viability_penalty = 0.0
                if left_quota > 1 and not _can_split(left_poly):
                    quota_viability_penalty += 3.0
                if right_quota > 1 and not _can_split(right_poly):
                    quota_viability_penalty += 3.0

                score = (
                    area_balance_penalty
                    + _panel_badness(left_poly)
                    + _panel_badness(right_poly)
                    + quota_viability_penalty
                )

                if score < best_score:
                    best_score = score
                    best = (left_poly, right_poly)

        return best

    def _collect_leaves(node: PanelTree, out: List[PanelTree]):
        if node.left is None and node.right is None:
            out.append(node)
            return
        if node.left is not None:
            _collect_leaves(node.left, out)
        if node.right is not None:
            _collect_leaves(node.right, out)

    def _subdivide_recursive(node: PanelTree, target_leaf_count: int):
        if target_leaf_count <= 1 or not _can_split(node.polygon):
            return

        left_quota, right_quota = _choose_quota_pair(target_leaf_count)
        best = _best_split(node.polygon, left_quota, right_quota)
        if best is None:
            return

        left_poly, right_poly = best

        node.left = PanelTree(left_poly)
        node.right = PanelTree(right_poly)

        if target_leaf_count == 2:
            return

        _subdivide_recursive(node.left, left_quota)
        _subdivide_recursive(node.right, right_quota)

    def _largest_splittable_leaf(root: PanelTree):
        leaves = []
        _collect_leaves(root, leaves)
        candidates = [leaf for leaf in leaves if _can_split(leaf.polygon)]
        if not candidates:
            return None
        return max(candidates, key=lambda node: node.polygon.area())

    def _build_panels(target_count: int):
        root_poly = Polygon([
            Point(4.0, 4.0),
            Point(coord_w - 4.0, 4.0),
            Point(coord_w - 4.0, coord_h - 4.0),
            Point(4.0, coord_h - 4.0),
        ])
        root = PanelTree(root_poly)
        _subdivide_recursive(root, max(1, target_count))

        leaves = []
        _collect_leaves(root, leaves)

        while len(leaves) < target_count:
            candidate = _largest_splittable_leaf(root)
            if candidate is None:
                break
            best = _best_split(candidate.polygon, 1, 1)
            if best is None:
                break
            left_poly, right_poly = best
            candidate.left = PanelTree(left_poly)
            candidate.right = PanelTree(right_poly)
            leaves = []
            _collect_leaves(root, leaves)

        return leaves[:target_count]

    for page_idx in range(1, data.pages_count + 1):
        try:
            panel_nodes = _build_panels(data.panels_per_page)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Lỗi tạo layout trang {page_idx}: {exc}")

        canvas = Image.new("RGB", (page_width, page_height), "white")

        try:
            from PIL import ImageDraw

            draw = ImageDraw.Draw(canvas)
            sx = page_width / coord_w
            sy = page_height / coord_h

            for panel in panel_nodes:
                pts = [
                    (
                        int(max(0, min(page_width, v.x * sx))),
                        int(max(0, min(page_height, v.y * sy))),
                    )
                    for v in panel.polygon.vertices
                ]
                if len(pts) >= 3:
                    draw.polygon(pts, fill="white", outline="black", width=border_width)

            page_name = f"page_{page_idx:03d}.jpg"
            save_path = os.path.join(output_folder, page_name)
            canvas.save(save_path, quality=95)
            generated_files.append(page_name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Lỗi render trang {page_idx}: {exc}")

    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO upload_sessions (session_id, user_id, total_images, upload_folder_path, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (session_id, user.get("id"), 0, upload_folder, "completed", datetime.now()),
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
            "diagonal_prob": data.diagonal_prob,
            "aspect_ratio": data.aspect_ratio,
            "resolution": data.resolution,
            "pages_count": data.pages_count,
        },
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


