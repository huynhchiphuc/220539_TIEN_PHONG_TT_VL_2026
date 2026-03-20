import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Flask threading
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import itertools
import random
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import os
from pathlib import Path as PathLib

# Import smart crop module (nếu có)
try:
    from app.services.ai.smart_crop import (
        smart_crop_to_panel,
        get_important_region,
        analyze_shot_type,
        analyze_image_context,
    )
    SMART_CROP_AVAILABLE = True
except ImportError:
    try:
        from smart_crop import smart_crop_to_panel, get_important_region, analyze_shot_type, analyze_image_context
        SMART_CROP_AVAILABLE = True
    except ImportError:
        SMART_CROP_AVAILABLE = False
        print("⚠️  Smart crop không khả dụng. Dùng crop thông thường.")


# Guardrails để loại bỏ panel tỉ lệ quá xấu (quá ngang hoặc quá cao-hẹp).
PANEL_MIN_ASPECT = 0.55
PANEL_MAX_ASPECT = 2.20

# Mặc định tắt warp phối cảnh để giữ orientation ổn định.
DEFAULT_ENABLE_PERSPECTIVE_WARP = False


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
                    'width': img.width,
                    'height': img.height,
                    'shot_type': 'medium',
                    'panel_weight': 1.0,
                    'shot_description': 'Not analyzed'
                }
                
                # Phân tích shot type nếu được bật
                if analyze_shot_type_enabled and SMART_CROP_AVAILABLE:
                    try:
                        shot_info = analyze_shot_type(img_path)  # dùng YOLO nếu có, tự fallback
                        info['shot_type'] = shot_info['shot_type']
                        info['panel_weight'] = shot_info['panel_weight']
                        info['shot_description'] = shot_info['description']
                    except Exception as e:
                        pass  # Giữ giá trị mặc định
                
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
    avg_aspect = avg_width / avg_height
    
    # Xác định orientation phổ biến nhất
    landscape_count = sum(1 for img in image_info_list if img['orientation'] == 'landscape')
    portrait_count = sum(1 for img in image_info_list if img['orientation'] == 'portrait')
    
    # [FIX] Mặc định dùng A4 dọc cho truyện tranh, tránh méo
    page_width = 1240
    page_height = 1754
    page_aspect = page_width / page_height

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
        'description': f"Optimized for {'landscape' if landscape_count > portrait_count else 'portrait'} images"
    }


def create_dynamic_grid_layout(image_aspects, width=100, height=160, jitter_factor=8.0, margin=2.5):
    """
    🆕 TẠO LAYOUT DỰA TRÊN GRID - KHÔNG TẠO HÌNH TAM GIÁC
    Chia trang thành các hàng, mỗi hàng có số cột tương ứng.
    Mỗi panel luôn là tứ giác (quadrilateral).
    """
    num_panels = len(image_aspects)
    if num_panels == 0:
        return []

    # Bước 1: Cấu hình hàng
    # Tránh tạo các panel dọc quá hẹp (đặc biệt khi còn 2-3 ảnh cuối).
    portrait_count = sum(1 for img in image_aspects if img.get('orientation') == 'portrait')
    portrait_ratio = portrait_count / max(1, num_panels)
    prefer_vertical_rows = (height > width * 1.2) or (portrait_ratio >= 0.5)

    def _build_rows_config(total_panels, vertical_bias=False):
        if total_panels <= 0:
            return []
        if total_panels == 1:
            return [1]

        if vertical_bias:
            # Với trang dọc/ảnh thiên dọc, 2-3 panels xếp theo từng hàng
            # để tránh cột dọc quá hẹp theo chiều ngang.
            if total_panels <= 3:
                return [1] * total_panels

            # Ưu tiên max 2 cột/row để panel không bị hẹp theo chiều ngang.
            rows = [2] * (total_panels // 2)
            if total_panels % 2 == 1:
                rows.append(1)

            # Chuyển [2, 2, 1] -> [2, 1, 2] để cân bằng thị giác.
            if len(rows) >= 3 and rows[-1] == 1 and rows[-2] == 2 and rows[-3] == 2:
                rows[-2], rows[-1] = rows[-1], rows[-2]
            return rows

        # Landscape-biased giữ layout cũ để tương thích.
        if total_panels <= 3:
            return [total_panels]
        if total_panels == 4:
            return [2, 2]
        if total_panels == 5:
            return [2, 1, 2]
        if total_panels == 6:
            return [2, 2, 2]

        rows = [3] * (total_panels // 3)
        remainder = total_panels % 3
        if remainder:
            rows.append(remainder)
        return rows

    rows_config = _build_rows_config(num_panels, vertical_bias=prefer_vertical_rows)

    num_rows = len(rows_config)
    
    # Bước 2: Tạo boundary lines cho Y
    y_lines = [margin]
    for i in range(1, num_rows):
        y_lines.append(margin + (i / num_rows) * (height - 2 * margin) + random.uniform(-jitter_factor * 0.3, jitter_factor * 0.3))
    y_lines.append(height - margin)

    # Bước 3: Tạo boundary x_points cho từng LINE (có num_rows + 1 boundary lines)
    # Để tránh triangle, mỗi boundary line i phải có đủ điểm cho cả hàng trên (rows_config[i-1]) 
    # và hàng dưới (rows_config[i]).
    all_boundaries_x = []
    for i in range(num_rows + 1):
        # Xác định số lượng cột cần 'split' tại đường kẻ này
        n1 = rows_config[i-1] if i > 0 else 0
        n2 = rows_config[i] if i < num_rows else 0
        max_cols = max(n1, n2)
        
        # Nếu max_cols = 1, chỉ có margin và width-margin
        # Nếu max_cols > 1, tạo các điểm chia jittered
        x_points = [margin]
        if max_cols > 1:
            for j in range(1, max_cols):
                base_x = margin + (j / max_cols) * (width - 2 * margin)
                x_points.append(np.clip(base_x + random.uniform(-jitter_factor, jitter_factor), margin + 4, width - margin - 4))
        x_points.append(width - margin)
        all_boundaries_x.append(x_points)

    all_panels = []
    # Bước 4: Xây dựng Panels từ vertices
    for i in range(num_rows):
        num_cols_in_row = rows_config[i]
        top_y = y_lines[i]
        bot_y = y_lines[i+1]
        
        # Points available on top and bottom boundary lines of this row
        x_pts_top = all_boundaries_x[i]
        x_pts_bot = all_boundaries_x[i+1]
        
        for j in range(num_cols_in_row):
            # Map index j to the available split points on top/bottom
            # Nếu boundary có nhiều điểm hơn num_cols_in_row, ta gộp lại để tạo quad lớn
            # Example: 1 panel in row but boundary has 2 segments -> map point 0 to 2.
            
            # Tính range index points cho panel j
            # Với num_cols_in_row, panel j dùng index point [j*len/num] -> [(j+1)*len/num]
            t_idx_start = int(j * (len(x_pts_top) - 1) / num_cols_in_row)
            t_idx_end = int((j + 1) * (len(x_pts_top) - 1) / num_cols_in_row)
            
            b_idx_start = int(j * (len(x_pts_bot) - 1) / num_cols_in_row)
            b_idx_end = int((j + 1) * (len(x_pts_bot) - 1) / num_cols_in_row)
            
            # Vertices: LT, RT, RB, LB
            # Panels có thể là đa giác nhiều hơn 4 cạnh nếutop/bot có nhiều segments
            vertices = []
            
            # Cạnh trên
            for k in range(t_idx_start, t_idx_end + 1):
                vertices.append([x_pts_top[k], top_y])
            
            # Cạnh dưới (ngược chiều kim đồng hồ)
            for k in range(b_idx_end, b_idx_start - 1, -1):
                vertices.append([x_pts_bot[k], bot_y])
                
            all_panels.append(Polygon(np.array(vertices)))

    return all_panels

    return all_panels


def create_adaptive_layout(image_aspects, width=100, height=140, diagonal_probability=0.3, max_diagonal_angle=12, force_aspect_matched=False):
    """
    Tạo layout THÍCH ỨNG dựa trên aspect ratio và shot type của các ảnh (UPGRADED V2)
    
    🆕 V2: Khi diagonal_probability > 0.5 → Dùng ASPECT-MATCHED layout:
        - Tạo panel theo ĐÚNG tỷ lệ ảnh (không cắt chéo từ đầu đến cuối)
        - Nghiêng nhẹ 2-3 độ (rotate vertices)
    
    Args:
        image_aspects: List các dict chứa 'aspect', 'orientation', 'panel_weight' của ảnh
        width, height: Kích thước trang
        diagonal_probability: > 0.5 = aspect-matched mode, <= 0.5 = split polygon mode
        max_diagonal_angle: Góc nghiêng (degrees) cho aspect-matched mode, default=12
        force_aspect_matched: True = luôn tạo panel theo đúng tỉ lệ ảnh gốc
    
    Returns:
        List[Polygon]: Danh sách panels phù hợp với ảnh
    """
    num_panels = len(image_aspects)
    if num_panels == 0:
        return []

    # Ưu tiên dùng thuật toán recursive subdivision mới để đồng bộ chất lượng layout
    # giữa Auto Frame và luồng tạo comic từ ảnh upload.
    try:
        recursive_panels = create_recursive_subdivision_layout(
            num_panels=num_panels,
            width=width,
            height=height,
            diagonal_probability=diagonal_probability,
            max_diagonal_angle=max_diagonal_angle,
            image_aspects=image_aspects,
        )
        if recursive_panels and len(recursive_panels) >= max(1, num_panels - 1):
            return recursive_panels[:num_panels]
    except Exception as exc:
        print(f"⚠️ Recursive layout fallback to legacy adaptive layout: {exc}")
    
    # 🆕 GRID-BASED VERTEX SHIFTING: Tạo panels theo grid và dịch chuyển đỉnh
    # Đây là phương pháp ổn định nhất cho Manga layout
    if force_aspect_matched or diagonal_probability > 0.5:
        print(f"🎨 Using VERTEX-SHIFTED GRID layout (jitter={max_diagonal_angle})")
        return create_dynamic_grid_layout(
            image_aspects,
            width=width,
            height=height,
            jitter_factor=max_diagonal_angle * 0.8, # Quy đổi góc sang độ lệch pixel
            margin=4
        )
    
    # 🔻 OLD MODE: Split polygons (backward compatibility)
    
    # Xác định orientation CHỦ ĐẠO của trang này (theo đa số ảnh)
    landscape_count = sum(1 for img in image_aspects if img['orientation'] == 'landscape')
    portrait_count = sum(1 for img in image_aspects if img['orientation'] == 'portrait')
    square_count = sum(1 for img in image_aspects if img['orientation'] == 'square')
    
    # Chọn orientation chủ đạo
    if landscape_count >= portrait_count and landscape_count >= square_count:
        dominant_orientation = 'landscape'
    elif portrait_count >= landscape_count and portrait_count >= square_count:
        dominant_orientation = 'portrait'
    else:
        dominant_orientation = 'square'
    
    # 🆕 Tính tổng panel weight để phân bổ diện tích
    total_weight = sum(img.get('panel_weight', 1.0) for img in image_aspects)
    if total_weight == 0:
        total_weight = num_panels
    
    # Bắt đầu với 1 polygon toàn trang
    initial_polygon = Polygon([[0, 0], [width, 0], [width, height], [0, height]])
    polygons = [initial_polygon]
    
    # 🆕 Track target weight cho mỗi panel (để matching sau)
    panel_target_weights = []
    
    attempts = 0
    max_attempts = num_panels * 3
    panel_index = 0
    
    while len(polygons) < num_panels and attempts < max_attempts:
        attempts += 1
        
        # Sắp xếp theo diện tích
        polygons.sort(key=lambda p: p.get_area(), reverse=True)
        poly = polygons.pop(0)
        x, y, w, h = poly.get_bounds()
        
        # Kiểm tra kích thước tối thiểu
        min_size = 15
        if w < min_size or h < min_size:
            polygons.insert(0, poly)
            continue
        
        # Dùng orientation CHỦ ĐẠO của trang làm HƯỚNG DẪN (không cứng nhắc)
        preferred_orientation = dominant_orientation
        
        # Tính aspect ratio của panel hiện tại
        panel_aspect = w / h
        
        # Quyết định hướng cắt DỰA TRÊN PANEL HIỆN TẠI và orientation chủ đạo
        # Logic: Cân bằng giữa tạo panels phù hợp với ảnh và tạo layout đẹp
        if preferred_orientation == 'landscape':
            # Đa số ảnh NGANG → Ưu tiên tạo panels ngang
            # Nhưng nếu panel hiện tại QUÁ NGANG rồi (aspect > 2), cắt dọc để cân bằng
            should_split_horizontal = panel_aspect < 2.0
        elif preferred_orientation == 'portrait':
            # Đa số ảnh DỌC → Ưu tiên tạo panels dọc
            # Nhưng nếu panel hiện tại QUÁ DỌC rồi (aspect < 0.5), cắt ngang để cân bằng
            should_split_horizontal = panel_aspect > 0.5
        else:  # square
            # Đa số ảnh VUÔNG → Cắt theo chiều dài hơn để tạo panels cân đối
            should_split_horizontal = h > w
        
        # 🆕 Tính adaptive split ratio dựa trên panel_weight của 2 ảnh tiếp theo
        current_panel_idx = len(panel_target_weights)
        if current_panel_idx < len(image_aspects) - 1:
            weight1 = image_aspects[current_panel_idx].get('panel_weight', 1.0)
            weight2 = image_aspects[current_panel_idx + 1].get('panel_weight', 1.0)
            # Normalize weights to get split ratio (0.3-0.7 range)
            weight_sum = weight1 + weight2
            if weight_sum > 0:
                split_ratio = 0.3 + (weight1 / weight_sum) * 0.4  # Maps to 0.3-0.7
            else:
                split_ratio = 0.5
        else:
            split_ratio = random.uniform(0.4, 0.6)
        
        # Quyết định cắt chéo hay vuông góc
        use_diagonal = random.random() < diagonal_probability and len(poly.vertices) == 4
        poly1, poly2 = None, None
        
        if use_diagonal:
            # 🆕 V2: Get content info cho adaptive diagonal angle
            current_idx = len(panel_target_weights)
            if current_idx < len(image_aspects):
                img_weight = image_aspects[current_idx].get('panel_weight', 1.0)
                # Determine content_type from shot_type (if available)
                shot_type = image_aspects[current_idx].get('shot_type', 'normal')
                # Map shot_type to content_type
                content_map = {
                    'wide': 'action',
                    'closeup': 'close_up',
                    'medium': 'normal'
                }
                content_type = content_map.get(shot_type, 'normal')
            else:
                img_weight = 1.0
                content_type = 'normal'
            
            poly1, poly2 = poly.split_diagonal(
                max_angle=max_diagonal_angle,
                content_type=content_type,
                panel_weight=img_weight
            )
        
        # Nếu cắt chéo thất bại -> cắt vuông góc với adaptive split ratio
        if poly1 is None or poly2 is None:
            # 🆕 Add minimum gap giữa 2 panels để tránh overlap
            min_gap = 1.0  # Minimum gap between panels
            
            if should_split_horizontal:
                # Cắt ngang (tạo 2 panels nằm ngang)
                split_pos = split_ratio * h
                # Đảm bảo có gap
                poly1 = Polygon([[x, y], [x+w, y], [x+w, y+split_pos-min_gap/2], [x, y+split_pos-min_gap/2]])
                poly2 = Polygon([[x, y+split_pos+min_gap/2], [x+w, y+split_pos+min_gap/2], [x+w, y+h], [x, y+h]])
            else:
                # Cắt dọc (tạo 2 panels đứng dọc)
                split_pos = split_ratio * w
                # Đảm bảo có gap
                poly1 = Polygon([[x, y], [x+split_pos-min_gap/2, y], [x+split_pos-min_gap/2, y+h], [x, y+h]])
                poly2 = Polygon([[x+split_pos+min_gap/2, y], [x+w, y], [x+w, y+h], [x+split_pos+min_gap/2, y+h]])
        
        # 🆕 Kiểm tra overlap, aspect ratio và kích thước minimum
        max_aspect = PANEL_MAX_ASPECT
        min_aspect = PANEL_MIN_ASPECT
        min_panel_size = 10  # Minimum width/height
        
        if poly1 and poly2:
            p1_bounds = poly1.get_bounds()
            p2_bounds = poly2.get_bounds()
            p1_aspect = p1_bounds[2] / p1_bounds[3] if p1_bounds[3] > 0 else 1
            p2_aspect = p2_bounds[2] / p2_bounds[3] if p2_bounds[3] > 0 else 1
            
            # 🆕 Check overlap giữa poly1 và poly2
            if poly1.overlaps_with(poly2):
                print(f"⚠️  Diagonal cut created overlap! Rejecting and retrying...")
                print(f"   Panel 1 bounds: {p1_bounds}")
                print(f"   Panel 2 bounds: {p2_bounds}")
                polygons.insert(0, poly)
                continue
            
            # 🆕 Check kích thước minimum
            if (p1_bounds[2] < min_panel_size or p1_bounds[3] < min_panel_size or
                p2_bounds[2] < min_panel_size or p2_bounds[3] < min_panel_size):
                polygons.insert(0, poly)
                continue
            
            # Nếu panels quá hẹp hoặc quá cao, bỏ qua lần cắt này
            if (p1_aspect > max_aspect or p1_aspect < min_aspect or
                p2_aspect > max_aspect or p2_aspect < min_aspect):
                # Thử panel khác
                if len(polygons) > 0:
                    continue
                else:
                    # Không còn panel nào, phải dừng
                    polygons.append(poly)
                    break
        
        # Kiểm tra polygon hợp lệ - CHỈ CHẤP NHẬN TỨ GIÁC (4) VÀ NGŨ GIÁC (5)
        if (poly1 and poly2 and 
            poly1.get_area() > 50 and poly2.get_area() > 50 and
            len(poly1.vertices) >= 4 and len(poly2.vertices) >= 4 and
            len(poly1.vertices) <= 5 and len(poly2.vertices) <= 5):
            polygons.extend([poly1, poly2])
            
            # 🆕 Track target weight cho 2 panels mới
            if panel_index < len(image_aspects):
                poly1.target_weight = image_aspects[panel_index].get('panel_weight', 1.0)
            if panel_index + 1 < len(image_aspects):
                poly2.target_weight = image_aspects[panel_index + 1].get('panel_weight', 1.0)
            
            panel_index += 2
            # Dừng ngay nếu đã đủ panels
            if len(polygons) >= num_panels:
                break
        else:
            polygons.insert(0, poly)
    
    # 🆕 Attach target_weight cho panels chưa có
    final_panels = polygons[:num_panels]
    for i, poly in enumerate(final_panels):
        if not hasattr(poly, 'target_weight'):
            if i < len(image_aspects):
                poly.target_weight = image_aspects[i].get('panel_weight', 1.0)
            else:
                poly.target_weight = 1.0
    
    # 🆕 FINAL VALIDATION: Check toàn bộ panels không overlap
    overlaps_found = False
    for i in range(len(final_panels)):
        for j in range(i+1, len(final_panels)):
            if final_panels[i].overlaps_with(final_panels[j]):
                print(f"⚠️  WARNING: Panels {i} và {j} overlap!")
                overlaps_found = True
    
    if overlaps_found:
        print("⚠️  Có panels overlap. Đang áp dụng fallback layout...")
        # Fallback: Tạo grid layout đơn giản không overlap
        return create_grid_layout(num_panels, width, height)
    
    return final_panels


def calculate_adaptive_diagonal_angle(content_type='normal', panel_weight=1.0, max_angle=12):
    """
    🆕 Tính góc diagonal THÍCH ỨNG dựa vào nội dung ảnh
    
    Args:
        content_type: Loại nội dung ('action', 'dialogue', 'close_up', 'normal')
        panel_weight: Trọng số panel (>1.5=quan trọng/action, <0.8=background/subtle)
        max_angle: Góc tối đa fallback (nếu không có content info)
    
    Returns:
        float: Góc diagonal (degrees)
    
    Logic:
        📊 WEIGHT-BASED (primary):
            - panel_weight > 1.5  → 10-15° (strong dynamic)
            - 1.2 ≤ weight ≤ 1.5  → 8-12° (moderate dynamic)  
            - 0.8 ≤ weight < 1.2  → 5-8° (light dynamic)
            - weight < 0.8        → 2-5° (subtle)
        
        🎬 TYPE-BASED (secondary):
            - action     → bias +2° (more dynamic)
            - dialogue   → bias -2° (more stable)
            - close_up   → bias -1° (subtle emotion)
            - normal     → no bias
    
    Examples:
        >>> # Action panel (weight=1.8)
        >>> calculate_adaptive_diagonal_angle('action', 1.8, 12)
        14.2  # 12-15 + 2 bias
        
        >>> # Dialogue panel (weight=0.9)
        >>> calculate_adaptive_diagonal_angle('dialogue', 0.9, 12)
        3.8  # 5-8 - 2 bias
        
        >>> # Normal panel (weight=1.0)
        >>> calculate_adaptive_diagonal_angle('normal', 1.0, 12)
        6.5  # 5-8 no bias
    """
    # Step 1: Base angle range dựa vào panel_weight
    if panel_weight > 1.5:
        # Strong dynamic (action, important scene)
        min_angle, max_base = 10, 15
    elif panel_weight >= 1.2:
        # Moderate dynamic
        min_angle, max_base = 8, 12
    elif panel_weight >= 0.8:
        # Light dynamic (normal)
        min_angle, max_base = 5, 8
    else:
        # Subtle (background, calm)
        min_angle, max_base = 2, 5
    
    # Clamp max_base với max_angle parameter
    max_base = min(max_base, max_angle)
    
    # Step 2: Random trong range
    base_angle = random.uniform(min_angle, max_base)
    
    # Step 3: Bias dựa vào content_type
    type_bias = 0
    if content_type == 'action':
        type_bias = 2  # Thêm góc (dynamic hơn)
    elif content_type == 'dialogue':
        type_bias = -2  # Giảm góc (stable hơn)
    elif content_type == 'close_up':
        type_bias = -1  # Giảm nhẹ (subtle emotion)
    # 'normal' → no bias
    
    final_angle = base_angle + type_bias
    
    # Step 4: Clamp vào giới hạn hợp lý
    final_angle = max(1, min(final_angle, 20))  # 1-20° range
    
    return final_angle


class Polygon:
    """Lớp đại diện cho một đa giác (panel)"""
    def __init__(self, vertices):
        self.vertices = np.array(vertices)
        self.image = None  # Ảnh được gán vào panel này
    
    def get_area(self):
        """Tính diện tích đa giác bằng công thức Shoelace"""
        x = self.vertices[:, 0]
        y = self.vertices[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    
    def overlaps_with(self, other, tolerance=0.1):
        """
        🆕 V2: Kiểm tra overlap CHÍNH XÁC hơn
        
        Dùng 2-stage check:
        1. Bounding box overlap (fast check)
        2. Polygon overlap (accurate check nếu bounding boxes overlap)
        
        tolerance: 0.1 (strict) - detect even small overlaps
        """
        # Stage 1: Bounding box check (fast)
        x1_min, y1_min, w1, h1 = self.get_bounds()
        x2_min, y2_min, w2, h2 = other.get_bounds()
        
        x1_max, y1_max = x1_min + w1, y1_min + h1
        x2_max, y2_max = x2_min + w2, y2_min + h2
        
        # Check overlap với tolerance để tránh floating point errors
        overlap_x = not (x1_max <= x2_min + tolerance or x2_max <= x1_min + tolerance)
        overlap_y = not (y1_max <= y2_min + tolerance or y2_max <= y1_min + tolerance)
        
        bbox_overlap = overlap_x and overlap_y
        
        if not bbox_overlap:
            return False  # Không overlap chắc chắn
        
        # Stage 2: Polygon overlap check (accurate)
        # Check nếu có vertex nào của poly1 nằm trong poly2 hoặc ngược lại
        from matplotlib.path import Path
        
        path1 = Path(self.vertices)
        path2 = Path(other.vertices)
        
        # Check vertices của poly2 có nằm trong poly1 không
        for vertex in other.vertices:
            if path1.contains_point(vertex, radius=-tolerance):
                return True
        
        # Check vertices của poly1 có nằm trong poly2 không
        for vertex in self.vertices:
            if path2.contains_point(vertex, radius=-tolerance):
                return True
        
        # Check edges intersection (nếu cần - optional, tốn performance)
        # Hiện tại bỏ qua vì đã có gap offset
        
        return False
    
    def get_bounds(self):
        """Lấy hình chữ nhật bao quanh"""
        x_min, y_min = self.vertices.min(axis=0)
        x_max, y_max = self.vertices.max(axis=0)
        return x_min, y_min, x_max - x_min, y_max - y_min

    @staticmethod
    def _segments_intersect(a, b, c, d):
        """Kiểm tra giao nhau giữa 2 đoạn thẳng (không tính đỉnh kề nhau)."""
        def ccw(p1, p2, p3):
            return (p3[1] - p1[1]) * (p2[0] - p1[0]) > (p2[1] - p1[1]) * (p3[0] - p1[0])

        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    def is_simple(self):
        """Đa giác hợp lệ nếu không tự cắt nhau và có diện tích dương."""
        verts = np.array(self.vertices)
        n = len(verts)
        if n < 3:
            return False
        if not np.isfinite(verts).all():
            return False
        if self.get_area() <= 1e-6:
            return False

        # Check self-intersection giữa các cạnh không kề nhau.
        for i in range(n):
            a1 = verts[i]
            a2 = verts[(i + 1) % n]
            for j in range(i + 1, n):
                # Bỏ qua cạnh kề nhau hoặc cùng cạnh.
                if j == i or (j + 1) % n == i or (i + 1) % n == j:
                    continue
                b1 = verts[j]
                b2 = verts[(j + 1) % n]
                if Polygon._segments_intersect(a1, a2, b1, b2):
                    return False
        return True

    @staticmethod
    def _order_quad_points(points):
        """Sắp xếp 4 điểm theo thứ tự TL,TR,BR,BL (hệ y-down), chống xoay 90°/lật ngang."""
        pts = np.array(points, dtype=np.float32)
        if pts.shape != (4, 2):
            return None

        def _safe_norm(v):
            n = float(np.hypot(v[0], v[1]))
            return max(1e-6, n)

        def _is_valid(cand):
            # cand: [TL, TR, BR, BL]
            tl, tr, br, bl = cand

            y_top = 0.5 * (tl[1] + tr[1])
            y_bottom = 0.5 * (bl[1] + br[1])
            x_left = 0.5 * (tl[0] + bl[0])
            x_right = 0.5 * (tr[0] + br[0])

            # Điều kiện cứng để loại mapping quay 90° hoặc mirror.
            if not (y_top < y_bottom and x_left < x_right):
                return False
            if not (tl[1] <= bl[1] and tr[1] <= br[1]):
                return False
            if not (tl[0] <= tr[0] and bl[0] <= br[0]):
                return False

            # Diện tích phải khác 0 để tránh cấu hình suy biến.
            area2 = 0.0
            for i in range(4):
                x1, y1 = cand[i]
                x2, y2 = cand[(i + 1) % 4]
                area2 += (x1 * y2) - (x2 * y1)
            if abs(area2) < 1e-3:
                return False

            return True

        # Anchor box corners: TL, TR, BR, BL trong hệ y-down.
        x_min = float(np.min(pts[:, 0]))
        y_min = float(np.min(pts[:, 1]))
        x_max = float(np.max(pts[:, 0]))
        y_max = float(np.max(pts[:, 1]))
        anchors = np.array(
            [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]],
            dtype=np.float32,
        )

        best = None
        best_score = float('inf')
        second_score = float('inf')

        # Thử toàn bộ 24 hoán vị để tránh miss corner ở các panel mép/góc bị xiên mạnh.
        for perm in itertools.permutations(range(4)):
            cand = pts[list(perm)]  # [TL, TR, BR, BL] theo giả định
            if not _is_valid(cand):
                continue

            # Score 1: khớp với 4 anchor corners của bounding box.
            corner_score = float(np.sum((cand - anchors) ** 2))

            # Score 2: ưu tiên hình học ổn định, giảm xoay bất thường 90°.
            v_top = cand[1] - cand[0]
            v_left = cand[3] - cand[0]
            dot = abs(float(np.dot(v_top, v_left)))
            ortho_penalty = (dot / (_safe_norm(v_top) * _safe_norm(v_left))) * 50.0

            l01 = _safe_norm(cand[1] - cand[0])
            l12 = _safe_norm(cand[2] - cand[1])
            l23 = _safe_norm(cand[3] - cand[2])
            l30 = _safe_norm(cand[0] - cand[3])
            edge_penalty = (abs(l01 - l23) + abs(l12 - l30)) * 0.02

            score = corner_score + ortho_penalty + edge_penalty

            if score < best_score:
                second_score = best_score
                best_score = score
                best = cand
            elif score < second_score:
                second_score = score

        if best is None:
            return None

        # Nếu 2 phương án tốt nhất quá sát nhau, bỏ warp để tránh panel xoay ngẫu nhiên.
        if abs(second_score - best_score) < 1e-2:
            return None

        ordered = np.array(best, dtype=np.float32)

        if not np.isfinite(ordered).all():
            return None
        return ordered

    @staticmethod
    def _warp_rgba_to_quad(src_rgba, quad_points, render_scale=28.0):
        """Warp ảnh RGBA hình chữ nhật vào tứ giác đích bằng biến đổi phối cảnh."""
        try:
            import cv2
        except Exception:
            return None, None

        if src_rgba is None or len(src_rgba.shape) != 3 or src_rgba.shape[2] != 4:
            return None, None

        src_h, src_w = src_rgba.shape[:2]
        if src_w < 2 or src_h < 2:
            return None, None

        quad = np.array(quad_points, dtype=np.float32)
        if quad.shape != (4, 2) or not np.isfinite(quad).all():
            return None, None

        x_min_f = float(np.min(quad[:, 0]))
        y_min_f = float(np.min(quad[:, 1]))
        x_max_f = float(np.max(quad[:, 0]))
        y_max_f = float(np.max(quad[:, 1]))

        x_min = int(np.floor(x_min_f))
        y_min = int(np.floor(y_min_f))
        x_max = int(np.ceil(x_max_f))
        y_max = int(np.ceil(y_max_f))

        out_w_units = x_max_f - x_min_f
        out_h_units = y_max_f - y_min_f
        if out_w_units < 1e-3 or out_h_units < 1e-3:
            return None, None

        # Render ở mật độ cao để tránh ảnh bị bệt/mờ khi panel lớn trên trang output.
        out_w = max(2, int(np.ceil(out_w_units * render_scale)))
        out_h = max(2, int(np.ceil(out_h_units * render_scale)))

        # Convert từ hệ tọa độ trang (y-up) sang hệ ảnh raster (y-down) trước khi order points.
        dst_local = np.zeros((4, 2), dtype=np.float32)
        dst_local[:, 0] = (quad[:, 0] - x_min_f) * render_scale
        dst_local[:, 1] = (y_max_f - quad[:, 1]) * render_scale

        ordered_quad = Polygon._order_quad_points(dst_local)
        if ordered_quad is None:
            return None, None

        base_src = np.array(
            [[0, 0], [src_w - 1, 0], [src_w - 1, src_h - 1], [0, src_h - 1]],
            dtype=np.float32,
        )  # TL, TR, BR, BL
        src_candidates = [
            base_src,
            np.array([base_src[1], base_src[2], base_src[3], base_src[0]], dtype=np.float32),
            np.array([base_src[2], base_src[3], base_src[0], base_src[1]], dtype=np.float32),
            np.array([base_src[3], base_src[0], base_src[1], base_src[2]], dtype=np.float32),
        ]

        def _project_point(H, p):
            x, y = float(p[0]), float(p[1])
            denom = (H[2, 0] * x) + (H[2, 1] * y) + H[2, 2]
            if abs(denom) < 1e-8:
                return None
            ox = ((H[0, 0] * x) + (H[0, 1] * y) + H[0, 2]) / denom
            oy = ((H[1, 0] * x) + (H[1, 1] * y) + H[1, 2]) / denom
            return np.array([ox, oy], dtype=np.float32)

        top_mid = np.array([(src_w - 1) * 0.5, 0.0], dtype=np.float32)
        bottom_mid = np.array([(src_w - 1) * 0.5, src_h - 1.0], dtype=np.float32)

        best_matrix = None
        best_score = -1e18
        for src_quad in src_candidates:
            H = cv2.getPerspectiveTransform(src_quad, ordered_quad)
            p_top = _project_point(H, top_mid)
            p_bottom = _project_point(H, bottom_mid)
            if p_top is None or p_bottom is None:
                continue

            v = p_bottom - p_top
            # Ưu tiên mapping giữ trục dọc của ảnh thành dọc trang (không bị nằm ngang).
            score = abs(float(v[1])) - abs(float(v[0]))
            if v[1] > 0:
                score += 0.05

            if score > best_score:
                best_score = score
                best_matrix = H

        if best_matrix is None:
            return None, None

        matrix = best_matrix
        warped = cv2.warpPerspective(
            src_rgba,
            matrix,
            (out_w, out_h),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

        return warped, (x_min, y_min, x_max, y_max)
    
    def split_diagonal(self, max_angle=12, content_type='normal', panel_weight=1.0):
        """
        Cắt đa giác bằng đường chéo NHẸ với GÓC THÍCH ỨNG - UPGRADED V2
        
        Args:
            max_angle: Góc nghiêng tối đa (degrees), default=12 độ (fallback)
            content_type: Loại content ('action', 'dialogue', 'close_up', 'normal')
            panel_weight: Trọng số panel (>1.5=important, <0.8=background)
        
        🆕 V2: Góc diagonal THÍCH ỨNG với nội dung:
            - Action/Dynamic (panel_weight > 1.5) → 10-15° (strong diagonal)
            - Normal (0.8 ≤ weight ≤ 1.5) → 5-10° (moderate diagonal)
            - Subtle/Dialogue (weight < 0.8) → 2-5° (light diagonal)
        """
        n = len(self.vertices)
        if n != 4:  # Chỉ cắt hình chữ nhật
            return None, None
        
        x, y, w, h = self.get_bounds()
        
        # Quyết định cắt ngang (horizontal) hay dọc (vertical)
        # Nếu panel ngang (w > h) → cắt ngang, nếu dọc → cắt dọc
        cut_horizontal = w > h
        
        # [UPGRADE V2] Tính góc ADAPTIVE dựa trên nội dung
        angle_deg = calculate_adaptive_diagonal_angle(content_type, panel_weight, max_angle)
        angle_rad = np.deg2rad(angle_deg)
        
        if cut_horizontal:
            # Cắt ngang với đường chéo nhẹ
            # Đường cắt gần song song với cạnh ngang, xéo nhẹ theo chiều dọc
            
            # Vị trí cắt chính (center line)
            split_y = y + h * random.uniform(0.35, 0.65)
            
            # Offset để tạo góc xéo: offset = width * tan(angle)
            # Offset nhỏ → góc nhỏ → đường gần thẳng
            max_offset = w * np.tan(angle_rad)
            offset = random.uniform(-max_offset, max_offset)
            
            # 2 điểm cut trên cạnh trái và phải
            # Điểm trái: (x, split_y + offset_left)
            # Điểm phải: (x+w, split_y + offset_right)
            # offset_left và offset_right ngược nhau để tạo góc
            left_y = split_y - offset/2
            right_y = split_y + offset/2
            
            # Clamp để không vượt bounds
            left_y = np.clip(left_y, y + h*0.1, y + h*0.9)
            right_y = np.clip(right_y, y + h*0.1, y + h*0.9)
            
            # 🆕 V3: 2 panels DÙNG CÙNG đường chéo (mirror)
            # Gap tăng lên 2.0 để tránh viền đè lên nhau (overlap)
            gap_offset = 2.0  # Safe gap length to fit borders
            left_y_bottom = left_y - gap_offset
            right_y_bottom = right_y - gap_offset
            left_y_top = left_y + gap_offset
            right_y_top = right_y + gap_offset
            
            # Tạo 2 polygons với diagonal MIRROR
            # Polygon 1: Phần dưới - đường chéo trên cùng
            poly1_vertices = np.array([
                [x, y],              # Bottom-left
                [x + w, y],          # Bottom-right
                [x + w, right_y_bottom],    # Cut point right (diagonal)
                [x, left_y_bottom]          # Cut point left (diagonal)
            ])
            
            # Polygon 2: Phần trên - đường chéo dưới MIRROR với poly1
            poly2_vertices = np.array([
                [x, left_y_top],         # Cut point left (MIRROR diagonal)
                [x + w, right_y_top],    # Cut point right (MIRROR diagonal)
                [x + w, y + h],      # Top-right
                [x, y + h]           # Top-left
            ])
            
        else:
            # Cắt dọc với đường chéo nhẹ
            # Đường cắt gần song song với cạnh dọc, xéo nhẹ theo chiều ngang
            
            # Vị trí cắt chính (center line)
            split_x = x + w * random.uniform(0.35, 0.65)
            
            # Offset để tạo góc xéo: offset = height * tan(angle)
            max_offset = h * np.tan(angle_rad)
            offset = random.uniform(-max_offset, max_offset)
            
            # 2 điểm cut trên cạnh trên và dưới
            bottom_x = split_x - offset/2
            top_x = split_x + offset/2
            
            # Clamp
            bottom_x = np.clip(bottom_x, x + w*0.1, x + w*0.9)
            top_x = np.clip(top_x, x + w*0.1, x + w*0.9)
            
            # 🆕 V3: 2 panels DÙNG CÙNG đường chéo (mirror)
            # Gap tăng lên 2.0 để tránh viền đè lên nhau (overlap)
            gap_offset = 2.0  # Safe gap length to fit borders
            bottom_x_left = bottom_x - gap_offset
            top_x_left = top_x - gap_offset
            bottom_x_right = bottom_x + gap_offset
            top_x_right = top_x + gap_offset
            
            # Polygon 1: Phần trái - đường chéo bên phải
            poly1_vertices = np.array([
                [x, y],              # Bottom-left
                [bottom_x_left, y],       # Cut point bottom (diagonal)
                [top_x_left, y + h],      # Cut point top (diagonal)
                [x, y + h]           # Top-left
            ])
            
            # Polygon 2: Phần phải - đường chéo bên trái MIRROR với poly1
            poly2_vertices = np.array([
                [bottom_x_right, y],       # Cut point bottom (MIRROR diagonal)
                [x + w, y],          # Bottom-right
                [x + w, y + h],      # Top-right
                [top_x_right, y + h]       # Cut point top (MIRROR diagonal)
            ])
        
        # Validate polygons - Kiểm tra aspect ratio không vượt quá 21:9
        if len(poly1_vertices) >= 4 and len(poly2_vertices) >= 4:
            # Tạo polygons tạm để check aspect ratio
            poly1 = Polygon(poly1_vertices)
            poly2 = Polygon(poly2_vertices)
            
            # Check aspect ratio
            p1_bounds = poly1.get_bounds()
            p2_bounds = poly2.get_bounds()
            p1_w, p1_h = p1_bounds[2], p1_bounds[3]
            p2_w, p2_h = p2_bounds[2], p2_bounds[3]
            
            max_aspect = PANEL_MAX_ASPECT
            min_aspect = PANEL_MIN_ASPECT
            
            # Kiểm tra cả 2 panels không vượt quá 21:9 hoặc 9:21
            if p1_h > 0 and p2_h > 0:
                p1_aspect = p1_w / p1_h
                p2_aspect = p2_w / p2_h
                
                # Nếu 1 trong 2 panels vượt quá max_aspect → reject split
                if (p1_aspect > max_aspect or p1_aspect < min_aspect or
                    p2_aspect > max_aspect or p2_aspect < min_aspect):
                    return None, None
            
            return poly1, poly2
        return None, None
    
    def draw_with_image(self, ax, gap=1.0, show_border=True, draw_speech_bubbles_outside=True, enable_perspective_warp=False):
        """Vẽ đa giác với ảnh bên trong sử dụng Shapely để shrink song song viền"""
        # Hỗ trợ đa giác từ 4-8 cạnh (để handle grid shared points)
        if len(self.vertices) < 4:
            print(f"⚠️  Bỏ qua polygon có {len(self.vertices)} vertices (quá ít)")
            return

        try:
            from shapely.geometry import Polygon as ShapelyPolygon
            poly = ShapelyPolygon(self.vertices)
            
            # buffer với giá trị âm thu nhỏ polygon đồng đều từ mọi viền (chuẩn xác toán học)
            # Dùng join_style=2 (mitre) để giữ các góc nhọn của bounding box không bị bo tròn
            shrunk_poly = poly.buffer(-gap, join_style=2)
            
            if shrunk_poly.is_empty:
                print(f"⚠️ Panel bị mất do gap quá lớn, bỏ qua")
                return
                
            if shrunk_poly.geom_type == 'MultiPolygon':
                shrunk_poly = max(shrunk_poly.geoms, key=lambda a: a.area)
                
            # Lấy list vertices trừ đi điểm cuối (shapely bị trùng điếm cuối lên đầu)
            shrunk_vertices = np.array(shrunk_poly.exterior.coords)[:-1]
        except Exception as e:
            print(f"⚠️ Lỗi shapely shrink: {e}, fallback không shrink")
            shrunk_vertices = np.array(self.vertices)

        # 🆕 Validate shrunk vertices không bị degenerate
        if len(shrunk_vertices) < 3:
            print(f"⚠️  Panel too small after inset, skipping")
            return
        
        # Nếu có ảnh, ưu tiên warp phối cảnh cho panel tứ giác để khớp cạnh chéo chính xác.
        if self.image is not None:
            x_min, y_min = shrunk_vertices.min(axis=0)
            x_max, y_max = shrunk_vertices.max(axis=0)
            
            # 🆕 Validate bounding box hợp lệ
            if x_max <= x_min or y_max <= y_min:
                print(f"⚠️  Invalid panel bounds after shrinking")
                return
            
            used_perspective_warp = False
            can_warp_quad = enable_perspective_warp and len(shrunk_vertices) == 4
            img_rgb = np.array(self.image)

            if can_warp_quad and len(img_rgb.shape) == 3 and img_rgb.shape[2] == 3:
                rgba_base = np.zeros((img_rgb.shape[0], img_rgb.shape[1], 4), dtype=np.uint8)
                rgba_base[:, :, :3] = img_rgb
                rgba_base[:, :, 3] = 255

                warped_rgba, warped_extent = Polygon._warp_rgba_to_quad(rgba_base, shrunk_vertices)
                if warped_rgba is not None and warped_extent is not None:
                    wx_min, wy_min, wx_max, wy_max = warped_extent
                    ax.imshow(
                        warped_rgba,
                        extent=[wx_min, wx_max, wy_min, wy_max],
                        aspect='auto',
                        zorder=1,
                        interpolation='nearest',
                        resample=False,
                    )
                    used_perspective_warp = True

            # Fallback cũ cho panel không phải tứ giác hoặc khi warp thất bại.
            if not used_perspective_warp:
                from matplotlib.patches import PathPatch
                from matplotlib.path import Path as MplPath

                im = ax.imshow(
                    self.image,
                    extent=[x_min, x_max, y_min, y_max],
                    aspect='auto',
                    zorder=1,
                    interpolation='nearest',
                    resample=False,
                )

                path = MplPath(shrunk_vertices)
                patch = PathPatch(path, transform=ax.transData)
                im.set_clip_path(patch)

            # --- NHẬN DIỆN VÀ VẼ ĐÈ BÓNG THOẠI (TÙY CHỌN) ---
            # Để bóng thoại không bị đè bởi viền panel, ta phát hiện vùng text rồi vẽ đè lên trên cùng.
            if draw_speech_bubbles_outside:
                try:
                    import cv2
                    img_cv = np.array(self.image)
                    if len(img_cv.shape) == 3 and img_cv.shape[2] == 3: # Phải là RGB
                        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
                        
                        # Tìm các vùng màu trắng (240-255)
                        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
                        
                        # Lấy contours cùng tính phân cấp (hierarchy)
                        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
                        
                        mask = np.zeros_like(gray)
                        has_bubble = False
                        
                        if hierarchy is not None:
                            img_area = gray.shape[0] * gray.shape[1]
                            for i, contour in enumerate(contours):
                                area = cv2.contourArea(contour)
                                # Giới hạn tỷ lệ diện tích bóng thoại: 0.5% - 40% panel
                                if 0.005 * img_area < area < 0.4 * img_area:
                                    # Xác định có chứa contour con (text) bên trong không
                                    if hierarchy[0][i][2] != -1:
                                        child_idx = hierarchy[0][i][2]
                                        children_count = 0
                                        # Đếm số kí tự/hình con trong vùng trắng
                                        while child_idx != -1:
                                            children_count += 1
                                            child_idx = hierarchy[0][child_idx][0]
                                        
                                        # Nếu có từ 2 kí tự trong đó trở lên -> Coi như bóng thoại
                                        if children_count >= 2:
                                            cv2.drawContours(mask, [contour], 0, 255, -1)
                                            has_bubble = True
                                            
                        if has_bubble:
                            # Làm mượt và phình to vùng mask một xíu để lấy trọn viền nét vẽ của bóng
                            kernel = np.ones((5,5), np.uint8)
                            mask = cv2.dilate(mask, kernel, iterations=1)
                            
                            # Tạo ảnh RGBA từ ảnh gốc + lớp mờ (mask) cực chuẩn
                            rgba = np.zeros((img_cv.shape[0], img_cv.shape[1], 4), dtype=np.uint8)
                            rgba[:, :, :3] = img_cv
                            rgba[:, :, 3] = mask # Channel Alpha chỉ hiện hình bóng thoại
                            
                            # Nếu có warp phối cảnh thì warp mask thoại theo cùng ma trận để không bị lệch cạnh chéo.
                            if used_perspective_warp and len(shrunk_vertices) == 4:
                                warped_bubble, bubble_extent = Polygon._warp_rgba_to_quad(rgba, shrunk_vertices)
                                if warped_bubble is not None and bubble_extent is not None:
                                    bx_min, by_min, bx_max, by_max = bubble_extent
                                    ax.imshow(
                                        warped_bubble,
                                        extent=[bx_min, bx_max, by_min, by_max],
                                        aspect='auto',
                                        zorder=5,
                                        interpolation='nearest',
                                        resample=False,
                                    )
                                else:
                                    ax.imshow(
                                        rgba,
                                        extent=[x_min, x_max, y_min, y_max],
                                        aspect='auto',
                                        zorder=5,
                                        interpolation='nearest',
                                        resample=False,
                                    )
                            else:
                                ax.imshow(
                                    rgba,
                                    extent=[x_min, x_max, y_min, y_max],
                                    aspect='auto',
                                    zorder=5,
                                    interpolation='nearest',
                                    resample=False,
                                )
                except Exception as e:
                    print(f"⚠️ Lỗi nhận diện/vẽ đè bóng thoại: {e}")
        
        # Vẽ border với linewidth tăng để dễ nhìn gap
        # Vẽ border với linewidth mảnh để tinh tế hơn
        if show_border:
            polygon = patches.Polygon(shrunk_vertices, linewidth=1.5, 
                                     edgecolor='black', facecolor='none', 
                                     zorder=3, joinstyle='miter')
            ax.add_patch(polygon)


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
                    'width': img.width,
                    'height': img.height
                })
        except Exception as e:
            print(f"⚠️  Không đọc được {img_path}: {e}")
    
    return image_info


def create_aspect_matched_layout(image_aspects, page_width=100, page_height=140, diagonal_tilt=3, margin=2):
    """
    TẠO PANELS ĐẦY RỘNG TRANG, chiều cao tỷ lệ với aspect ratio ảnh.
    Panel luôn bắt đầu từ margin trái, rộng hết trang → không bao giờ nổi lơ lửng.
    Tuỳ chọn nghiêng nhẹ (rotate) để tạo feel manga.
    """
    panels = []
    num_images = len(image_aspects)
    
    if num_images == 0:
        return panels
    
    panel_width = page_width - 2 * margin  # Panel luôn full-width
    
    # Chiều cao tự nhiên khi panel full-width: height = width / aspect
    natural_heights = []
    for img_data in image_aspects:
        aspect = max(0.1, img_data.get('aspect', 1.0))  # tránh div-by-zero
        natural_heights.append(panel_width / aspect)
    
    # Co tỷ lệ để tổng heights vừa khít trang
    total_available = page_height - 2 * margin - (num_images - 1) * margin
    if total_available <= 0:
        total_available = page_height * 0.9
    total_natural = sum(natural_heights) or 1
    scale = total_available / total_natural
    
    current_y = margin
    
    for i, (img_data, natural_h) in enumerate(zip(image_aspects, natural_heights)):
        panel_height = natural_h * scale
        panel_x = margin
        panel_y = current_y
        
        # Create rectangular vertices (KHÔNG cắt chéo!)
        rect_vertices = np.array([
            [panel_x, panel_y],
            [panel_x + panel_width, panel_y],
            [panel_x + panel_width, panel_y + panel_height],
            [panel_x, panel_y + panel_height]
        ])
        
        # Apply SLIGHT rotation (2-3 degrees) around center - 50% xác suất
        if diagonal_tilt > 0 and random.random() < 0.5:
            angle_deg = random.uniform(-diagonal_tilt, diagonal_tilt)
            angle_rad = np.deg2rad(angle_deg)
            
            # Center of panel
            center_x = panel_x + panel_width / 2
            center_y = panel_y + panel_height / 2
            
            # Rotate each vertex around center
            tilted_vertices = []
            for vx, vy in rect_vertices:
                # Translate to origin
                dx = vx - center_x
                dy = vy - center_y
                
                # Rotate
                new_dx = dx * np.cos(angle_rad) - dy * np.sin(angle_rad)
                new_dy = dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
                
                # Translate back
                new_x = center_x + new_dx
                new_y = center_y + new_dy
                tilted_vertices.append([new_x, new_y])
            
            panel = Polygon(np.array(tilted_vertices))
        else:
            # No tilt, keep rectangular
            panel = Polygon(rect_vertices)
        
        panels.append(panel)
        
        # Tiến tới vị trí panel tiếp theo
        current_y += panel_height + margin
    
    return panels


def create_grid_layout(num_panels, width=100, height=140):
    """🆕 Fallback: Tạo grid layout đơn giản, KHÔNG overlap (safe)"""
    polygons = []
    gap = 3.0  # Gap giữa panels (tăng lên để đảm bảo không overlap)
    
    if num_panels <= 2:
        # 2 panels vertical
        mid = height / 2
        polygons.append(Polygon([[0, 0], [width, 0], [width, mid-gap], [0, mid-gap]]))
        polygons.append(Polygon([[0, mid+gap], [width, mid+gap], [width, height], [0, height]]))
    elif num_panels == 3:
        # Top full + bottom 2
        mid_h = height * 0.5
        mid_w = width / 2
        polygons.append(Polygon([[0, 0], [width, 0], [width, mid_h-gap], [0, mid_h-gap]]))
        polygons.append(Polygon([[0, mid_h+gap], [mid_w-gap, mid_h+gap], [mid_w-gap, height], [0, height]]))
        polygons.append(Polygon([[mid_w+gap, mid_h+gap], [width, mid_h+gap], [width, height], [mid_w+gap, height]]))
    elif num_panels == 4:
        # 2x2 grid
        mid_w, mid_h = width/2, height/2
        polygons.append(Polygon([[0, 0], [mid_w-gap, 0], [mid_w-gap, mid_h-gap], [0, mid_h-gap]]))
        polygons.append(Polygon([[mid_w+gap, 0], [width, 0], [width, mid_h-gap], [mid_w+gap, mid_h-gap]]))
        polygons.append(Polygon([[0, mid_h+gap], [mid_w-gap, mid_h+gap], [mid_w-gap, height], [0, height]]))
        polygons.append(Polygon([[mid_w+gap, mid_h+gap], [width, mid_h+gap], [width, height], [mid_w+gap, height]]))
    elif num_panels == 5:
        # 5 panels: Top 2 + bottom 3
        top_h = height * 0.45
        mid_w = width / 2
        bottom_panel_w = width / 3
        
        # Top 2 panels
        polygons.append(Polygon([[0, 0], [mid_w-gap, 0], [mid_w-gap, top_h-gap], [0, top_h-gap]]))
        polygons.append(Polygon([[mid_w+gap, 0], [width, 0], [width, top_h-gap], [mid_w+gap, top_h-gap]]))
        
        # Bottom 3 panels  
        y_start = top_h + gap
        polygons.append(Polygon([[0, y_start], [bottom_panel_w-gap, y_start], 
                                [bottom_panel_w-gap, height], [0, height]]))
        polygons.append(Polygon([[bottom_panel_w+gap, y_start], [2*bottom_panel_w-gap, y_start],
                                [2*bottom_panel_w-gap, height], [bottom_panel_w+gap, height]]))
        polygons.append(Polygon([[2*bottom_panel_w+gap, y_start], [width, y_start],
                                [width, height], [2*bottom_panel_w+gap, height]]))
    elif num_panels == 6:
        # 6 panels: 2x3 grid
        col_w = width / 2
        row_h = height / 3
        
        for row in range(3):
            for col in range(2):
                x = col * col_w
                y = row * row_h
                # Add gap
                x1 = x + gap if col > 0 else x
                y1 = y + gap if row > 0 else y
                x2 = x + col_w - gap if col < 1 else x + col_w
                y2 = y + row_h - gap if row < 2 else y + row_h
                
                polygons.append(Polygon([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]))
    else:
        # 7+ panels: Top row + middle + bottom grid
        top_h = height * 0.35
        mid_h = height * 0.65
        cols = 3
        
        # Top 2 panels
        mid_w = width / 2
        polygons.append(Polygon([[0, 0], [mid_w-gap, 0], [mid_w-gap, top_h-gap], [0, top_h-gap]]))
        polygons.append(Polygon([[mid_w+gap, 0], [width, 0], [width, top_h-gap], [mid_w+gap, top_h-gap]]))
        
        # Bottom grid (remaining panels)
        remaining = num_panels - 2
        panel_w = width / cols
        y_start = top_h + gap
        
        for i in range(remaining):
            col = i % cols
            row = i // cols
            x = col * panel_w
            y = y_start + row * ((height - y_start) / ((remaining + cols - 1) // cols))
            
            x1 = x + gap if col > 0 else x
            y1 = y + gap if row > 0 else y
            x2 = x + panel_w - gap if col < cols-1 else x + panel_w
            y2 = y + ((height - y_start) / ((remaining + cols - 1) // cols)) - gap
            
            if i < remaining:
                polygons.append(Polygon([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]))
    
    return polygons[:num_panels]


def create_recursive_subdivision_layout(
    num_panels=5,
    width=100,
    height=140,
    diagonal_probability=0.3,
    max_diagonal_angle=12,
    image_aspects=None,
):
    """
    Recursive subdivision layout dùng chung cho Auto Frame và Comic từ ảnh upload.
    Mục tiêu: panel cân bằng hơn, vẫn có ngẫu nhiên và giữ được gutter giữa các khung.
    """
    if num_panels <= 0:
        return []

    rng = random.Random()
    min_gap = max(0.8, min(2.4, 0.8 + diagonal_probability * 1.6))
    min_panel_w = max(10.0, width * 0.12)
    min_panel_h = max(10.0, height * 0.12)

    # Ước lượng panel aspect lý tưởng từ ảnh upload nếu có.
    if image_aspects:
        vals = []
        for info in image_aspects:
            try:
                vals.append(float(info.get('aspect', 1.0)))
            except Exception:
                pass
        if vals:
            vals.sort()
            ideal_aspect = vals[len(vals) // 2]
        else:
            ideal_aspect = width / max(1e-6, height)
    else:
        ideal_aspect = width / max(1e-6, height)
    ideal_aspect = max(0.55, min(2.2, ideal_aspect))

    def can_split(poly):
        x, y, w, h = poly.get_bounds()
        return w >= (min_panel_w * 1.25) and h >= (min_panel_h * 1.25) and poly.get_area() >= (min_panel_w * min_panel_h)

    def panel_badness(poly):
        _, _, w, h = poly.get_bounds()
        h = max(1e-6, h)
        ar = w / h
        score = abs(np.log(max(1e-6, ar / ideal_aspect)))
        if ar < PANEL_MIN_ASPECT:
            score += (PANEL_MIN_ASPECT - ar) * 6.0
        if ar > PANEL_MAX_ASPECT:
            score += (ar - PANEL_MAX_ASPECT) * 4.0
        if w < min_panel_w:
            score += ((min_panel_w - w) / min_panel_w) * 2.0
        if h < min_panel_h:
            score += ((min_panel_h - h) / min_panel_h) * 2.0
        return score

    def lerp(a, b, t):
        return np.array([
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
        ], dtype=float)

    def clamp_pt(p):
        return np.array([
            np.clip(p[0], 0.0, width),
            np.clip(p[1], 0.0, height),
        ], dtype=float)

    def offset_cut_edge(a, b, distance):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = np.hypot(dx, dy)
        if length < 1e-6:
            return a, b, a, b
        nx = -dy / length
        ny = dx / length
        side_a_1 = clamp_pt(np.array([a[0] - nx * distance, a[1] - ny * distance], dtype=float))
        side_a_2 = clamp_pt(np.array([b[0] - nx * distance, b[1] - ny * distance], dtype=float))
        side_b_1 = clamp_pt(np.array([a[0] + nx * distance, a[1] + ny * distance], dtype=float))
        side_b_2 = clamp_pt(np.array([b[0] + nx * distance, b[1] + ny * distance], dtype=float))
        return side_a_1, side_a_2, side_b_1, side_b_2

    def make_split(poly, split_ratio=0.5, force_axis=None):
        x, y, w, h = poly.get_bounds()
        split_ratio = max(0.22, min(0.78, split_ratio))

        if force_axis is None:
            if w > h * 1.25:
                axis = 'vertical'
            elif h > w * 1.25:
                axis = 'horizontal'
            else:
                axis = 'horizontal' if rng.random() < 0.5 else 'vertical'
        else:
            axis = force_axis

        diag_strength = min(1.0, max(0.0, diagonal_probability))
        line_tilt = (0.01 + 0.09 * diag_strength + (max_diagonal_angle / 100.0)) * (1 if rng.random() > 0.5 else -1)
        jitter = 0.02 + 0.08 * diag_strength
        t1 = max(0.18, min(0.82, split_ratio + rng.uniform(-jitter, jitter)))
        t2 = max(0.18, min(0.82, split_ratio + line_tilt + rng.uniform(-jitter, jitter)))

        verts = np.array(poly.vertices, dtype=float)
        if len(verts) != 4:
            # fallback an toàn cho polygon không phải tứ giác
            if axis == 'horizontal':
                left_y = y + h * t1
                right_y = y + h * t2
                poly1 = Polygon([[x, y], [x + w, y], [x + w, right_y - min_gap / 2], [x, left_y - min_gap / 2]])
                poly2 = Polygon([[x, left_y + min_gap / 2], [x + w, right_y + min_gap / 2], [x + w, y + h], [x, y + h]])
                return poly1, poly2

            bottom_x = x + w * t1
            top_x = x + w * t2
            poly1 = Polygon([[x, y], [bottom_x - min_gap / 2, y], [top_x - min_gap / 2, y + h], [x, y + h]])
            poly2 = Polygon([[bottom_x + min_gap / 2, y], [x + w, y], [x + w, y + h], [top_x + min_gap / 2, y + h]])
            return poly1, poly2

        v0, v1, v2, v3 = verts

        if axis == 'horizontal':
            left_cut = lerp(v0, v3, t1)
            right_cut = lerp(v1, v2, t2)
            top_left, top_right, bottom_left, bottom_right = offset_cut_edge(left_cut, right_cut, min_gap * 0.5)
            top_poly = Polygon([v0, v1, top_right, top_left])
            bottom_poly = Polygon([bottom_left, bottom_right, v2, v3])
            return top_poly, bottom_poly

        top_cut = lerp(v0, v1, t1)
        bottom_cut = lerp(v3, v2, t2)
        side_a_top, side_a_bottom, side_b_top, side_b_bottom = offset_cut_edge(top_cut, bottom_cut, min_gap * 0.5)
        left_poly = Polygon([v0, side_b_top, side_b_bottom, v3])
        right_poly = Polygon([side_a_top, v1, v2, side_a_bottom])
        return left_poly, right_poly

    def best_split(poly, left_quota, right_quota):
        x, y, w, h = poly.get_bounds()
        target_ratio = left_quota / max(1, left_quota + right_quota)

        if w > h * 1.2:
            axis_candidates = ['vertical', 'horizontal']
        elif h > w * 1.2:
            axis_candidates = ['horizontal', 'vertical']
        else:
            axis_candidates = ['horizontal', 'vertical']

        candidates = []
        sample_n = 10 + int(8 * diagonal_probability)
        for axis in axis_candidates:
            for _ in range(sample_n):
                ratio_noise = rng.uniform(-0.10, 0.10) * diagonal_probability
                ratio_try = max(0.20, min(0.80, target_ratio + ratio_noise))
                p1, p2 = make_split(poly, split_ratio=ratio_try, force_axis=axis)
                if p1.get_area() <= 1 or p2.get_area() <= 1:
                    continue
                if not p1.is_simple() or not p2.is_simple():
                    continue
                if p1.overlaps_with(p2):
                    continue

                area1 = p1.get_area()
                area2 = p2.get_area()
                actual_ratio = area1 / max(1e-6, area1 + area2)
                balance_penalty = abs(actual_ratio - target_ratio) * 8.0

                viability_penalty = 0.0
                if left_quota > 1 and not can_split(p1):
                    viability_penalty += 3.0
                if right_quota > 1 and not can_split(p2):
                    viability_penalty += 3.0

                score = balance_penalty + panel_badness(p1) + panel_badness(p2) + viability_penalty
                score += rng.uniform(0.0, 0.18) * diagonal_probability
                candidates.append((score, p1, p2))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        top_k = min(len(candidates), max(1, 2 + int(4 * diagonal_probability)))
        top = candidates[:top_k]
        weights = [1.0 / (idx + 1) for idx in range(top_k)]
        chosen = rng.choices(top, weights=weights, k=1)[0]
        return chosen[1], chosen[2]

    def choose_quota_pair(total):
        if total <= 2:
            return 1, max(1, total - 1)
        center = total / 2.0
        spread = max(1.0, total * (0.10 + 0.14 * diagonal_probability))
        left = int(round(center + rng.uniform(-spread, spread)))
        left = max(1, min(total - 1, left))
        right = total - left
        return left, right

    def collect_leaves(node):
        if node['left'] is None and node['right'] is None:
            return [node]
        out = []
        if node['left'] is not None:
            out.extend(collect_leaves(node['left']))
        if node['right'] is not None:
            out.extend(collect_leaves(node['right']))
        return out

    def subdivide(node, target):
        if target <= 1 or not can_split(node['poly']):
            return
        left_quota, right_quota = choose_quota_pair(target)
        best = best_split(node['poly'], left_quota, right_quota)
        if best is None:
            return
        p1, p2 = best
        node['left'] = {'poly': p1, 'left': None, 'right': None}
        node['right'] = {'poly': p2, 'left': None, 'right': None}
        if target == 2:
            return
        subdivide(node['left'], left_quota)
        subdivide(node['right'], right_quota)

    root = {
        'poly': Polygon([[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]]),
        'left': None,
        'right': None,
    }

    subdivide(root, max(1, num_panels))
    leaves = collect_leaves(root)

    # Bù panel nếu chưa đủ số lượng.
    while len(leaves) < num_panels:
        candidates = [leaf for leaf in leaves if can_split(leaf['poly'])]
        if not candidates:
            break
        candidate = max(candidates, key=lambda item: item['poly'].get_area())
        best = best_split(candidate['poly'], 1, 1)
        if best is None:
            break
        p1, p2 = best
        candidate['left'] = {'poly': p1, 'left': None, 'right': None}
        candidate['right'] = {'poly': p2, 'left': None, 'right': None}
        leaves = collect_leaves(root)

    return [leaf['poly'] for leaf in leaves[:num_panels]]


def create_page_layout(num_panels=5, width=100, height=140, diagonal_probability=0.3, max_diagonal_angle=12):
    """
    Tạo bố cục cho 1 trang truyện (cải thiện - không overlap)
    
    Returns:
        List[Polygon]: Danh sách các panels không bị chồng lấp
    """
    try:
        panels = create_recursive_subdivision_layout(
            num_panels=num_panels,
            width=width,
            height=height,
            diagonal_probability=diagonal_probability,
            max_diagonal_angle=max_diagonal_angle,
            image_aspects=None,
        )
        if panels:
            return panels
    except Exception as exc:
        print(f"⚠️ Recursive page layout failed, fallback legacy simple grid: {exc}")

    # Fallback cực an toàn nếu recursive gặp lỗi.
    return create_structured_layout(num_panels=num_panels, width=width, height=height)


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
        
        # Fallback: Scale-to-fit (KHÔNG crop khi tắt smart crop)
        if not use_smart_crop or not SMART_CROP_AVAILABLE:
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img).convert('RGB')
            
            # Tính aspect ratio
            img_aspect = img.width / img.height
            panel_aspect = panel_w / panel_h
            
            # COVER MODE: Crop to match panel_aspect, avoiding distortion when stretched to polygon bounds
            if img_aspect > panel_aspect:
                # Image is wider: center crop horizontally
                crop_width = int(img.height * panel_aspect)
                left = (img.width - crop_width) // 2
                img = img.crop((left, 0, left + crop_width, img.height))
            else:
                # Image is taller: center crop vertically
                crop_height = int(img.width / panel_aspect)
                top = (img.height - crop_height) // 2
                img = img.crop((0, top, img.width, top + crop_height))

            img = img.resize(display_size, Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=2))
        else:
            # Smart crop mode: resize về display_size
            # Nhánh smart crop đã trả ảnh theo display_size ở trên.
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=110, threshold=2))
        
        return np.array(img)
    except Exception as e:
        print(f"⚠️  Lỗi khi đọc ảnh {image_path}: {e}")
        return None


def create_comic_book_from_images(image_folder, output_folder="output_comic", 
                                  panels_per_page=5, diagonal_prob=0.3, adaptive_layout=True,
                                  use_smart_crop=False, reading_direction='ltr', analyze_shot_type=False,
                                  auto_page_size=True, target_dpi=150, classify_characters=False,
                                  draw_speech_bubbles_outside=True,
                                  enable_perspective_warp=DEFAULT_ENABLE_PERSPECTIVE_WARP):
    """
    Tự động tạo comic book từ thư mục ảnh (CẢI THIỆN - Adaptive Layout + Smart Crop + Shot Type + Auto Page Size)
    
    Args:
        image_folder: Thư mục chứa ảnh (001.jpg, 002.jpg, ...)
        output_folder: Thư mục lưu kết quả
        panels_per_page: Số khung mỗi trang (4-7)
        diagonal_prob: Xác suất đường chéo (0-1)
        adaptive_layout: Có tạo layout thích ứng với kích thước ảnh không
        use_smart_crop: Có dùng smart crop (phát hiện text/người) không
        reading_direction: Hướng đọc 'ltr' (left-to-right) hoặc 'rtl' (right-to-left)
        analyze_shot_type: Có phân tích shot type (wide/medium/close-up) để điều chỉnh panel không
        auto_page_size: Có tự động tính kích thước trang dựa trên ảnh đầu vào không
        target_dpi: DPI mục tiêu cho output (150 web, 300 print)
        draw_speech_bubbles_outside: Có hiển thị bóng thoại nhô ra khỏi khung panel không
        enable_perspective_warp: Có biến dạng phối cảnh ảnh theo khung hay không
    """
    # Tạo thư mục output
    os.makedirs(output_folder, exist_ok=True)
    
    # Lấy danh sách ảnh (loại bỏ trùng lặp bằng set)
    image_files_set = set()
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        for file in PathLib(image_folder).glob(ext):
            # Dùng đường dẫn tuyệt đối để tránh trùng lặp
            image_files_set.add(file.resolve())
    
    image_files = sorted(list(image_files_set))
    total_images = len(image_files)
    
    if total_images == 0:
        print(f"❌ Không tìm thấy ảnh trong thư mục: {image_folder}")
        return
    
    # Phân tích aspect ratio và shot type của tất cả ảnh
    print("\n🔍 Phân tích kích thước ảnh...")
    if analyze_shot_type:
        print("🎬 Đang phân tích shot type (bối cảnh/nhân vật)...")
        image_info_list = analyze_images_with_context(image_files, analyze_shot_type_enabled=True)
    else:
        image_info_list = analyze_image_aspect_ratios(image_files)
    
    # Tính toán kích thước trang tối ưu dựa trên ảnh đầu vào
    if auto_page_size:
        print("📐 Tính toán kích thước trang tối ưu từ ảnh đầu vào...")
        page_size = calculate_optimal_page_size(image_info_list, target_dpi=target_dpi)
    else:
        print("📐 Sử dụng kích thước trang mặc định (A4)...")
        page_size = {
            'width': int(8.5 * target_dpi),
            'height': int(11 * target_dpi),
            'aspect': 8.5/11,
            'scale_factor': 100 / (8.5 * target_dpi),
            'avg_image_size': 'N/A',
            'description': 'Fixed A4'
        }
    
    # 🆕 Single page mode: Bỏ giới hạn chiều cao
    if panels_per_page >= total_images:  # Nếu panels_per_page = số ảnh → Single page mode
        page_size['height'] = page_size['width'] * 20  # Chiều cao rất lớn
        page_size['coord_height'] = page_size.get('coord_width', 100) * 20
        page_size['aspect'] = page_size['width'] / page_size['height']
        print(f"📄 Single page mode: Bỏ giới hạn chiều cao (tạo 1 trang dài)")
    
    # Thống kê orientation
    landscape_count = sum(1 for info in image_info_list if info['orientation'] == 'landscape')
    portrait_count = sum(1 for info in image_info_list if info['orientation'] == 'portrait')
    square_count = sum(1 for info in image_info_list if info['orientation'] == 'square')
    
    # Thống kê shot type (nếu có)
    if analyze_shot_type:
        wide_count = sum(1 for info in image_info_list if info.get('shot_type') == 'wide')
        medium_count = sum(1 for info in image_info_list if info.get('shot_type') == 'medium')
        closeup_count = sum(1 for info in image_info_list if info.get('shot_type') == 'close_up')
        extreme_closeup_count = sum(1 for info in image_info_list if info.get('shot_type') == 'extreme_close_up')
    
    print("=" * 80)
    print(f"📚 TẠO COMIC BOOK TỰ ĐỘNG - ADAPTIVE LAYOUT")
    print("=" * 80)
    print(f"📂 Thư mục ảnh: {image_folder}")
    print(f"🖼️  Tổng số ảnh: {total_images}")
    print(f"📏 Kích thước trang: {page_size['width']}x{page_size['height']}px ({page_size['description']})")
    print(f"   Trung bình ảnh đầu vào: {page_size['avg_image_size']}")
    print(f"📊 Phân loại:")
    print(f"   ➡️  Nằm ngang: {landscape_count} ảnh")
    print(f"   ⬆️  Đứng dọc: {portrait_count} ảnh")
    print(f"   ◼️  Vuông: {square_count} ảnh")
    
    if analyze_shot_type:
        print(f"🎬 Shot Type:")
        print(f"   🌄 Wide shot: {wide_count} ảnh (panel lớn)")
        print(f"   🎭 Medium shot: {medium_count} ảnh (panel trung bình)")
        print(f"   👤 Close-up: {closeup_count} ảnh (panel nhỏ)")
        print(f"   🔍 Extreme close-up: {extreme_closeup_count} ảnh (panel nhỏ nhất)")
    
    print(f"📄 Số khung/trang: {panels_per_page}")
    print(f"📐 Xác suất đường chéo: {diagonal_prob * 100}%")
    print(f"⚙️  Chế độ Adaptive: {'BẬT' if adaptive_layout else 'TẮT'}")
    print(f"🎬 Phân tích Shot Type: {'BẬT' if analyze_shot_type else 'TẮT'}")
    print("-" * 80)
    
    page_num = 1
    image_idx = 0
    output_paths = []
    
    while image_idx < total_images:
        print(f"\n📄 Đang tạo trang {page_num}...")
        
        # Xác định số panels cho trang này
        remaining_images = total_images - image_idx
        
        # Điều chỉnh số panels dựa trên số ảnh còn lại
        if remaining_images <= 2:
            # Nếu còn 1-2 ảnh, tạo 2 panels để tránh full trang
            num_panels = 2
        elif remaining_images == 3:
            # Nếu còn 3 ảnh, tạo 3 panels
            num_panels = 3
        else:
            # 🆕 FIX: Single page mode vs Normal mode
            if panels_per_page > 7:
                # Single page mode: Dùng chính xác số panels yêu cầu
                num_panels = min(panels_per_page, remaining_images)
            else:
                # Normal mode: Random trong khoảng hợp lệ
                min_val = max(4, panels_per_page - 1)
                max_val = min(7, panels_per_page + 1)
                num_panels = min(random.randint(min_val, max_val), remaining_images)
        
        # Lấy thông tin các ảnh cho trang này
        page_image_info = image_info_list[image_idx:image_idx + num_panels]
        
        # [FIX] Dùng coordinate system động từ page_size
        coord_w = page_size.get('coord_width', 100)
        coord_h = page_size.get('coord_height', 160)
        
        # 🆕 Single page mode: Tăng coord_h theo số panels để mỗi panel đủ lớn
        if panels_per_page >= total_images and num_panels > 7:
            # Mỗi panel cần ít nhất 200 units cao để đẹp và dễ đọc
            min_height_per_panel = 200
            required_height = num_panels * min_height_per_panel
            coord_h = max(coord_h, required_height)
            print(f"   📏 Adjusted coord_h = {coord_h} ({num_panels} panels × {min_height_per_panel})")
        
        # Tạo layout thích ứng với kích thước ảnh
        if adaptive_layout:
            panels = create_adaptive_layout(
                page_image_info,
                width=coord_w,
                height=coord_h,
                diagonal_probability=diagonal_prob,
                max_diagonal_angle=12,
                force_aspect_matched=True
            )
        else:
            panels = create_page_layout(num_panels=num_panels, width=coord_w, height=coord_h, diagonal_probability=diagonal_prob, max_diagonal_angle=12)

        # Safety gate: nếu layout có panel lỗi (self-intersection/degenerate), fallback layout ổn định.
        valid_panels = []
        for p in panels:
            try:
                x, y, w, h = p.get_bounds()
                if w < 6 or h < 6:
                    continue
                if not p.is_simple():
                    continue
                valid_panels.append(p)
            except Exception:
                continue

        min_expected = max(1, int(num_panels * 0.7))
        if len(valid_panels) < min_expected:
            print(f"⚠️  Layout trang {page_num} không ổn định ({len(valid_panels)}/{num_panels}), fallback structured layout")
            panels = create_structured_layout(num_panels=num_panels, width=coord_w, height=coord_h)
        else:
            panels = valid_panels
        
        # [FIX] SMART PANEL ASSIGNMENT: Match ảnh với panel theo ORIENTATION
        # Tạo list ảnh cho trang này với index gốc
        page_images = []
        for i in range(num_panels):
            if image_idx + i < total_images:
                img_info = image_info_list[image_idx + i]
                page_images.append({
                    'info': img_info,
                    'index': image_idx + i,
                    'weight': img_info.get('panel_weight', 1.0)
                })
        
        # Phân loại panels và images theo orientation
        panels_with_info = []
        for p in panels:
            x, y, w, h = p.get_bounds()
            panel_aspect = w / h
            if panel_aspect > 1.2:
                panel_orientation = 'landscape'
            elif panel_aspect < 0.8:
                panel_orientation = 'portrait'
            else:
                panel_orientation = 'square'
            panels_with_info.append({
                'panel': p,
                'bounds': (x, y, w, h),
                'aspect': panel_aspect,
                'orientation': panel_orientation,
                'area': w * h
            })
        
        # [FIX] MATCHING THÔNG MINH: Ảnh NGANG → Panel NGANG, ảnh DỌC → Panel DỌC
        image_panel_pairs = []
        used_panels = set()
        
        # Pass 1: Match ảnh với panel cùng orientation
        for img_data in page_images:
            img_orientation = img_data['info']['orientation']
            img_aspect = max(0.05, img_data['info'].get('aspect', 1.0))
            best_panel = None
            best_score = float('-inf')
            best_panel_idx = -1
            
            for idx, panel_data in enumerate(panels_with_info):
                if idx in used_panels:
                    continue
                
                # Score ưu tiên panel có aspect gần ảnh gốc, sau đó mới tới orientation/area.
                panel_aspect = max(0.05, panel_data['aspect'])
                aspect_delta = abs((img_aspect / panel_aspect) - 1.0)
                aspect_score = 100.0 - (aspect_delta * 100.0)

                orientation_bonus = 10 if panel_data['orientation'] == img_orientation else -10
                area_score = panel_data['area'] * 0.001  # nhẹ, chỉ dùng tie-break

                score = aspect_score + orientation_bonus + area_score
                
                if score > best_score:
                    best_score = score
                    best_panel = panel_data
                    best_panel_idx = idx
            
            if best_panel:
                image_panel_pairs.append((img_data, best_panel['panel'], best_panel['bounds']))
                used_panels.add(best_panel_idx)
        
        # [FIX] KHÔNG SORT LẠI - Giữ nguyên thứ tự đã match để tránh đảo lộn
        # (Đã match theo orientation + area, không cần sort lại)
        
        # Gán ảnh vào các panels (đã được matched)
        assigned = 0
        for img_data, panel, panel_bounds in image_panel_pairs:
            img_info = img_data['info']
            img_original_idx = img_data['index']
            image_path = img_info['path']
            fitted_image = fit_image_to_panel(image_path, panel_bounds, use_smart_crop=use_smart_crop)
            
            if fitted_image is not None:
                panel.image = fitted_image
                assigned += 1
                
                # Hiển thị thông tin chi tiết
                orientation_icon = {
                    'landscape': '➡️',
                    'portrait': '⬆️',
                    'square': '◼️'
                }.get(img_info['orientation'], '🖼️')
                
                panel_w, panel_h = panel_bounds[2], panel_bounds[3]
                panel_area = panel_w * panel_h
                panel_orientation = 'ngang' if panel_w > panel_h * 1.2 else ('dọc' if panel_h > panel_w * 1.2 else 'vuông')
                
                shot_info = ""
                weight_info = ""
                if analyze_shot_type and 'shot_type' in img_info:
                    shot_icon = {
                        'wide': '🌄',
                        'medium': '🎭',
                        'close_up': '👤',
                        'extreme_close_up': '🔍'
                    }.get(img_info['shot_type'], '')
                    shot_info = f" {shot_icon} {img_info['shot_type'].upper()}"
                    weight_info = f" [W:{img_data['weight']:.1f}→Area:{panel_area:.0f}]"
                
                # [DEBUG] Show matching info
                img_orient = img_info['orientation']
                match_status = '✅' if img_orient == panel_orientation or (img_orient == 'square' and panel_orientation == 'vuông') or (img_orient == 'landscape' and panel_orientation == 'ngang') or (img_orient == 'portrait' and panel_orientation == 'dọc') else '❌ MISMATCH'
                
                print(f"  ✓ Ảnh {img_original_idx + 1}/{total_images}: {image_path.name} {orientation_icon}{shot_info}{weight_info}")
                print(f"    ↪ Panel {assigned} ({panel_orientation}) - Img aspect: {img_info['aspect']:.2f} → Panel aspect: {panel_w/panel_h:.2f} {match_status}")
        
        # Tiến image_idx theo số ảnh ĐÃ LẤY cho trang này (dù assign thành công hay không)
        # Tránh ảnh bị xử lý lại ở trang tiếp theo gây "dư ảnh"
        images_attempted = len(page_images)
        image_idx += max(assigned, images_attempted)
        
        # Vẽ trang với kích thước tối ưu
        # 🆕 Tính lại coord_h nếu là single page mode (để match với panels đã tạo)
        actual_coord_w = page_size.get('coord_width', 100)
        actual_coord_h = page_size.get('coord_height', 140)
        
        if panels_per_page >= total_images and len(panels) > 7:
            # Single page mode: Tăng coord_h theo số panels
            min_height_per_panel = 200
            required_height = len(panels) * min_height_per_panel
            actual_coord_h = max(actual_coord_h, required_height)
        
        # Tính figsize từ coord system (không phải từ page_size cố định)
        # Giữ aspect ratio: fig_height/fig_width = coord_h/coord_w
        fig_width = page_size['width'] / 100  # Generate an effectively bigger size in inches to reduce blurriness
        fig_height = fig_width * (actual_coord_h / actual_coord_w)  # Scale theo coord ratio
        
        # [FIX] Dùng coordinate system động
        coord_w = actual_coord_w
        coord_h = actual_coord_h
        
        # Tạo ảnh comic lớn/rõ nét hơn để tránh bị mờ
        fig, ax = plt.subplots(1, figsize=(fig_width, fig_height), dpi=300)
        ax.set_xlim(0, coord_w)
        ax.set_ylim(0, coord_h)
        ax.set_aspect('equal')
        
        for panel in panels:
            # Bỏ qua panel không có ảnh để tránh khung trắng thừa
            if not hasattr(panel, 'image') or panel.image is None:
                continue
            panel.draw_with_image(
                ax,
                gap=1.0,
                show_border=True,
                draw_speech_bubbles_outside=draw_speech_bubbles_outside,
                enable_perspective_warp=enable_perspective_warp,
            )
        
        # Thêm số trang (position theo coordinate system)
        ax.text(coord_w/2, 2, f'Page {page_num}', ha='center', va='bottom', 
               fontsize=10, color='gray', style='italic')
        
        plt.axis('off')
        plt.tight_layout(pad=0)
        
        # Lưu trang
        output_path = os.path.join(output_folder, f'page_{page_num:03d}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"  💾 Đã lưu: {output_path}")
        output_paths.append(output_path)
        page_num += 1
        
        # 🆕 Single page mode: Dừng sau page 1 (không phân trang)
        if panels_per_page >= total_images:
            print(f"📄 Single page mode: Dừng sau trang 1 (đã ghép tất cả ảnh)")
            break
    
    print("\n" + "=" * 80)
    print(f"✅ HOÀN THÀNH!")
    print(f"📖 Đã tạo {page_num - 1} trang")
    print(f"🖼️  Đã xử lý {image_idx} / {total_images} ảnh")
    print(f"📁 Kết quả lưu tại: {output_folder}/")
    print("=" * 80)
    
    return output_paths

def create_sample_images(output_folder="images", num_images=10):
    """
    Tạo ảnh mẫu để test (nếu chưa có ảnh)
    """
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"🎨 Đang tạo {num_images} ảnh mẫu...")
    
    for i in range(1, num_images + 1):
        # Tạo ảnh màu ngẫu nhiên với text
        fig, ax = plt.subplots(1, figsize=(6, 4))
        
        # Background màu ngẫu nhiên
        color = np.random.rand(3,)
        ax.set_facecolor(color)
        
        # Text số thứ tự
        ax.text(0.5, 0.5, f'{i:03d}', ha='center', va='center',
               fontsize=80, color='white', weight='bold',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        # Thêm random shapes
        for _ in range(5):
            x, y = np.random.rand(2)
            size = np.random.uniform(0.1, 0.3)
            shape_color = np.random.rand(3,)
            circle = plt.Circle((x, y), size, color=shape_color, alpha=0.5)
            ax.add_patch(circle)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        output_path = os.path.join(output_folder, f'{i:03d}.png')
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
    
    print(f"✓ Đã tạo {num_images} ảnh tại: {output_folder}/")


if __name__ == "__main__":
    # Bước 1: Tạo ảnh mẫu (nếu chưa có)
    sample_folder = "images"
    if not os.path.exists(sample_folder) or len(list(PathLib(sample_folder).glob('*.png'))) == 0:
        create_sample_images(sample_folder, num_images=25)
    
    # Bước 2: Tạo comic book với ADAPTIVE LAYOUT + SMART CROP
    print("\n")
    
    # Tùy chọn: Bật/tắt smart crop
    USE_SMART_CROP = True  # Đổi thành True để bật phát hiện text/người
    
    if USE_SMART_CROP and not SMART_CROP_AVAILABLE:
        print("⚠️  Smart crop được yêu cầu nhưng không khả dụng!")
        print("📦 Cài đặt: pip install opencv-python")
        print("📦 (Tùy chọn) pip install easyocr ultralytics")
        print("")
    
    create_comic_book_from_images(
        image_folder=sample_folder,
        output_folder="output_comic",
        panels_per_page=5,       # Trung bình 5 khung/trang
        diagonal_prob=0.3,       # 30% đường chéo
        adaptive_layout=True,    # BẬT chế độ thích ứng!
        use_smart_crop=USE_SMART_CROP  # Smart crop (phát hiện text/người)
    )
