"""
Router ComicCraft AI - Chuyển đổi từ THUC_TAP2/app.py (Flask)
sang chuẩn FastAPI của dự án 220359_TIEN_PHONG_TT_VL_2026
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pathlib import Path
from typing import List, Optional
import os
import shutil
import zipfile
import io
import time
from PIL import Image
from datetime import datetime
from uuid import uuid4
from jose import jwt, JWTError

from app.models.comic import GenerateRequest
from app.config import settings
from app.security.security import get_current_user
from app.utils.mysql_connection import get_mysql_connection

# ── Database Manager (Optional - graceful fallback) ──

try:
    from app.utils.db_manager import (
        MySQLDatabase, SessionManager, ProjectManager, 
        ActivityLogger, AIAnalysisManager, UserPreferencesManager
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
    project_mgr = ProjectManager(db)
    activity_logger = ActivityLogger(db)
    ai_analysis_mgr = AIAnalysisManager(db)
    user_prefs_mgr = UserPreferencesManager(db)
    DB_AVAILABLE = True
    print("✅ MySQL Database connected")
except Exception as e:
    DB_AVAILABLE = False
    print(f"⚠️  Database không khả dụng (app vẫn hoạt động với file storage): {e}")

# ── Import các utility modules từ THUC_TAP2 (optional, graceful fallback) ──

try:
    from app.utils.comic_book_auto_fill import create_comic_book_from_images
    from app.utils.comic_layout_simple import process_comic_layout
    COMIC_ENGINE_AVAILABLE = True
    print("✅ Comic Engine loaded")
except ImportError as e:
    COMIC_ENGINE_AVAILABLE = False
    print(f"⚠️  Comic Engine không có: {e}")

try:
    from app.utils.character_classifier import CharacterClassifier, FACE_RECOGNITION_AVAILABLE
    from app.utils.scene_classifier import SceneClassifier, AI_MODEL_AVAILABLE as CLIP_AVAILABLE
    from app.utils.image_analyzer import ImageAnalyzer
    AI_ANALYSIS_AVAILABLE = True
    print("✅ AI Analysis Modules loaded")
except ImportError as e:
    AI_ANALYSIS_AVAILABLE = False
    FACE_RECOGNITION_AVAILABLE = False
    CLIP_AVAILABLE = False
    print(f"⚠️  AI Analysis không có: {e}")

try:
    from app.utils.validation import validate_file, validate_session_id, ValidationError
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️  Validation module không có.")


# ── Cấu hình ──────────────────────────────────────────────────────────────────

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
COVER_TYPES = {'front', 'back', 'thank_you'}
MEDIA_TOKEN_EXPIRE_MINUTES = 30

# Giới hạn kích thước và độ phân giải
MIN_FILE_SIZE = 1024           # 1 KB — file nhỏ hơn này coi là rỗng/hỏng
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50 MB per file
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB toàn session
MIN_RESOLUTION = 50            # 50px — ảnh nhỏ hơn này vô dụng
MAX_RESOLUTION = 12000         # 12000px — tránh memory bomb

# Magic bytes để xác thực nội dung file thực sự
MAGIC_BYTES = {
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png':  [b'\x89PNG\r\n\x1a\n'],
    'gif':  [b'GIF87a', b'GIF89a'],
    'bmp':  [b'BM'],
    'webp': None,  # RIFF....WEBP — xử lý đặc biệt
}

# Đảm bảo thư mục tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/comic", tags=["comic"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_magic_bytes(content: bytes, ext: str) -> bool:
    """Kiểm tra magic bytes để xác thực file thực sự là ảnh, không phải file rename."""
    if len(content) < 12:
        return False
    ext = ext.lower()
    if ext == 'webp':
        return content[:4] == b'RIFF' and content[8:12] == b'WEBP'
    signatures = MAGIC_BYTES.get(ext)
    if signatures is None:
        return True   # Extension không biết, cho qua
    return any(content[:len(sig)] == sig for sig in signatures)


def validate_image_content(content: bytes, filename: str) -> tuple:
    """
    Kiểm tra sâu nội dung ảnh bằng PIL.
    Returns (is_valid: bool, error_msg: str, width: int, height: int)
    """
    from io import BytesIO
    try:
        with Image.open(BytesIO(content)) as img:
            img.load()  # Force decode — phát hiện dữ liệu hỏng
            width, height = img.size

        if width < MIN_RESOLUTION or height < MIN_RESOLUTION:
            return False, f"Ảnh quá nhỏ ({width}×{height}px). Tối thiểu {MIN_RESOLUTION}×{MIN_RESOLUTION}px", width, height

        if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
            return False, f"Ảnh quá lớn ({width}×{height}px). Tối đa {MAX_RESOLUTION}×{MAX_RESOLUTION}px", width, height

        return True, "", width, height

    except Exception as e:
        return False, f"File ảnh bị hỏng hoặc không đọc được: {str(e)[:80]}", 0, 0


def detect_image_orientation(input_folder: str):
    """Phát hiện orientation chủ đạo của ảnh đầu vào."""
    try:
        valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')
        image_files = [
            os.path.join(input_folder, f)
            for f in os.listdir(input_folder)
            if f.lower().endswith(valid_exts)
        ]
        if not image_files:
            return 'landscape', '16:9'

        portrait_aspects = []
        landscape_aspects = []
        sample_files = image_files[:min(20, len(image_files))]

        for img_path in sample_files:
            try:
                with Image.open(img_path) as img:
                    w, h = img.size
                    aspect = w / h
                    if aspect < 0.95:
                        portrait_aspects.append(aspect)
                    else:
                        landscape_aspects.append(aspect)
            except Exception:
                continue

        all_aspects = portrait_aspects + landscape_aspects
        if not all_aspects:
            return 'landscape', '16:9'

        overall_avg_aspect = sum(all_aspects) / len(all_aspects)

        if overall_avg_aspect < 0.95:
            orientation = 'portrait'
            if overall_avg_aspect <= 0.56:
                aspect_suggestion = '9:16'
            elif overall_avg_aspect <= 0.67:
                aspect_suggestion = '2:3'
            elif overall_avg_aspect <= 0.8:
                aspect_suggestion = '3:4'
            else:
                aspect_suggestion = '4:5'
        elif overall_avg_aspect > 1.05:
            orientation = 'landscape'
            if overall_avg_aspect >= 2.33:
                aspect_suggestion = '21:9'
            elif overall_avg_aspect >= 1.6:
                aspect_suggestion = '16:9'
            elif overall_avg_aspect >= 1.4:
                aspect_suggestion = '3:2'
            elif overall_avg_aspect >= 1.2:
                aspect_suggestion = '4:3'
            else:
                aspect_suggestion = '5:4'
        else:
            orientation = 'square'
            aspect_suggestion = '1:1'

        return orientation, aspect_suggestion

    except Exception as e:
        print(f"⚠️  Lỗi detect orientation: {e}")
        return 'landscape', '16:9'


def validate_session(session_id: str) -> str:
    """Validate session_id và trả về path, raise HTTPException nếu lỗi."""
    if not session_id or '/' in session_id or '\\' in session_id or '..' in session_id:
        raise HTTPException(status_code=400, detail="session_id không hợp lệ")
    input_folder = os.path.join(UPLOAD_FOLDER, session_id)
    if not os.path.abspath(input_folder).startswith(os.path.abspath(UPLOAD_FOLDER)):
        raise HTTPException(status_code=400, detail="session_id không hợp lệ (path traversal)")
    return input_folder


def get_session_owner(session_id: str) -> Optional[int]:
    """Trả về user_id sở hữu session hoặc None nếu không có."""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM upload_sessions WHERE session_id = %s LIMIT 1", (session_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row.get("user_id") if row else None
    except Exception:
        return None


def ensure_session_owner(session_id: str, user: dict):
    """Đảm bảo session thuộc user hiện tại."""
    owner_id = get_session_owner(session_id)
    if owner_id is None or owner_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập session này")


def create_media_access_token(session_id: str, user_id: int) -> str:
    payload = {
        "sid": session_id,
        "uid": user_id,
        "type": "media_access",
        "exp": datetime.utcnow().timestamp() + MEDIA_TOKEN_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_media_access_token(session_id: str, token: str):
    if not token:
        raise HTTPException(status_code=401, detail="Thiếu token truy cập media")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token media không hợp lệ hoặc hết hạn")

    if payload.get("type") != "media_access" or payload.get("sid") != session_id:
        raise HTTPException(status_code=403, detail="Token media không hợp lệ")


def resolve_safe_file(base_folder: str, filename: str) -> str:
    """Resolve file path an toàn để tránh path traversal."""
    if not filename or '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    base_path = Path(base_folder).resolve()
    target_path = (base_path / filename).resolve()
    if base_path not in target_path.parents:
        raise HTTPException(status_code=400, detail="Đường dẫn file không hợp lệ")
    return str(target_path)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
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
    if DB_AVAILABLE:
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
async def generate_comic(data: GenerateRequest, user: dict = Depends(get_current_user)):
    """Tạo comic book từ ảnh đã upload. Cần session_id từ /upload trước."""
    if not COMIC_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Comic engine chưa được cài đặt")

    input_folder = validate_session(data.session_id)
    ensure_session_owner(data.session_id, user)
    if not os.path.exists(input_folder):
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn")

    image_files = list(Path(input_folder).glob('*'))
    if not image_files:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh trong session")

    output_folder = os.path.join(OUTPUT_FOLDER, data.session_id)

    # Xóa output cũ nếu có
    if os.path.exists(output_folder):
        try:
            shutil.rmtree(output_folder)
        except Exception as e:
            print(f"⚠️  Không xóa được output cũ: {e}")
            try:
                for f in Path(output_folder).glob('*'):
                    try:
                        f.unlink()
                    except Exception:
                        pass
            except Exception:
                pass

    os.makedirs(output_folder, exist_ok=True)

    try:
        if data.layout_mode == 'simple':
            print(f"🎨 Using SIMPLE layout mode")

            resolution_map = {"1K": 1000, "2K": 2000, "4K": 4000}
            aspect_ratio_map = {
                "1:1": (1, 1), "2:3": (2, 3), "3:2": (3, 2),
                "3:4": (3, 4), "4:3": (4, 3), "4:5": (4, 5),
                "5:4": (5, 4), "9:16": (9, 16), "16:9": (16, 9), "21:9": (21, 9)
            }

            aspect_ratio_key = data.aspect_ratio
            if aspect_ratio_key.lower() == 'auto':
                _, aspect_ratio_key = detect_image_orientation(input_folder)

            base_resolution = resolution_map.get(data.resolution, 2000)
            aspect_w, aspect_h = aspect_ratio_map.get(aspect_ratio_key, (16, 9))
            page_width = base_resolution

            if data.single_page_mode:
                page_height = base_resolution * 20
                img_files = [f for f in os.listdir(input_folder)
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                simple_panels_per_page = len(img_files)
            else:
                page_height = int(base_resolution * aspect_h / aspect_w)
                simple_panels_per_page = data.panels_per_page if data.panels_per_page else 8

            base_output = os.path.join(output_folder, 'page')
            process_comic_layout(
                input_folder=input_folder,
                output_filename=base_output + '.jpg',
                page_width=page_width,
                margin=data.margin,
                gap=data.gap,
                page_height=page_height,
                panels_per_page=simple_panels_per_page,
                use_smart_crop=data.use_smart_crop,
                adaptive_layout=data.adaptive_layout,
                analyze_shot_type=data.analyze_shot_type,
                classify_characters=data.classify_characters,
                reading_direction=data.reading_direction
            )

        else:
            print(f"🧠 Using ADVANCED layout mode")
            panels = data.panels_per_page
            if data.single_page_mode:
                img_files = [f for f in os.listdir(input_folder)
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                panels = len(img_files)

            create_comic_book_from_images(
                image_folder=input_folder,
                output_folder=output_folder,
                panels_per_page=panels,
                diagonal_prob=data.diagonal_prob,
                adaptive_layout=data.adaptive_layout,
                use_smart_crop=data.use_smart_crop,
                reading_direction=data.reading_direction,
                analyze_shot_type=data.analyze_shot_type,
                auto_page_size=data.auto_page_size,
                target_dpi=data.target_dpi,
                classify_characters=data.classify_characters
            )

    except MemoryError:
        raise HTTPException(status_code=500, detail="Không đủ bộ nhớ. Thử giảm số ảnh hoặc DPI")
    except Exception as gen_error:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo comic: {str(gen_error)}")

    # ── AI Analysis & Save to Database (if enabled) ──
    if DB_AVAILABLE and AI_ANALYSIS_AVAILABLE and (data.analyze_shot_type or data.classify_characters):
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

    # Đếm số trang đã tạo
    pages = (list(Path(output_folder).glob('page_*.png')) +
             list(Path(output_folder).glob('page_*.jpg')) +
             list(Path(output_folder).glob('page.png')) +
             list(Path(output_folder).glob('page.jpg')))

    if not pages:
        raise HTTPException(status_code=500, detail="Không tạo được trang nào. Kiểm tra lại ảnh đầu vào")

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


@router.get("/preview/{session_id}")
async def preview(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Lấy danh sách URL các trang comic đã tạo."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)

    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả")

    pages_png = sorted(Path(output_folder).glob('page_*.png'))
    pages_jpg = sorted(Path(output_folder).glob('page_*.jpg'))
    pages = list(pages_png) + list(pages_jpg)

    # Lấy base URL từ request
    base_url = str(request.base_url).rstrip('/')
    api_prefix = "/api/v1"
    timestamp = int(time.time() * 1000)
    media_token = create_media_access_token(session_id, user.get("id"))
    page_urls = [
        f"{base_url}{api_prefix}/comic/output/{session_id}/{p.name}?st={media_token}&t={timestamp}"
        for p in pages
    ]

    return {"success": True, "pages": page_urls, "timestamp": timestamp}


@router.get("/output/{session_id}/{filename}")
async def serve_output(session_id: str, filename: str, st: str = Query(...)):
    """Serve file ảnh output."""
    validate_session(session_id)
    verify_media_access_token(session_id, st)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    file_path = resolve_safe_file(output_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại")

    return FileResponse(
        path=file_path,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        }
    )


@router.get("/output/{session_id}/covers/{filename}")
async def serve_cover(session_id: str, filename: str, st: str = Query(...)):
    """Serve file bìa."""
    validate_session(session_id)
    verify_media_access_token(session_id, st)
    covers_folder = os.path.join(OUTPUT_FOLDER, session_id, 'covers')
    file_path = resolve_safe_file(covers_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File bìa không tồn tại")

    return FileResponse(path=file_path)


@router.get("/download/{session_id}")
async def download_zip(session_id: str, user: dict = Depends(get_current_user)):
    """Download toàn bộ comic dưới dạng ZIP."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)

    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả")

    # Log download activity
    if DB_AVAILABLE:
        try:
            pages_count = len(list(Path(output_folder).glob('page_*.*')))
            activity_logger.log(
                action='download_zip',
                user_id=None,
                session_id=session_id,
                resource_type='comic_output',
                details={'pages_count': pages_count, 'format': 'zip'}
            )
        except Exception as e:
            print(f"⚠️  Activity logging failed: {e}")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for page in Path(output_folder).glob('page_*.png'):
            zipf.write(page, page.name)
        for page in Path(output_folder).glob('page_*.jpg'):
            zipf.write(page, page.name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=comic_{session_id}.zip"}
    )


@router.get("/download_pdf/{session_id}")
async def download_pdf(session_id: str, user: dict = Depends(get_current_user)):
    """Xuất toàn bộ comic thành PDF (bìa trước → nội dung → bìa sau → lời cảm ơn)."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)

    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Log download activity
    if DB_AVAILABLE:
        try:
            activity_logger.log(
                action='download_pdf',
                user_id=None,
                session_id=session_id,
                resource_type='comic_output',
                details={'format': 'pdf', 'with_covers': True}
            )
        except Exception as e:
            print(f"⚠️  Activity logging failed: {e}")

    page_files = sorted(
        list(Path(output_folder).glob('page_*.png')) +
        list(Path(output_folder).glob('page_*.jpg')) +
        list(Path(output_folder).glob('page.png')) +
        list(Path(output_folder).glob('page.jpg')),
        key=lambda p: p.name
    )

    if not page_files:
        raise HTTPException(status_code=400, detail="Chưa tạo trang nội dung. Hãy bấm 'Tạo truyện' trước.")

    # Thu thập bìa
    covers_folder = os.path.join(output_folder, 'covers')
    cover_order = ['front', 'back', 'thank_you']
    cover_paths = {}
    if os.path.exists(covers_folder):
        for ctype in cover_order:
            for ext in ALLOWED_EXTENSIONS:
                p = os.path.join(covers_folder, f'{ctype}.{ext}')
                if os.path.exists(p):
                    cover_paths[ctype] = p
                    break

    # Xác định kích thước PDF từ trang đầu tiên
    with Image.open(page_files[0]) as ref_img:
        page_w, page_h = ref_img.size

    def fit_to_page(img_path, target_w, target_h, bg_color=(255, 255, 255)):
        """Scale ảnh vừa khít trong khung target_w x target_h, giữ aspect ratio."""
        img = Image.open(img_path).convert('RGB')
        orig_w, orig_h = img.size
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (target_w, target_h), bg_color)
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(img_resized, (paste_x, paste_y))
        return canvas

    images_for_pdf = []

    if 'front' in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths['front'], page_w, page_h))

    for p in page_files:
        images_for_pdf.append(Image.open(p).convert('RGB'))

    if 'back' in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths['back'], page_w, page_h))

    if 'thank_you' in cover_paths:
        images_for_pdf.append(fit_to_page(cover_paths['thank_you'], page_w, page_h))

    if not images_for_pdf:
        raise HTTPException(status_code=400, detail="Không có trang nào để xuất PDF")

    buf = io.BytesIO()
    first_img = images_for_pdf[0]
    rest = images_for_pdf[1:]
    first_img.save(
        buf,
        format='PDF',
        save_all=True,
        append_images=rest,
        resolution=150
    )
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comic_{session_id}.pdf"}
    )


@router.delete("/clear/{session_id}")
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
        "url": f"/api/v1/comic/output/{session_id}/covers/{save_name}?st={create_media_access_token(session_id, user.get('id'))}"
    }


@router.get("/covers/{session_id}")
async def get_covers(session_id: str, user: dict = Depends(get_current_user)):
    """Lấy danh sách bìa đã upload."""
    validate_session(session_id)
    ensure_session_owner(session_id, user)
    covers_folder = os.path.join(OUTPUT_FOLDER, session_id, 'covers')

    if not os.path.exists(covers_folder):
        return {"success": True, "covers": {}}

    covers = {}
    media_token = create_media_access_token(session_id, user.get("id"))
    for cover_type in COVER_TYPES:
        for ext in ALLOWED_EXTENSIONS:
            path = os.path.join(covers_folder, f'{cover_type}.{ext}')
            if os.path.exists(path):
                covers[cover_type] = f"/api/v1/comic/output/{session_id}/covers/{cover_type}.{ext}?st={media_token}"
                break

    return {"success": True, "covers": covers}


@router.get("/ai_capabilities")
async def ai_capabilities():
    """Kiểm tra các AI features và trạng thái của chúng."""
    return {
        "ai_analysis_available": AI_ANALYSIS_AVAILABLE,
        "comic_engine_available": COMIC_ENGINE_AVAILABLE,
        "features": {
            "character_classification": {
                "available": AI_ANALYSIS_AVAILABLE,
                "description": "Phân loại nhân vật (Primary/Secondary/Background)"
            },
            "face_recognition": {
                "available": FACE_RECOGNITION_AVAILABLE,
                "description": "Nhận diện tên nhân vật từ database",
                "requires_install": not FACE_RECOGNITION_AVAILABLE
            },
            "scene_classification": {
                "available": AI_ANALYSIS_AVAILABLE,
                "description": "Phân loại cảnh (close_up, action, dialogue, group, normal)",
                "methods": ["rule_based", "ai_model", "hybrid"]
            },
            "smart_crop": {
                "available": True,
                "description": "Crop thông minh giữ vùng quan trọng"
            }
        },
        "recommendations": [] if AI_ANALYSIS_AVAILABLE else [
            "Install: pip install ultralytics opencv-python Pillow"
        ]
    }


@router.get("/projects")
async def get_user_projects(user: dict = Depends(get_current_user)):
    """
    Lấy danh sách tất cả projects của user hiện tại.
    Filter theo user_id từ database.
    """
    projects = []
    user_id = user.get("id")
    
    try:
        # Query sessions của user từ database
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Lấy tất cả sessions của user này
        cursor.execute("""
            SELECT DISTINCT session_id 
            FROM upload_sessions 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        user_sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Nếu không có session nào trong database
        if not user_sessions:
            return {"projects": [], "total": 0, "user_id": user_id}
        
        # Lấy danh sách session_ids
        session_ids = [s["session_id"] for s in user_sessions]
        
    except Exception as e:
        print(f"⚠️ Database query error: {e}")
        # Fallback: return empty nếu DB lỗi
        return {"projects": [], "total": 0, "user_id": user_id}
    
    # Scan thư mục outputs/ nhưng chỉ lấy sessions của user
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return {"projects": [], "total": 0, "user_id": user_id}
    
    for session_id in session_ids:
        session_folder = outputs_dir / session_id
        
        # Skip nếu folder không tồn tại
        if not session_folder.exists() or not session_folder.is_dir():
            continue
        
        # Đếm số trang (các file page_*.jpg hoặc page_*.png)
        pages = list(session_folder.glob("page_*.*"))
        page_count = len([p for p in pages if p.suffix.lower() in ['.jpg', '.jpeg', '.png']])
        
        # Lấy thumbnail (page_001)
        thumbnail = None
        for ext in ['.jpg', '.jpeg', '.png']:
            thumb_path = session_folder / f"page_001{ext}"
            if thumb_path.exists():
                media_token = create_media_access_token(session_id, user_id)
                thumbnail = f"/api/v1/comic/output/{session_id}/page_001{ext}?st={media_token}"
                break
        
        # Lấy thông tin covers
        covers_dir = session_folder / "covers"
        has_covers = covers_dir.exists() and any(covers_dir.iterdir())
        
        # Lấy thời gian tạo
        created_at = datetime.fromtimestamp(session_folder.stat().st_ctime)
        modified_at = datetime.fromtimestamp(session_folder.stat().st_mtime)
        
        # Tính kích thước folder
        total_size = sum(f.stat().st_size for f in session_folder.rglob('*') if f.is_file())
        size_mb = round(total_size / (1024 * 1024), 2)
        
        projects.append({
            "session_id": session_id,
            "page_count": page_count,
            "thumbnail": thumbnail,
            "has_covers": has_covers,
            "created_at": created_at.isoformat(),
            "modified_at": modified_at.isoformat(),
            "size_mb": size_mb,
            "status": "completed" if page_count > 0 else "incomplete"
        })
    
    return {
        "projects": projects,
        "total": len(projects),
        "user_id": user_id,
        "username": user.get("username")
    }


@router.delete("/projects/{session_id}")
async def delete_project(session_id: str, user: dict = Depends(get_current_user)):
    """Xóa project theo session_id"""
    ensure_session_owner(session_id, user)
    session_folder = Path("outputs") / session_id
    
    if not session_folder.exists():
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    
    try:
        # Xóa thư mục và tất cả file bên trong
        shutil.rmtree(session_folder)
        
        # TODO: Xóa entries trong database nếu có
        
        return {
            "success": True,
            "message": f"Đã xóa project {session_id}",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa project: {str(e)}")


@router.get("/activity")
async def get_activity_history(user: dict = Depends(get_current_user), limit: int = 100):
    """Lấy lịch sử hoạt động của user (từ activity_logs table)"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Truy vấn activity_logs - dùng đúng tên cột theo schema:
        # - 'action' (không phải action_type)
        # - 'created_at' (không phải timestamp)
        # - 'session_id' (không phải target_id)
        # - 'resource_type' (không phải target_type)
        cursor.execute(
            """SELECT 
                id,
                action AS action_type,
                resource_type,
                session_id,
                details, 
                ip_address,
                user_agent,
                created_at AS timestamp
            FROM activity_logs 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s""",
            (user.get("id"), limit)
        )
        
        activities = cursor.fetchall()
        
        # Enrich activities với metadata
        enriched_activities = []
        for activity in activities:
            details_str = activity.get('details', '') or ''
            
            enriched = {
                "id": activity['id'],
                "action_type": activity['action_type'],  # đã alias từ 'action'
                "session_id": activity.get('session_id'),
                "details": details_str,
                "timestamp": activity['timestamp'].isoformat() if activity['timestamp'] else None,
                "ip_address": activity.get('ip_address'),
                "user_agent": activity.get('user_agent'),
                "image_count": 0,
                "layout_mode": None,
                "status": "success"
            }
            
            if details_str and 'image' in details_str.lower():
                import re
                match = re.search(r'(\d+)\s*(?:ảnh|image)', details_str.lower())
                if match:
                    enriched['image_count'] = int(match.group(1))
            
            if details_str:
                if 'simple' in details_str.lower():
                    enriched['layout_mode'] = 'simple'
                elif 'advanced' in details_str.lower():
                    enriched['layout_mode'] = 'advanced'
            
            enriched_activities.append(enriched)
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "activities": enriched_activities,
            "total": len(enriched_activities),
            "user_id": user.get("id")
        }
        
    except Exception as e:
        print(f"Activity log error: {str(e)}")
        return {
            "success": True,
            "activities": [],
            "total": 0,
            "message": "Activity logging not available yet"
        }


@router.get("/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """Dashboard với tổng hợp thống kê toàn bộ"""
    user_id = user.get("id")
    
    try:
        # Get projects stats from database
        projects = []
        total_projects = 0
        total_pages = 0
        total_size_mb = 0.0
        recent_projects = []

        try:
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)

            # Get user's sessions from upload_sessions table
            cursor.execute("""
                SELECT DISTINCT session_id 
                FROM upload_sessions 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            user_sessions_db = cursor.fetchall()
            session_ids = [s["session_id"] for s in user_sessions_db]

            # Scan outputs directory for these sessions
            outputs_dir = Path("outputs")
            if outputs_dir.exists():
                for session_id in session_ids:
                    session_dir = outputs_dir / session_id
                    if session_dir.is_dir():
                        page_files = (
                            list(session_dir.glob("page_*.jpg")) +
                            list(session_dir.glob("page_*.png")) +
                            list(session_dir.glob("page.jpg")) +
                            list(session_dir.glob("page.png"))
                        )
                        page_count = len(page_files)
                        
                        size_mb = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file()) / (1024 * 1024)
                        created_at = datetime.fromtimestamp(session_dir.stat().st_ctime)
                        
                        projects.append({
                            "session_id": session_dir.name,
                            "page_count": page_count,
                            "size_mb": size_mb,
                            "created_at": created_at.isoformat()
                        })
            
            total_projects = len(projects)
            total_pages = sum(p["page_count"] for p in projects)
            total_size_mb = sum(p["size_mb"] for p in projects)
            recent_projects = sorted(projects, key=lambda x: x['created_at'], reverse=True)[:5]

            # Recent activities - dùng đúng tên cột: 'action' và 'created_at'
            cursor.execute(
                """SELECT action AS action_type, details, created_at AS timestamp
                FROM activity_logs 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 5""",
                (user_id,)
            )
            recent_activities = cursor.fetchall()
            
            # Activity breakdown - GROUP BY 'action' (tên cột thực)
            cursor.execute(
                """SELECT action AS action_type, COUNT(*) as count 
                FROM activity_logs 
                WHERE user_id = %s 
                GROUP BY action""",
                (user_id,)
            )
            activity_breakdown_list = cursor.fetchall()
            activity_breakdown = {item['action_type']: item['count'] for item in activity_breakdown_list}
            
            # Total activities
            cursor.execute(
                "SELECT COUNT(*) as total FROM activity_logs WHERE user_id = %s",
                (user_id,)
            )
            total_activities = cursor.fetchone()['total']
            
            # User info
            cursor.execute(
                "SELECT username, email, created_at, last_login FROM users WHERE id = %s",
                (user_id,)
            )
            user_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "total_projects": total_projects,
                "total_pages": total_pages,
                "total_size_mb": round(total_size_mb, 2),
                "total_activities": total_activities,
                "recent_projects": sorted(projects, key=lambda x: x['created_at'], reverse=True)[:5],
                "recent_activities": [
                    {
                        "action_type": a['action_type'],
                        "details": a['details'],
                        "timestamp": a['timestamp'].isoformat() if a['timestamp'] else None
                    }
                    for a in recent_activities
                ],
                "activity_breakdown": activity_breakdown,
                "user_name": user_info['username'] if user_info else user.get('username'),
                "user_email": user_info['email'] if user_info else user.get('email'),
                "user_created_at": user_info['created_at'].isoformat() if user_info and user_info['created_at'] else None,
                "user_last_login": user_info['last_login'].isoformat() if user_info and user_info['last_login'] else None
            }
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            # Return basic stats if database fails
            return {
                "success": True,
                "total_projects": total_projects,
                "total_pages": total_pages,
                "total_size_mb": total_size_mb,
                "total_activities": 0,
                "recent_projects": sorted(projects, key=lambda x: x['created_at'], reverse=True)[:5],
                "recent_activities": [],
                "activity_breakdown": {},
                "user_name": user.get('username'),
                "user_email": user.get('email'),
                "user_created_at": None,
                "user_last_login": None
            }
        
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return minimal stats on any error
        return {
            "success": True,
            "total_projects": 0,
            "total_pages": 0,
            "total_size_mb": 0,
            "total_activities": 0,
            "recent_projects": [],
            "recent_activities": [],
            "activity_breakdown": {},
            "user_name": user.get('username', 'Unknown'),
            "user_email": user.get('email', 'Unknown'),
            "message": f"Dashboard limited - {str(e)}"
        }
