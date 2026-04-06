"""
Validation và Error Handling utilities cho Comic Book Generator
"""
import os
from functools import wraps
from flask import jsonify


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def validate_session_id(session_id, base_folder):
    """
    Validate session ID an toàn
    
    Raises:
        ValidationError: Nếu session ID không hợp lệ
    """
    if not session_id:
        raise ValidationError("Session ID không được để trống")
    
    if not isinstance(session_id, str):
        raise ValidationError("Session ID phải là chuỗi")
    
    if not session_id.isdigit():
        raise ValidationError("Session ID chỉ được chứa số")
    
    # Security: Prevent path traversal
    session_path = os.path.abspath(os.path.join(base_folder, session_id))
    base_path = os.path.abspath(base_folder)
    
    if not session_path.startswith(base_path):
        raise ValidationError("Session ID không hợp lệ", 403)
    
    return session_id


def validate_generate_params(data):
    """
    Validate parameters cho generate endpoint
    
    Returns:
        dict: Validated và sanitized parameters
    """
    if not data:
        raise ValidationError("Request body trống")
    
    # Validate session_id
    session_id = data.get('session_id')
    if not session_id:
        raise ValidationError("Thiếu session_id")
    
    # Validate và convert parameters
    try:
        params = {
            'session_id': str(session_id),
            'panels_per_page': int(data.get('panels_per_page', 5)),
            'diagonal_prob': float(data.get('diagonal_prob', 0.3)),
            'target_dpi': int(data.get('target_dpi', 150)),
            'adaptive_layout': bool(data.get('adaptive_layout', True)),
            'use_smart_crop': bool(data.get('use_smart_crop', False)),
            'analyze_shot_type': bool(data.get('analyze_shot_type', False)),
            'classify_characters': bool(data.get('classify_characters', False)),
            'enable_perspective_warp': bool(data.get('enable_perspective_warp', False)),
            'auto_page_size': bool(data.get('auto_page_size', True)),
            'aspect_ratio': str(data.get('aspect_ratio', '9:16')),
            'reading_direction': str(data.get('reading_direction', 'ltr'))
        }
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Lỗi chuyển đổi tham số: {str(e)}")
    
    # Range validation
    if not (2 <= params['panels_per_page'] <= 10):
        raise ValidationError("panels_per_page phải từ 2-10")
    
    if not (0 <= params['diagonal_prob'] <= 1):
        raise ValidationError("diagonal_prob phải từ 0-1")
    
    if params['target_dpi'] not in [75, 150, 300, 600]:
        raise ValidationError("target_dpi phải là 75, 150, 300 hoặc 600")
    
    if params['reading_direction'] not in ['ltr', 'rtl']:
        raise ValidationError("reading_direction phải là 'ltr' hoặc 'rtl'")

    allowed_aspect_ratios = {'auto', '1:1', '2:3', '3:4', '4:5', '9:16'}
    if params['aspect_ratio'] not in allowed_aspect_ratios:
        raise ValidationError("aspect_ratio không hợp lệ")
    
    return params


def validate_file(file, max_size_mb=50):
    """
    Validate uploaded file
    
    Args:
        file: FileStorage object
        max_size_mb: Max file size in MB
    
    Returns:
        tuple: (is_valid, error_message)
    """
    from PIL import Image
    
    if not file or not file.filename:
        return False, "File không hợp lệ"
    
    # Check extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return False, f"Định dạng không hỗ trợ: .{ext}. Chấp nhận: {', '.join(allowed_extensions)}"
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File quá lớn ({file_size/1024/1024:.1f}MB). Tối đa {max_size_mb}MB"
    
    if file_size == 0:
        return False, "File rỗng"
    
    # Verify it's actually an image
    try:
        file.seek(0)
        img = Image.open(file)
        img.verify()
        file.seek(0)
        
        # Check image dimensions
        if img.width < 10 or img.height < 10:
            return False, "Ảnh quá nhỏ (tối thiểu 10x10px)"
        
        if img.width > 10000 or img.height > 10000:
            return False, "Ảnh quá lớn (tối đa 10000x10000px)"
        
    except Exception as e:
        return False, f"File không phải ảnh hợp lệ: {str(e)}"
    
    return True, None


def handle_errors(f):
    """Decorator để handle errors chung"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return jsonify({'success': False, 'error': e.message}), e.status_code
        except FileNotFoundError as e:
            return jsonify({'success': False, 'error': 'File hoặc thư mục không tồn tại'}), 404
        except PermissionError:
            return jsonify({'success': False, 'error': 'Không có quyền truy cập'}), 403
        except MemoryError:
            return jsonify({'success': False, 'error': 'Không đủ bộ nhớ. Thử giảm số ảnh hoặc DPI'}), 500
        except Exception as e:
            print(f"Unexpected error in {f.__name__}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Lỗi server: {str(e)}'}), 500
    
    return decorated_function
