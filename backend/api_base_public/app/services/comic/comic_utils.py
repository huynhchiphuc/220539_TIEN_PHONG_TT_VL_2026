import os
import math
import random
import numpy as np
from PIL import Image, ImageOps, ImageFilter

# Guardrails
PANEL_MIN_ASPECT = 0.55
PANEL_MAX_ASPECT = 2.20

def calculate_adaptive_diagonal_angle(content_type='normal', panel_weight=1.0, max_angle=12):
    if panel_weight > 1.5:
        min_angle, max_base = 10, 15
    elif panel_weight >= 1.2:
        min_angle, max_base = 8, 12
    elif panel_weight >= 0.8:
        min_angle, max_base = 5, 8
    else:
        min_angle, max_base = 2, 5
    max_base = min(max_base, max_angle)
    base_angle = random.uniform(min_angle, max_base)
    type_bias = 0
    if content_type == 'action':
        type_bias = 2
    elif content_type == 'dialogue':
        type_bias = -2
    elif content_type == 'close_up':
        type_bias = -1
    final_angle = base_angle + type_bias
    final_angle = max(1, min(final_angle, 20))
    return final_angle

# Giới hạn kích thước output
MAX_OUTPUT_LONG_SIDE = int(os.getenv("COMIC_MAX_LONG_SIDE", "1920"))

try:
    from app.services.ai.smart_crop import (
        smart_crop_to_panel,
        get_important_region,
        analyze_shot_type,
        analyze_image_context,
    )
    SMART_CROP_AVAILABLE = True
except ImportError:
    SMART_CROP_AVAILABLE = False
def analyze_image_aspect_ratios(image_files):
    """
    Phân tích aspect ratio của tất cả ảnh
    
    Returns:
        List[dict]: [{'path': path, 'aspect': ratio, 'orientation': 'landscape'/'portrait'/'square'}]
    """
    image_info = []
    
    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                aspect = img.width / img.height
                
                # Xác định orientation
                if aspect > 1.2:
                    orientation = 'landscape'  # Nằm ngang
                elif aspect < 0.8:
                    orientation = 'portrait'   # Đứng dọc
                else:
                    orientation = 'square'     # Gần vuông
                
                image_info.append({
                    'path': img_path,
                    'aspect': aspect,
                    'orientation': orientation,
                    'type': _classify_ar(aspect),
                    'width': img.width,
                    'height': img.height
                })
        except Exception as e:
            print(f"⚠️  Không đọc được {img_path}: {e}")
    
    return image_info

def analyze_images_with_context(image_files, analyze_shot_type_enabled=False):
    """
    Phân tích ảnh với thông tin bối cảnh (shot type)
    
    Args:
        image_files: Danh sách đường dẫn ảnh
        analyze_shot_type_enabled: Có phân tích shot type không
    
    Returns:
        List[dict]: Thông tin chi tiết về từng ảnh
    """
    image_info = []
    
    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                aspect = img.width / img.height
                
                # Xác định orientation
                if aspect > 1.2:
                    orientation = 'landscape'
                elif aspect < 0.8:
                    orientation = 'portrait'
                else:
                    orientation = 'square'
                
                info = {
                    'path': img_path,
                    'aspect': aspect,
                    'orientation': orientation,
                    'type': _classify_ar(aspect),
                    'width': img.width,
                    'height': img.height,
                    'shot_type': 'medium',
                    'panel_weight': 1.0,
                    'shot_description': 'Not analyzed'
                }
                
                # Phân tích AI nếu được bật (nhân vật + chữ + bong bóng)
                if analyze_shot_type_enabled and SMART_CROP_AVAILABLE:
                    try:
                        # Phân tích toàn diện: shot type + text/bubbles
                        context_info = analyze_image_context(img_path, use_yolo=False)
                        shot_info = context_info['shot_type_info']
                        
                        info['shot_type'] = shot_info['shot_type']
                        info['panel_weight'] = shot_info['panel_weight']
                        info['shot_description'] = shot_info['description']
                        
                        # Trích xuất dữ liệu chữ / bong bóng thoại
                        t_count = context_info.get('text_count', 0)
                        b_count = context_info.get('bubble_count', 0)
                        
                        # --- CƠ CHẾ NỚI RỘNG KHUNG CHO ẢNH CÓ CHỮ TRONG CÙNG 1 DÒNG ---
                        # Nếu ảnh nằm cùng dòng 2 khung, thuật toán layout sẽ chia tỉ lệ width theo 'aspect'
                        # Bằng cách "bơm" aspect to ra, nó sẽ nới rộng ảnh này ra chiếm phần lớn >50% !
                        if t_count > 0 or b_count > 0:
                            # Boost aspect lên 10%-40% tùy thuộc mật độ chữ
                            boost_factor = 1.0 + min(0.4, (t_count * 0.1) + (b_count * 0.15))
                            
                            # Cập nhật AR mới để giành giật chiều rộng trong layout
                            info['aspect'] = info['aspect'] * boost_factor
                            print(f"📝 {os.path.basename(img_path)} có {t_count} Box chữ, {b_count} Bong bóng -> Nới rộng ô x{boost_factor:.2f}")
                            
                    except Exception as e:
                        print(f"⚠️  Lỗi khi phân tích AI {img_path}: {e}")
                
                image_info.append(info)
        except Exception as e:
            print(f"⚠️  Không đọc được {img_path}: {e}")
    
    return image_info

def calculate_optimal_page_size(image_info_list, target_dpi=150, max_width=2480, max_height=3508):
    """
    Tính toán kích thước trang tối ưu dựa trên kích thước ảnh đầu vào
    
    Args:
        image_info_list: Danh sách thông tin ảnh
        target_dpi: DPI mục tiêu (150 cho web, 300 cho print)
        max_width: Chiều rộng tối đa (pixels) - mặc định A4 width @ 300dpi
        max_height: Chiều cao tối đa (pixels) - mặc định A4 height @ 300dpi
    
    Returns:
        dict: {'width': px, 'height': px, 'aspect': ratio, 'scale_factor': factor}
    """
    if not image_info_list:
        # Mặc định A4 portrait @ 150dpi
        return {
            'width': 1240,  # 8.3" @ 150dpi
            'height': 1754,  # 11.7" @ 150dpi
            'aspect': 1240/1754,
            'scale_factor': 1.0,
            'description': 'Default A4'
        }
    
    # Tính trung bình kích thước ảnh
    avg_width = sum(img['width'] for img in image_info_list) / len(image_info_list)
    avg_height = sum(img['height'] for img in image_info_list) / len(image_info_list)

    aspects = []
    for img in image_info_list:
        w = max(1, int(img.get('width', 1)))
        h = max(1, int(img.get('height', 1)))
        aspects.append(w / float(h))
    aspects.sort()
    median_aspect = aspects[len(aspects) // 2]
    
    # Xác định orientation phổ biến nhất
    landscape_count = sum(1 for img in image_info_list if img['orientation'] == 'landscape')
    portrait_count = sum(1 for img in image_info_list if img['orientation'] == 'portrait')
    
    # Chọn tỉ lệ trang bám theo ảnh đầu vào thay vì ép cứng một tỉ lệ cố định.
    # landscape majority -> ưu tiên trang ngang, còn lại ưu tiên trang dọc.
    landscape_majority = landscape_count > portrait_count * 1.2
    if landscape_majority:
        page_aspect = min(1.6, max(1.1, median_aspect))
    else:
        portrait_aspect = median_aspect if median_aspect < 1.0 else (1.0 / median_aspect)
        page_aspect = min(0.9, max(0.55, portrait_aspect))

    if page_aspect >= 1.0:
        page_width = MAX_OUTPUT_LONG_SIDE
        page_height = max(1, int(round(page_width / page_aspect)))
    else:
        page_height = MAX_OUTPUT_LONG_SIDE
        page_width = max(1, int(round(page_height * page_aspect)))

    # Normalize coordinate system: Width luôn = 100
    coord_width = 100
    coord_height = int(coord_width / page_aspect)  # Điều chỉnh height theo aspect
    
    # Scale factor để convert từ pixels → coordinate
    scale_factor = coord_width / page_width
    
    return {
        'width': page_width,
        'height': page_height,
        'aspect': page_aspect,
        'scale_factor': scale_factor,
        'coord_width': coord_width,
        'coord_height': coord_height,
        'avg_image_size': f"{int(avg_width)}x{int(avg_height)}",
        'description': f"Adaptive page ratio from input images (median aspect={median_aspect:.2f})"
    }

def normalize_page_size_for_web(page_size: dict, max_long_side: int = MAX_OUTPUT_LONG_SIDE) -> dict:
    """Giới hạn kích thước output và đồng bộ coordinate system để tránh ảnh quá lớn."""
    width = max(1, int(page_size.get('width', 1240)))
    height = max(1, int(page_size.get('height', 1754)))

    long_side = max(width, height)
    if long_side > max_long_side:
        scale = max_long_side / float(long_side)
        width = max(1, int(round(width * scale)))
        height = max(1, int(round(height * scale)))

    coord_width = 100
    coord_height = max(1, int(round(coord_width * (height / float(width)))))

    normalized = dict(page_size)
    normalized['width'] = width
    normalized['height'] = height
    normalized['aspect'] = width / float(height)
    normalized['coord_width'] = coord_width
    normalized['coord_height'] = coord_height
    normalized['scale_factor'] = coord_width / float(width)

    desc = str(normalized.get('description', 'Optimized for web'))
    if 'web-capped' not in desc:
        normalized['description'] = f"{desc} (web-capped long side={max_long_side}px)"
    return normalized

def force_page_aspect_ratio(page_size: dict, aspect_w: int, aspect_h: int, max_long_side: int = MAX_OUTPUT_LONG_SIDE) -> dict:
    """Ép kích thước trang theo tỉ lệ cố định, giữ cạnh dài bằng max_long_side."""
    if aspect_w <= 0 or aspect_h <= 0:
        return normalize_page_size_for_web(page_size, max_long_side=max_long_side)

    ratio = aspect_w / float(aspect_h)
    # Ưu tiên portrait cho comic: cạnh dài nằm ở height.
    target_height = max_long_side
    target_width = max(1, int(round(target_height * ratio)))

    normalized = dict(page_size)
    normalized['width'] = target_width
    normalized['height'] = target_height

    normalized = normalize_page_size_for_web(normalized, max_long_side=max_long_side)
    normalized['description'] = f"{normalized.get('description', 'Optimized')} (forced {aspect_w}:{aspect_h})"
    return normalized

def _classify_ar(aspect: float) -> str:
    """
    Phân loại ảnh theo Aspect Ratio (12 categories).
    Đồng bộ với classify_aspect_ratio() trong comic_layout_simple.py.
    """
    if aspect > 2.8:
        return 'ultra_panoramic'  # Rất ngang, tỉ lệ > 2.8
    elif aspect > 2.2:
        return 'panoramic'        # Ngang giống Panorama (2.2 - 2.8)
    elif aspect > 1.8:
        return 'cinema_landscape' # Ngang chuẩn điện ảnh (1.8 - 2.2)
    elif aspect > 1.5:
        return 'wide_landscape'   # Ngang rộng (1.5 - 1.8)
    elif aspect > 1.25:
        return 'landscape'        # Ngang chuẩn (1.25 - 1.5)
    elif aspect > 1.05:
        return 'wide_square'      # Hơi ngang, gần vuông (1.05 - 1.25)
    elif aspect >= 0.95:
        return 'square'           # Vuông cân xứng (0.95 - 1.05)
    elif aspect >= 0.8:
        return 'tall_square'      # Hơi dọc, gần vuông (0.8 - 0.95)
    elif aspect >= 0.6:
        return 'portrait'         # Dọc vừa chuẩn (0.6 - 0.8)
    elif aspect >= 0.45:
        return 'tall_portrait'    # Dọc cao (0.45 - 0.6)
    elif aspect >= 0.3:
        return 'thin_portrait'    # Dọc mảnh (0.3 - 0.45)
    else:
        return 'ultrathin_portrait' # Rất gầy (< 0.3)

def _build_ar_strategy(image_aspects: list) -> list:
    """
    Giai đoạn 2: Xây dựng chiến lược cắt dựa trên Aspect Ratio chính xác.

    Nguyên tắc mới: Số ảnh/hàng phải đảm bảo panel sinh ra có AR gần với ảnh gốc.
    
    AR > 1.5  : Wide/Panoramic → 1 ảnh/hàng (toàn chiều rộng)
    1.1 < AR <= 1.5: Landscape vừa → 2 ảnh/hàng
    0.85 <= AR <= 1.1: Square → 2 ảnh/hàng
    0.5 <= AR < 0.85: Portrait vừa → TỐI ĐA 2 ảnh/hàng (giảm từ 3)
    AR < 0.5  : Thin/ultra portrait → 1 ảnh/hàng (quá hẹp nếu chia đôi)
    """
    tagged = []
    for idx, img in enumerate(image_aspects):
        entry = dict(img)
        entry['_orig_idx'] = idx
        tagged.append(entry)

    def _max_cols(ar: float) -> int:
        """Trả về số ảnh tối đa trong một hàng theo AR của ảnh đầu hàng."""
        if ar >= 1.8:    return 1   # cinema_landscape+ -> 1 ảnh 1 hàng (toàn chiều rộng)
        if ar >= 1.25:   return 2   # landscape -> 2 ảnh 1 dòng (theo yêu cầu)
        if ar >= 0.8:    return 2   # square -> max 2 ảnh 1 dòng
        if ar >= 0.45:   return 2   # portrait -> max 2 ảnh 1 dòng
        return 2                    # thin_portrait -> 2 ảnh

    def _get_core_category(ar: float) -> str:
        if ar >= 1.25: return 'landscape'
        if ar >= 0.8:  return 'square'
        return 'portrait'

    def _can_share_row(current_ars: list, next_ar: float) -> bool:
        """
        Cho phép ghép tự do Ngang + Dọc, Dọc + Vuông v.v (Học theo SIMPLE).
        Chỉ cấm ghép ảnh quá dị dạng (Cinema, Ultra thin).
        """
        all_ars = current_ars + [next_ar]
        if any(a > 1.8 or a < 0.3 for a in all_ars):
            return False
        return True

    rows = []
    queue = list(tagged)

    while queue:
        img = queue.pop(0)
        ar = img.get('aspect', 1.0)
        max_in_row = _max_cols(ar)
        group = [img]
        group_ars = [ar]
        core_cat = _get_core_category(ar)

        # Cố gắng thêm nhiều ảnh vào cùng hàng cho đến max_in_row
        while queue and len(group) < max_in_row:
            next_img = queue[0]
            next_ar = next_img.get('aspect', 1.0)
            
            if not _can_share_row(group_ars, next_ar):
                break
                
            # Nếu ghép hai thể loại ảnh khác nhau (Ngang + Dọc, v.v), giới hạn hàng đó chỉ tối đa 2 khung!
            next_cat = _get_core_category(next_ar)
            if next_cat != core_cat:
                max_in_row = min(max_in_row, 2)
            
            if len(group) < max_in_row:
                group.append(queue.pop(0))
                group_ars.append(next_ar)
            else:
                break

        rows.append(group)

    return rows


def fit_image_to_panel(image_path, panel_bounds, use_smart_crop=False):
    """
    Resize và crop ảnh để fit vào panel
    
    Args:
        image_path: Đường dẫn đến ảnh
        panel_bounds: (x, y, width, height) của panel
        use_smart_crop: True = dùng smart crop (phát hiện text/người), False = crop center
    
    Returns:
        numpy array của ảnh đã được xử lý
    """
    try:
        x, y, panel_w, panel_h = panel_bounds
        display_size = (max(280, int(panel_w * 34)), max(280, int(panel_h * 34)))
        
        # Bỏ qua panel quá nhỏ
        if panel_w < 5 or panel_h < 5:
            return None
        
        # Dùng smart crop nếu có
        if use_smart_crop and SMART_CROP_AVAILABLE:
            try:
                # Quan trọng: panel_bounds ở đây là hệ tọa độ layout (nhỏ),
                # nếu truyền thẳng sẽ khiến smart_crop resize ảnh quá bé rồi bị phóng to lại -> mờ.
                # Dùng kích thước render thực tế để smart crop trả ảnh đủ độ phân giải.
                smart_bounds = (0, 0, display_size[0], display_size[1])
                img = smart_crop_to_panel(image_path, smart_bounds, method='smart').convert('RGB')
                img = ImageOps.exif_transpose(img)

                # Đồng bộ đúng kích thước panel hiển thị.
                if img.size != display_size:
                    img = img.resize(display_size, Image.Resampling.LANCZOS)

                # Tăng nhẹ độ nét cho line-art/chữ khi smart crop.
                img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=1))
            except Exception as e:
                print(f"⚠️  Smart crop thất bại, dùng crop thường: {e}")
                use_smart_crop = False
        
        # Fallback: giữ nguyên toàn bộ ảnh theo tỉ lệ (KHÔNG crop),
        # tránh mất chữ nằm sát mép ảnh.
        if not use_smart_crop or not SMART_CROP_AVAILABLE:
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img).convert('RGB')

            target_w, target_h = display_size
            scale = min(target_w / max(1, img.width), target_h / max(1, img.height))
            new_w = max(1, int(round(img.width * scale)))
            new_h = max(1, int(round(img.height * scale)))

            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Dùng nền blur từ chính ảnh để lấp phần dư, nhìn hoàn chỉnh hơn letterbox trắng/đen.
            bg = img.resize(display_size, Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=14))
            canvas = bg.copy()

            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) // 2
            canvas.paste(resized, (paste_x, paste_y))

            img = canvas.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=2))
        else:
            # Smart crop mode: resize về display_size
            # Nhánh smart crop đã trả ảnh theo display_size ở trên.
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=110, threshold=2))
        
        return np.array(img)
    except Exception as e:
        print(f"⚠️  Lỗi khi đọc ảnh {image_path}: {e}")
        return None

