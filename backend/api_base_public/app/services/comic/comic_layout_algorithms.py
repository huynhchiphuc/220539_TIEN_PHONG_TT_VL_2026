import random
import math
import hashlib
import numpy as np
from typing import List, Tuple, Callable, Optional, Dict, Any
from uuid import uuid4

from app.services.comic.comic_geometry import Point, Polygon, _make_gutter_quad
from app.services.comic.comic_utils import (
    _classify_ar, 
    _build_ar_strategy,
    PANEL_MIN_ASPECT,
    PANEL_MAX_ASPECT,
    calculate_adaptive_diagonal_angle
)
def create_dynamic_grid_layout(image_aspects, width=100, height=160, jitter_factor=8.0, margin=2.5, rng=None):
    """
    🆕 TẠO LAYOUT DỰA TRÊN GRID - KHÔNG TẠO HÌNH TAM GIÁC
    Chia trang thành các hàng, mỗi hàng có số cột tương ứng.
    Mỗi panel luôn là tứ giác (quadrilateral).
    """
    num_panels = len(image_aspects)
    if num_panels == 0:
        return []

    rng = rng or random

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
    
    # Bước 2: Tạo boundary lines cho Y (THẲNG - không jitter)
    y_lines = [margin]
    for i in range(1, num_rows):
        y_lines.append(margin + (i / num_rows) * (height - 2 * margin))
    y_lines.append(height - margin)

    # Bước 3: Tạo boundary x_points cho từng LINE (THẲNG - không jitter)
    all_boundaries_x = []
    
    # Tính tỉ lệ cột cho từng row 
    row_starts = [0]
    for n in rows_config[:-1]:
        row_starts.append(row_starts[-1] + n)
        
    for i in range(num_rows + 1):
        x_points = [margin]
        # Nếu đang ở đỉnh hoặc đáy, dùng config của row kề cạnh
        row_params_idx = i if i < num_rows else num_rows - 1
        cols_in_layer = rows_config[row_params_idx]
        start_img_idx = row_starts[row_params_idx]
        
        if cols_in_layer > 1:
            # Lấy list aspect ratio của row đó
            aspects = []
            for k in range(cols_in_layer):
                if start_img_idx + k < len(image_aspects):
                    aspects.append(max(0.3, image_aspects[start_img_idx + k].get('aspect', 1.0)))
                else:
                    aspects.append(1.0)
                    
            total_aspect = sum(aspects) or 1.0
            
            cur_weight = 0.0
            for j in range(cols_in_layer - 1):
                cur_weight += aspects[j]
                base_x = margin + (cur_weight / total_aspect) * (width - 2 * margin)
                # Không jitter - giữ thẳng
                x_points.append(float(np.clip(base_x, margin + 4, width - margin - 4)))
                
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

def create_adaptive_layout(image_aspects, width=100, height=140, diagonal_probability=0.3, max_diagonal_angle=12, force_aspect_matched=False, deterministic_seed=None):
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

    def _build_stable_seed(items):
        payload = []
        for item in items:
            payload.append({
                'aspect': round(float(item.get('aspect', 1.0)), 4),
                'orientation': str(item.get('orientation', 'square')),
                'type': str(item.get('type', 'unknown')),
            })
        digest = hashlib.sha256(repr(payload).encode('utf-8')).hexdigest()
        return int(digest[:8], 16)

    stable_seed = deterministic_seed if deterministic_seed is not None else _build_stable_seed(image_aspects)

    # ── Ưu tiên #1: AR-Driven Subdivision (Data-Driven Slicing) ────────────
    # Thuật toán phân tích AR từng ảnh → chiến lược nhóm hàng → cắt đệ quy.
    try:
        ar_panels = create_ar_driven_subdivision_layout(
            image_aspects=image_aspects,
            width=width,
            height=height,
            gutter=max(1.5, min(4.0, width * 0.025)),   # ~2.5% chiều rộng
            tilt_deg=max_diagonal_angle * 0.25,           # góc nhẹ (25% góc tối đa)
        )
        if ar_panels and len(ar_panels) >= max(1, num_panels - 1):
            print(f"✅ AR-Driven layout: {len(ar_panels)} panels (target={num_panels})")
            return ar_panels[:num_panels]
    except Exception as exc:
        print(f"⚠️ AR-Driven layout failed, fallback to recursive: {exc}")

    # ── Ưu tiên #2: Recursive Subdivision ────────────────────────────────────
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
        print(f"🎨 Using AR-LOCKED grid layout (no jitter, seed={stable_seed})")
        return create_dynamic_grid_layout(
            image_aspects,
            width=width,
            height=height,
            jitter_factor=0,  # Không jitter - giữ thẳng
            margin=4,
            rng=random.Random(stable_seed),
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
        # Không dùng đường chéo - luôn cắt thẳng
        use_diagonal = False
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
        
        # Không xoay - giữ hình chữ nhật thẳng
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

        # Cắt THẲNG: t1 == t2, không jitter, không tilt
        t1 = max(0.18, min(0.82, split_ratio))
        t2 = t1  # Đường cắt thẳng vuông góc

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

def create_ar_driven_subdivision_layout(
    image_aspects: list,
    width: float = 100.0,
    height: float = 160.0,
    gutter: float = 2.5,
    tilt_deg: float = 3.0,
) -> list:
    """
    Thuật toán AR-Driven Recursive Subdivision - ĐỘ NGHIÊNG THỰC SỰ.

    Giai đoạn 1 - _classify_ar: Portrait/Landscape/Square.
    Giai đoạn 2 - _build_ar_strategy: nhóm hàng theo AR.
    Giai đoạn 3 - Cắt đệ quy với ĐƯỜNG CẮT NGHIÊNG (tilted cuts):
      • Đường ngang (giữa các hàng): y_left ≠ y_right → hình thang.
      • Đường dọc (giữa các cột): x_top ≠ x_bot → hình thang.
      • Panels liền kề CHIA SẺ cùng đường cắt nghiêng (gutter là khoảng trống).
    """
    if not image_aspects:
        return []

    rng = random.Random()
    # Đảm bảo tilt đủ lớn để thấy rõ (tối thiểu 2°)
    eff_tilt = max(2.0, float(tilt_deg))
    tilt_rad = np.deg2rad(eff_tilt)

    # ── Giai đoạn 2: Xây chiến lược nhóm ──────────────────────────────────
    rows_groups = _build_ar_strategy(image_aspects)
    num_rows = len(rows_groups)

    # ── Phân bổ chiều cao cho từng hàng theo AR-weight ─────────────────────
    def _row_weight(group):
        if not group:
            return 1.0
        avg_ar = sum(g.get('aspect', 1.0) for g in group) / len(group)
        # Để các panel trong dòng giữ được tỉ lệ avg_ar, 
        # chiều cao của dòng phải tỉ lệ nghịch với SỐ_CỘT * avg_ar
        return 1.0 / (len(group) * max(0.3, avg_ar))

    row_weights = [_row_weight(g) for g in rows_groups]
    total_row_w = sum(row_weights) or 1.0
    
    # Chiều cao tự nhiên mong muốn để KHÔNG dập nát hay bóp chóp tỷ lệ gốc
    ideal_usable_h = total_row_w * width
    
    # Cho phép hình bị giãn ra tối đa 15% để ăn bớt viền trắng
    max_usable_h = ideal_usable_h * 1.15
    
    # Chiều cao thực tế của frame giấy được cung cấp
    target_usable_h = height - (num_rows - 1) * gutter
    
    # Nếu trang có chiều dài QUÁ CAO so với tổng kết cấu hình, ta không căng khung ra nữa!
    # Tránh tình trạng giãn ngược ảnh ngang thành khung dọc.
    if target_usable_h > max_usable_h:
        actual_usable_h = max_usable_h
        vertical_padding = (target_usable_h - max_usable_h) / 2.0
        start_y = vertical_padding
    else:
        actual_usable_h = target_usable_h
        start_y = 0.0

    row_heights = [max(8.0, (w / total_row_w) * actual_usable_h) for w in row_weights]

    # [FIX] Căn chỉnh Y-up: 
    # Hệ toạ độ bắt đầu từ y=0 ở DƯỚI CÙNG lên y=height ở TRÊN CÙNG.
    # Để group đầu tiên nằm ở TRÊN CÙNG, ta cần phải nối nó ở cuối vòng lặp (với y lớn nhất).
    # Do đó, tải ngược danh sách group và chiều cao trước khi dựng hình!
    rows_groups = list(reversed(rows_groups))
    row_heights = list(reversed(row_heights))

    # ── Tạo HORIZONTAL BOUNDARIES (đường ngang THẲNG) ──────────────────────
    # h_boundaries[i] = (y_left, y_right) – y tại x=0 và x=width (luôn bằng nhau = thẳng)
    h_boundaries = [(start_y, start_y)]

    current_y = start_y
    for row_idx, row_h in enumerate(row_heights):
        current_y += row_h
        if row_idx < num_rows - 1:
            y_mid = current_y + gutter / 2.0
            y_mid = float(np.clip(y_mid, 4.0, height - 4.0))
            # Đường biên THẲNG (y_left == y_right)
            h_boundaries.append((y_mid, y_mid))
            current_y += gutter
        else:
            h_boundaries.append((current_y, current_y))

    # Helper: y tại x cho một boundary (y_left, y_right) - luôn bằng nhau nên trả về y_left
    def _y_at(bnd, x):
        y_l, y_r = bnd
        t = float(x) / float(width) if width > 1e-6 else 0.0
        return y_l + (y_r - y_l) * t

    # ── Xây dựng panels từng hàng ──────────────────────────────────────────
    panels_out = []

    for row_idx, group in enumerate(rows_groups):
        num_cols = len(group)
        top_bnd = h_boundaries[row_idx]
        bot_bnd = h_boundaries[row_idx + 1]

        if num_cols == 1:
            # Full-width → hình CHỮ NHẬT thẳng
            y_top = _y_at(top_bnd, 0.0)
            y_bot = _y_at(bot_bnd, 0.0)
            verts = np.array([
                [0.0,   y_top],
                [width, y_top],
                [width, y_bot],
                [0.0,   y_bot],
            ])
            p = Polygon(verts)
            p.image = None
            orig_idx = group[0].get('_orig_idx', row_idx)
            panels_out.append((p, orig_idx))

        else:
            # Phân bổ chiều rộng theo AR
            col_weights = [max(0.3, g.get('aspect', 1.0)) for g in group]
            total_col_w = sum(col_weights) or 1.0
            usable_w = width - (num_cols - 1) * gutter
            col_widths = [max(5.0, (cw / total_col_w) * usable_w) for cw in col_weights]

            # ── VERTICAL BOUNDARIES (đường dọc THẲNG trong hàng) ───────────
            # v_boundaries[j] = (x, x) – luôn thẳng (x_top == x_bot)
            v_boundaries = [(0.0, 0.0)]

            cur_x = 0.0
            for col_idx in range(num_cols - 1):
                cur_x += col_widths[col_idx]
                x_mid = float(np.clip(cur_x + gutter / 2.0, 3.0, width - 3.0))
                # Đường cắt THẲNG (x_top == x_bot)
                v_boundaries.append((x_mid, x_mid))
                cur_x += gutter

            v_boundaries.append((width, width))

            # Xây panel từ corners chính xác
            for col_idx in range(num_cols):
                lft = v_boundaries[col_idx]      # (x_top_left,  x_bot_left)
                rgt = v_boundaries[col_idx + 1]  # (x_top_right, x_bot_right)

                x_tl, x_bl = lft[0], lft[1]
                x_tr, x_br = rgt[0], rgt[1]

                y_tl = _y_at(top_bnd, x_tl)
                y_tr = _y_at(top_bnd, x_tr)
                y_bl = _y_at(bot_bnd, x_bl)
                y_br = _y_at(bot_bnd, x_br)

                verts = np.array([
                    [x_tl, y_tl],  # TL
                    [x_tr, y_tr],  # TR
                    [x_br, y_br],  # BR
                    [x_bl, y_bl],  # BL
                ])
                p = Polygon(verts)
                p.image = None
                img_info = group[col_idx]
                panels_out.append((p, img_info.get('_orig_idx', col_idx)))

    # Trả về panels theo đúng thứ tự mảng gốc (orig_idx) để mapping 1-1 không bị sai lệch
    panels_out.sort(key=lambda item: item[1])
    num_out = min(len(panels_out), len(image_aspects))
    return [p for p, _ in panels_out[:num_out]]

def create_auto_frame_layout(
    target_count: int,
    coord_w: float = 1000.0,
    coord_h: float = 1778.0,
    diagonal_prob: float = 0.3,
    gutter: float = 8.0,
    seed: int = None,
) -> list:
    """
    Tạo layout panel cho Auto-Frames (không cần ảnh đầu vào).

    Trích xuất từ generate_auto_frames() trong comic.py để tránh code trùng lặp.
    Thuật toán: Recursive polygon subdivision với đường cắt nghiêng (diagonal_prob).

    Args:
        target_count:  số panel cần tạo
        coord_w/h:     không gian toạ độ (pixel)
        diagonal_prob: xác suất / cường độ đường nghiêng (0..1)
        gutter:        độ rộng rãnh giữa panel (px trong coord space)
        seed:          random seed (None = random thực sự)

    Returns:
        list[list[tuple[float, float]]]: mỗi phần tử là danh sách (x, y)
        vertices trong coord space [0..coord_w] x [0..coord_h] cho 1 panel.
    """
    import math as _math
    from dataclasses import dataclass as _dc

    _rng = random.Random(seed)
    _min_panel_w = max(80.0, coord_w * 0.12)
    _min_panel_h = max(80.0, coord_h * 0.12)
    _ideal_aspect = max(0.55, min(2.1, coord_w / max(1e-6, coord_h)))
    _randomness_base = 0.0  # Không dùng randomness dựa trên diagonal_prob nữa

    @_dc
    class _Pt:
        x: float
        y: float

    @_dc
    class _Poly:
        vertices: list

        def bbox(self):
            xs = [p.x for p in self.vertices]
            ys = [p.y for p in self.vertices]
            return min(xs), min(ys), max(xs), max(ys)

        def area(self):
            pts = self.vertices
            total = 0.0
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                total += p1.x * p2.y - p2.x * p1.y
            return abs(total) * 0.5

    @_dc
    class _Tree:
        polygon: object
        left: object = None
        right: object = None

    def _lerp(a, b, t):
        return _Pt(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)

    def _clamp(pt):
        return _Pt(max(2.0, min(coord_w - 2.0, pt.x)),
                   max(2.0, min(coord_h - 2.0, pt.y)))

    def _offset_edge(a, b, dist):
        dx, dy = b.x - a.x, b.y - a.y
        length = _math.hypot(dx, dy)
        if length < 1e-6:
            return a, b, a, b
        nx, ny = -dy / length, dx / length
        return (_clamp(_Pt(a.x - nx * dist, a.y - ny * dist)),
                _clamp(_Pt(b.x - nx * dist, b.y - ny * dist)),
                _clamp(_Pt(a.x + nx * dist, a.y + ny * dist)),
                _clamp(_Pt(b.x + nx * dist, b.y + ny * dist)))

    def _can_split(poly):
        x0, y0, x1, y1 = poly.bbox()
        return ((x1 - x0) >= _min_panel_w * 1.3 and
                (y1 - y0) >= _min_panel_h * 1.3 and
                poly.area() >= _min_panel_w * _min_panel_h)

    def _slice(poly, ratio=0.5, rand=0.5, axis=None):
        v0, v1, v2, v3 = poly.vertices
        x0, y0, x1, y1 = poly.bbox()
        bw, bh = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        if axis is None:
            if bw > bh * 1.25:    axis = 'vertical'
            elif bh > bw * 1.25:  axis = 'horizontal'
            else:                 axis = 'horizontal' if _rng.random() < 0.5 else 'vertical'
        ratio = max(0.22, min(0.78, ratio))
        # Cắt THẲNG: t1 == t2, không jitter, không tilt
        t1 = max(0.18, min(0.82, ratio))
        t2 = t1  # Đường cắt thẳng vuông góc
        if axis == 'horizontal':
            lc, rc = _lerp(v0, v3, t1), _lerp(v1, v2, t2)
            tl, tr, bl, br = _offset_edge(lc, rc, gutter * 0.5)
            return _Poly([v0, v1, tr, tl]), _Poly([bl, br, v2, v3])
        tc, bc = _lerp(v0, v1, t1), _lerp(v3, v2, t2)
        at, ab, bt2, bb = _offset_edge(tc, bc, gutter * 0.5)
        return _Poly([v0, bt2, bb, v3]), _Poly([at, v1, v2, ab])

    def _badness(poly):
        x0, y0, x1, y1 = poly.bbox()
        w, h = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        ar = w / h
        s = abs(_math.log(max(1e-6, ar / _ideal_aspect)))
        if ar < 0.45:   s += (0.45 - ar) * 6.0
        if ar > 2.6:    s += (ar - 2.6) * 3.0
        if w < _min_panel_w: s += ((_min_panel_w - w) / _min_panel_w) * 2.0
        if h < _min_panel_h: s += ((_min_panel_h - h) / _min_panel_h) * 2.0
        return s

    def _quota_pair(total, rand):
        if total <= 2:
            return 1, max(1, total - 1)
        rand = max(0.0, min(1.0, rand))
        spread = max(1.0, total * (0.10 + 0.16 * rand))
        left = int(round(total / 2.0 + _rng.uniform(-spread, spread)))
        left = max(1, min(total - 1, left))
        if total >= 5 and _rng.random() < (0.20 + 0.45 * rand):
            swing = _rng.randint(-max(1, int(total * (0.08 + 0.10 * rand))),
                                  max(1, int(total * (0.08 + 0.10 * rand))))
            left = max(1, min(total - 1, left + swing))
        return left, total - left

    def _best_split(poly, lq, rq, rand):
        x0, y0, x1, y1 = poly.bbox()
        bw, bh = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        target = lq / max(1, lq + rq)
        if bw > bh * 1.2:   axes = ['vertical', 'horizontal']
        elif bh > bw * 1.2: axes = ['horizontal', 'vertical']
        else:               axes = ['horizontal', 'vertical']
        candidates = []
        samples = 10 + int(10 * rand)
        for axis in axes:
            for _ in range(samples):
                r = max(0.20, min(0.80, target + _rng.uniform(-0.12, 0.12) * rand))
                try:
                    lp, rp = _slice(poly, ratio=r, rand=rand, axis=axis)
                except Exception:
                    continue
                al, ar_ = max(1e-6, lp.area()), max(1e-6, rp.area())
                bal = abs(al / (al + ar_) - target) * 8.0
                qp = (3.0 if lq > 1 and not _can_split(lp) else 0.0) + \
                     (3.0 if rq > 1 and not _can_split(rp) else 0.0)
                score = bal + _badness(lp) + _badness(rp) + qp
                score += _rng.uniform(0.0, 0.20) * rand
                candidates.append((score, lp, rp))
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        top_k = min(len(candidates), max(1, 2 + int(4 * rand)))
        w_ = [1.0 / (i + 1) for i in range(top_k)]
        return _rng.choices(candidates[:top_k], weights=w_, k=1)[0][1:]

    def _leaves(node, out):
        if node.left is None and node.right is None:
            out.append(node)
            return
        if node.left:  _leaves(node.left, out)
        if node.right: _leaves(node.right, out)

    def _subdivide(node, count, rand):
        if count <= 1 or not _can_split(node.polygon):
            return
        lq, rq = _quota_pair(count, rand)
        best = _best_split(node.polygon, lq, rq, rand)
        if best is None:
            return
        lp, rp = best
        node.left, node.right = _Tree(lp), _Tree(rp)
        if count == 2:
            return
        nr = max(0.15, min(1.0, rand * (0.92 + _rng.uniform(-0.06, 0.06))))
        _subdivide(node.left, lq, nr)
        _subdivide(node.right, rq, nr)

    def _largest_leaf(root):
        ls = []
        _leaves(root, ls)
        cands = [l for l in ls if _can_split(l.polygon)]
        return max(cands, key=lambda n: n.polygon.area()) if cands else None

    root_poly = _Poly([
        _Pt(4.0, 4.0), _Pt(coord_w - 4.0, 4.0),
        _Pt(coord_w - 4.0, coord_h - 4.0), _Pt(4.0, coord_h - 4.0),
    ])
    root = _Tree(root_poly)
    # Dùng page_rand = 0.5 cố định → chia panel đều (không lệch ngẫu nhiên)
    page_rand = 0.5
    _subdivide(root, max(1, target_count), page_rand)

    leaf_list = []
    _leaves(root, leaf_list)

    while len(leaf_list) < target_count:
        cand = _largest_leaf(root)
        if cand is None:
            break
        best = _best_split(cand.polygon, 1, 1, page_rand)
        if best is None:
            break
        cand.left, cand.right = _Tree(best[0]), _Tree(best[1])
        leaf_list = []
        _leaves(root, leaf_list)

    return [
        [(v.x, v.y) for v in node.polygon.vertices]
        for node in leaf_list[:target_count]
    ]

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
    return create_grid_layout(num_panels=num_panels, width=width, height=height)

