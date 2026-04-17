import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Flask threading
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import itertools
import math
import random
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import os
import re
import hashlib
from pathlib import Path as PathLib

# Giới hạn kích thước output để giữ chất lượng ở mức web-friendly (~FullHD).
MAX_OUTPUT_LONG_SIDE = int(os.getenv("COMIC_MAX_LONG_SIDE", "1920"))

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



from app.services.comic.comic_utils import (
    analyze_image_aspect_ratios,
    analyze_images_with_context,
    calculate_optimal_page_size,
    force_page_aspect_ratio,
    normalize_page_size_for_web,
    fit_image_to_panel,
    _build_ar_strategy
)

from app.services.comic.comic_layout_algorithms import (
    create_page_layout,
    create_auto_frame_layout,
    create_adaptive_layout,
    create_grid_layout,
    create_dynamic_grid_layout,
)
def create_comic_book_from_images(image_folder, output_folder="output_comic", 
                                  panels_per_page=5, diagonal_prob=0.3, adaptive_layout=True,
                                  use_smart_crop=False, reading_direction='ltr', analyze_shot_type=False,
                                  auto_page_size=True, target_dpi=150, classify_characters=False,
                                  aspect_ratio='9:16',
                                  draw_speech_bubbles_outside=True,
                                  enable_perspective_warp=DEFAULT_ENABLE_PERSPECTIVE_WARP,
                                  initial_image_info=None):
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
        aspect_ratio: Tỉ lệ trang mục tiêu (vd: '9:16', '16:9', 'auto')
        draw_speech_bubbles_outside: Có hiển thị bóng thoại nhô ra khỏi khung panel không
        enable_perspective_warp: Có biến dạng phối cảnh ảnh theo khung hay không
    """
    # Tạo thư mục output
    os.makedirs(output_folder, exist_ok=True)
    
    # 2. Phân tích aspect ratio và shot type của tất cả ảnh
    if initial_image_info and len(initial_image_info) > 0:
        print("\nℹ️  Sử dụng thông tin ảnh cấu hình từ JSON (External Metadata)...")
        image_info_list = []
        # Đảm bảo các đường dẫn ảnh là tuyệt đối và validate file tồn tại
        for info in list(initial_image_info):
            # Resolve đường dẫn
            if not os.path.isabs(info['path']):
                info['path'] = os.path.abspath(os.path.join(image_folder, info['path']))

            # Kiểm tra file tồn tại
            if not os.path.exists(info['path']):
                print(f"   ⚠️  Không tìm thấy file từ config: '{os.path.basename(info['path'])}', bỏ qua.")
                continue

            # Bổ sung width/height thực tế nếu chưa có (cần cho calculate_optimal_page_size)
            # GIỮ NGUYÊN aspect từ JSON — người dùng đã cố tình định nghĩa cho layout engine
            if 'width' not in info or 'height' not in info:
                try:
                    with Image.open(info['path']) as _img:
                        _img = ImageOps.exif_transpose(_img)
                        info['width']  = _img.width
                        info['height'] = _img.height
                        # Chỉ bổ sung aspect nếu JSON chưa có, không overwrite
                        if 'aspect' not in info:
                            info['aspect'] = _img.width / max(1, _img.height)
                except Exception as _e:
                    print(f"   ⚠️  Không đọc được '{os.path.basename(info['path'])}': {_e}, bỏ qua.")
                    continue

            # Bổ sung orientation nếu thiếu
            if 'orientation' not in info:
                ar = info.get('aspect', 1.0)
                if ar > 1.2: info['orientation'] = 'landscape'
                elif ar < 0.8: info['orientation'] = 'portrait'
                else: info['orientation'] = 'square'

            # Bổ sung type nếu thiếu (dùng cho layout logic)
            if 'type' not in info:
                from app.services.comic.comic_utils import _classify_ar
                info['type'] = _classify_ar(info.get('aspect', 1.0))

            image_info_list.append(info)

        if not image_info_list:
            print("   ⚠️  Không có ảnh hợp lệ từ config JSON! Fallback sang scan folder...")
            # Fallback: scan folder như chế độ bình thường
            valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
            seen_paths = set()
            image_files_raw = []
            for file in PathLib(image_folder).iterdir():
                if file.suffix.lower() in valid_exts:
                    resolved = file.resolve()
                    key = str(resolved).lower()
                    if key not in seen_paths:
                        seen_paths.add(key)
                        image_files_raw.append(resolved)
            import re as _re
            def _natural_key_fb(p):
                name = PathLib(p).name
                return [int(x) if x.isdigit() else x.lower() for x in _re.split(r'(\d+)', name)]
            image_files_raw = sorted(image_files_raw, key=_natural_key_fb)
            print(f"\n🔍 Phân tích kích thước ảnh (fallback)...")
            if analyze_shot_type:
                image_info_list = analyze_images_with_context(image_files_raw, analyze_shot_type_enabled=True)
            else:
                image_info_list = analyze_image_aspect_ratios(image_files_raw)
        else:
            print(f"📋 Đã load {len(image_info_list)}/{len(initial_image_info)} ảnh hợp lệ từ JSON config")

        image_files = [info['path'] for info in image_info_list]
        total_images = len(image_files)
    else:
        # Lấy danh sách ảnh — loại bỏ trùng lặp
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
        seen_paths = set()
        image_files_list = []
        for file in PathLib(image_folder).iterdir():
            if file.suffix.lower() in valid_exts:
                resolved = file.resolve()
                key = str(resolved).lower()
                if key not in seen_paths:
                    seen_paths.add(key)
                    image_files_list.append(resolved)

        def natural_key(path_obj):
            name = PathLib(path_obj).name
            return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', name)]

        image_files = sorted(image_files_list, key=natural_key)
        total_images = len(image_files)
        
        if total_images == 0:
            print(f"❌ Không tìm thấy ảnh trong thư mục: {image_folder}")
            return
        
        print("\n🔍 Phân tích kích thước ảnh...")
        if analyze_shot_type:
            print("🎬 Đang phân tích shot type (bối cảnh/nhân vật)...")
            image_info_list = analyze_images_with_context(image_files, analyze_shot_type_enabled=True)
        else:
            image_info_list = analyze_image_aspect_ratios(image_files)
    
    # Parse tỉ lệ trang yêu cầu. 'auto' sẽ giữ logic tự động như cũ.
    requested_aspect = str(aspect_ratio or '9:16').strip().lower()
    forced_ratio = None
    if requested_aspect != 'auto':
        matched = re.match(r'^(\d+)\s*:\s*(\d+)$', requested_aspect)
        if matched:
            aw = int(matched.group(1))
            ah = int(matched.group(2))
            if aw > 0 and ah > 0:
                forced_ratio = (aw, ah)

    # Tính toán kích thước trang tối ưu dựa trên ảnh đầu vào
    if auto_page_size:
        print("📐 Tính toán kích thước trang tối ưu từ ảnh đầu vào...")
        page_size = calculate_optimal_page_size(image_info_list, target_dpi=target_dpi)
    else:
        print("📐 Sử dụng kích thước trang mặc định (portrait baseline)...")
        page_size = {
            'width': int(8.5 * target_dpi),
            'height': int(11 * target_dpi),
            'aspect': 8.5/11,
            'scale_factor': 100 / (8.5 * target_dpi),
            'avg_image_size': 'N/A',
            'description': 'Fixed portrait baseline'
        }

    # Nếu có tỉ lệ yêu cầu (mặc định 9:16), ưu tiên ép theo tỉ lệ đó.
    # Khi chọn 'auto', giữ tỉ lệ từ ảnh đầu vào như trước đây.
    if forced_ratio is not None:
        page_size = force_page_aspect_ratio(
            page_size,
            forced_ratio[0],
            forced_ratio[1],
            max_long_side=MAX_OUTPUT_LONG_SIDE,
        )
    else:
        # Giữ tỉ lệ trang theo ảnh đầu vào, chỉ giới hạn kích thước để tối ưu cho web.
        page_size = normalize_page_size_for_web(page_size, max_long_side=MAX_OUTPUT_LONG_SIDE)
    
    if panels_per_page >= total_images:
        print("📄 Single page mode: gom 1 trang nhưng vẫn giữ chiều cao hợp lý")
    
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
    print(f"📐 Tỉ lệ trang yêu cầu: {aspect_ratio}")
    print(f"📐 Xác suất đường chéo: {diagonal_prob * 100}%")
    print(f"⚙️  Chế độ Adaptive: {'BẬT' if adaptive_layout else 'TẮT'}")
    print(f"🎬 Phân tích Shot Type: {'BẬT' if analyze_shot_type else 'TẮT'}")
    print("-" * 80)
    
    page_num = 1
    image_idx = 0
    output_paths = []

    def _build_page_seed(page_number, page_infos):
        payload = [
            (
                int(page_number),
                str(info.get('path', '')),
                round(float(info.get('aspect', 1.0)), 4),
                str(info.get('orientation', 'square')),
            )
            for info in page_infos
        ]
        digest = hashlib.sha256(repr(payload).encode('utf-8')).hexdigest()
        return int(digest[:8], 16)

    def _validate_layout(candidate_panels, expected_count, page_w, page_h):
        """Validate layout để tránh panel chồng lấp, quá mỏng hoặc vượt biên."""
        if not candidate_panels:
            return [], "empty"

        page_area = max(1.0, float(page_w * page_h))
        # Giới hạn diện tích tối thiểu theo số panel để loại các mảnh cực nhỏ.
        min_panel_area = max(page_area * 0.012, page_area / (max(1, expected_count) * 9.5))

        valid = []
        for p in candidate_panels:
            try:
                x, y, w, h = p.get_bounds()
                if w < 6 or h < 6:
                    continue
                if (w * h) < min_panel_area:
                    continue
                # Panel phải nằm trong canvas (cho phép sai số nhỏ do float).
                if x < -0.5 or y < -0.5 or (x + w) > (page_w + 0.5) or (y + h) > (page_h + 0.5):
                    continue
                if not p.is_simple():
                    continue
                valid.append(p)
            except Exception:
                continue

        min_expected = max(1, int(expected_count * 0.7))
        if len(valid) < min_expected:
            return valid, f"insufficient_valid_panels={len(valid)}/{expected_count}"

        # Loại layout có panel đè lên nhau gây rách ảnh/duplicate nội dung.
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                if valid[i].overlaps_with(valid[j], tolerance=0.05):
                    return valid, f"overlap_detected={i}-{j}"

        return valid, None
    
    while image_idx < total_images:
        print(f"\n📄 Đang tạo trang {page_num}...")
        
        # Xác định số panels cho trang này
        remaining_images = total_images - image_idx
        
        # --- LOGIC TÍNH `num_panels` MỚI BẰNG TOÁN HỌC HÀNG (ROW-BASED) ---
        target_panels = max(1, min(int(panels_per_page), remaining_images))
        
        # Test gom hàng với tất cả ảnh còn lại (hoặc 1 lượng lớn hơn target 1 chút) để dự đoán
        remaining_infos = image_info_list[image_idx : image_idx + min(remaining_images, target_panels + 4)]
        test_rows = _build_ar_strategy(remaining_infos)
        
        candidate_num_panels = 0
        for i, r in enumerate(test_rows):
            if candidate_num_panels == 0:
                candidate_num_panels += len(r)
                continue
                
            next_cand = candidate_num_panels + len(r)
            
            # Row có rủi ro là "1 ảnh đọc/vuông đơn độc" không? 
            # (Ảnh đơn lẻ mà không phải Landscape sẽ bị kéo ngang toàn bộ trang rất xấu)
            is_bad_single = False
            if len(r) == 1:
                ar = r[0].get('aspect', 1.0)
                if ar < 1.25:  # Square hoặc Portrait
                    is_bad_single = True

            # NẾU gặp 1 panel xấu nằm trơ trọi (vì các ảnh dồn vào group trước hết rồi)
            # -> Đừng ép nó thành row dài ngang. Cắt luôn ở đây, vứt ảnh lẻ này qua trang sau!
            if is_bad_single:
                # Tính tổng số ảnh nếu ta cắt ở đây
                leftover_images = total_images - (image_idx + candidate_num_panels)
                
                # NẾU nếu vứt ảnh này qua trang sau, trang sau CHỈ CÒN 1-2 ẢNH rớt lại (hoặc đây là ảnh cuối truyện)
                # thì tàn nhẫn đẩy qua trang sau cũng làm trang sau cực kỳ xấu! 
                # -> Thà ôm luôn vào trang này để gánh nhau.
                if leftover_images <= 2:
                    pass # Cố gắng gom luôn vào trang này
                else:
                    break
                
            # Xem xét khoảng cách tới target
            if abs(next_cand - target_panels) <= abs(candidate_num_panels - target_panels):
                candidate_num_panels = next_cand
            elif next_cand - target_panels == 1:
                # Ưu tiên LẤY LỐ 1 ảnh (ví dụ 8 thay vì 7) để giữ TRỌN VẸN 1 hàng (2 ảnh)
                # thay vì ngắt giữa chừng làm nó rớt xuống thành "1 ảnh đơn độc"
                candidate_num_panels = next_cand
            else:
                break
                
        if candidate_num_panels == 0:
            candidate_num_panels = target_panels
            
        num_panels = max(1, min(candidate_num_panels, remaining_images))
        # -----------------------------------------------------------------
        
        # Lấy thông tin các ảnh cho trang này
        page_image_info = image_info_list[image_idx:image_idx + num_panels]
        page_seed = _build_page_seed(page_num, page_image_info)
        
        # [FIX] Dùng coordinate system động từ page_size
        coord_w = page_size.get('coord_width', 100)
        coord_h = page_size.get('coord_height', 160)
        
        # Không mở rộng coord_h cực đoan để tránh ảnh đầu ra quá dài.
        
        used_grid_layout = False

        # Tạo layout thích ứng với kích thước ảnh
        # Với trang chỉ còn 2 ảnh: nếu diagonal cao thì cho phép layout nghiêng nhẹ để tránh quá đơn điệu.
        if num_panels == 2:
            if adaptive_layout and diagonal_prob >= 0.35:
                panels = create_page_layout(
                    num_panels=num_panels,
                    width=coord_w,
                    height=coord_h,
                    diagonal_probability=min(0.65, diagonal_prob),
                    max_diagonal_angle=10,
                )
            else:
                panels = create_grid_layout(num_panels=num_panels, width=coord_w, height=coord_h)
                used_grid_layout = True
        elif adaptive_layout:
            panels = create_adaptive_layout(
                page_image_info,
                width=coord_w,
                height=coord_h,
                diagonal_probability=diagonal_prob,
                max_diagonal_angle=6,
                # AR-locked: giữ tỉ lệ ảnh đầu vào ổn định như simple, chỉ nghiêng nhẹ để tạo phong cách.
                force_aspect_matched=True,
                deterministic_seed=page_seed,
            )
        else:
            panels = create_page_layout(num_panels=num_panels, width=coord_w, height=coord_h, diagonal_probability=diagonal_prob, max_diagonal_angle=12)

        # Safety gate: reject layout nếu panel lỗi/chồng lấp/quá mảnh/vượt biên.
        valid_panels, layout_issue = _validate_layout(panels, num_panels, coord_w, coord_h)
        if layout_issue is not None:
            print(f"⚠️  Layout trang {page_num} không ổn định ({layout_issue}), fallback grid layout")
            # Ưu tiên grid nghiêng (dynamic) để giữ phong cách manga; chỉ rơi về grid vuông khi cần.
            dynamic_jitter = max(3.0, min(10.0, 3.0 + diagonal_prob * 10.0))
            dynamic_panels = create_dynamic_grid_layout(
                page_image_info,
                width=coord_w,
                height=coord_h,
                jitter_factor=dynamic_jitter,
                margin=3,
                rng=random.Random(page_seed),
            )
            valid_dynamic, dynamic_issue = _validate_layout(dynamic_panels, num_panels, coord_w, coord_h)
            if dynamic_issue is None:
                panels = valid_dynamic
            else:
                grid_panels = create_grid_layout(num_panels=num_panels, width=coord_w, height=coord_h)
                valid_grid_panels, grid_issue = _validate_layout(grid_panels, num_panels, coord_w, coord_h)
                panels = valid_grid_panels if grid_issue is None else grid_panels
                used_grid_layout = True 
        else:
            panels = valid_panels
        
        # [FIX] STRICT PANEL ASSIGNMENT: Giữ thứ tự ảnh đầu vào theo thứ tự đọc trang.
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
        
        def _orientation_from_aspect(aspect: float) -> str:
            if aspect > 1.2:
                return 'landscape'
            if aspect < 0.8:
                return 'portrait'
            return 'square'

        def _is_orientation_match(img_orient: str, panel_orient: str) -> bool:
            return img_orient == panel_orient

        def _build_panels_with_info(panels_list):
            info = []
            for p in panels_list:
                x, y, w, h = p.get_bounds()
                panel_aspect = w / h
                info.append({
                    'panel': p,
                    'bounds': (x, y, w, h),
                    'aspect': panel_aspect,
                    'orientation': _orientation_from_aspect(panel_aspect),
                    'area': w * h
                })
            return info

        # Thu thập thông tin panel
        panels_with_info = _build_panels_with_info(panels)
        # ── Sắp xếp panels theo thứ tự đọc: trên → dưới, trong hàng: LTR hoặc RTL ──
        # Thuật toán (hệ toạ độ y-up):
        # 1. Góm panels vào các hàng bằng cách cluster theo toạ độ y của centerpoint.
        # 2. Sắp hàng giảm dần theo center_y (y lớn hơn nằm cao hơn trên trang).
        # 3. Trong mỗi hàng: LTR sắp theo x tăng dần; RTL sắp giảm dần.
        ROW_TOLERANCE = max(8.0, coord_h * 0.06)  # 6% chiều cao trang (coord_h)

        def _sort_panels_reading_order(panels_info, rtl=False):
            """Sắp xếp panel theo thứ tự đọc: trên-xuống, trong hàng: LTR/RTL."""
            if not panels_info:
                return []

            # Tnh center_y của mỗi panel
            for d in panels_info:
                bx, by, bw, bh = d['bounds']
                d['_cy'] = by + bh / 2.0  # center Y
                d['_cx'] = bx + bw / 2.0  # center X

            # Góm các panel có center_y gần nhau vào cùng hàng (tolerance-based)
            # Với hệ y-up, panel ở phía trên có center_y lớn hơn.
            sorted_by_y = sorted(panels_info, key=lambda d: d['_cy'], reverse=True)
            row_groups = []
            for d in sorted_by_y:
                placed = False
                for rg in row_groups:
                    # So sánh với center_y trung bình của hàng
                    avg_cy = sum(m['_cy'] for m in rg) / len(rg)
                    if abs(d['_cy'] - avg_cy) <= ROW_TOLERANCE:
                        rg.append(d)
                        placed = True
                        break
                if not placed:
                    row_groups.append([d])

            # Sắp hàng: giảm dần theo center_y trung bình (trên -> dưới)
            row_groups.sort(key=lambda rg: sum(m['_cy'] for m in rg) / len(rg), reverse=True)

            # Trong mỗi hàng: sắp theo center_x
            result = []
            for rg in row_groups:
                rg.sort(key=lambda d: d['_cx'], reverse=rtl)
                result.extend(rg)
            return result

        # LUÔN sắp xếp panels theo thứ tự đọc (trên→dưới, trái→phải) trước khi gán ảnh.
        # TUY NHIÊN, với `adaptive_layout` (AR-driven), thứ tự của list panels đã khớp hoàn hảo 100% 
        # với logic AR của mảng ảnh gốc (trái -> phải, trên -> dưới).
        # Hàm sort theo toạ độ Y/X bên dưới có dung sai làm đảo lộn thứ tự khi đường cắt nghiêng quá cao!
        if (not adaptive_layout) or used_grid_layout or reading_direction == 'rtl':
            panels_with_info = _sort_panels_reading_order(panels_with_info, rtl=(reading_direction == 'rtl'))

        def _create_pairs_with_strict_order(images_list, panels_info_list):
            pair_count_local = min(len(images_list), len(panels_info_list))
            if pair_count_local <= 0:
                return [], 0, 0.0

            pairs = []
            mismatch_count_local = 0

            for i in range(pair_count_local):
                image_data = images_list[i]
                panel_info = panels_info_list[i]
                
                img_orient = image_data['info'].get('orientation', 'square')
                panel_orient = panel_info['orientation']
                img_aspect = float(max(1e-6, image_data['info'].get('aspect', 1.0)))
                panel_aspect = float(max(1e-6, panel_info['aspect']))
                
                aspect_delta = abs(math.log(img_aspect / panel_aspect))
                is_match = _is_orientation_match(img_orient, panel_orient) and aspect_delta <= 0.55
                if img_orient == 'square' or panel_orient == 'square':
                    is_match = aspect_delta <= 0.45
                
                if not is_match:
                    mismatch_count_local += 1
                
                pairs.append((image_data, panel_info, is_match))

            mismatch_rate_local = mismatch_count_local / float(pair_count_local) if pair_count_local > 0 else 0.0
            return pairs, mismatch_count_local, mismatch_rate_local

        image_panel_pairs, mismatch_count, mismatch_rate = _create_pairs_with_strict_order(
            page_images,
            panels_with_info,
        )

        # Không đẩy ảnh sang trang sau khi lệch tỉ lệ.
        # Mỗi trang giữ đủ ảnh theo thứ tự để tránh bố cục bị vỡ nhịp câu chuyện.

        # Ghi log thông tin mismatch (chỉ để debug)
        remaining_mismatches = sum(1 for _, _, ok in image_panel_pairs if not ok)
        if remaining_mismatches > 0:
            print(f"   ℹ️  Trang {page_num}: {remaining_mismatches}/{len(image_panel_pairs)} panel không khớp orientation nhẹ (vẫn giữ để đảm bảo thứ tự truyện)")

        
        # Gán ảnh vào các panels (đã được matched)
        assigned = 0
        for img_data, panel_info, is_match in image_panel_pairs:
            panel = panel_info['panel']
            panel_bounds = panel_info['bounds']
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
                match_status = '✅' if is_match else '❌ MISMATCH'
                
                print(f"  ✓ Ảnh {img_original_idx + 1}/{total_images}: {os.path.basename(image_path)} {orientation_icon}{shot_info}{weight_info}")
                print(f"    ↪ Panel {assigned} ({panel_orientation}) - Img aspect: {img_info['aspect']:.2f} → Panel aspect: {panel_w/panel_h:.2f} {match_status}")
        
        # Tiến image_idx theo số ảnh THỰC SỰ ĐÃ RENDER (sau khi overflow trim).
        # Dùng len(image_panel_pairs) thay vì len(page_images) để ảnh bị overflow
        # không bị "tiêu thụ" và sẽ xuất hiện ở đầu trang tiếp theo.
        images_rendered = len(image_panel_pairs)
        image_idx += max(assigned, images_rendered)
        
        # Vẽ trang với kích thước tối ưu
        # Dùng coordinate system đã được chuẩn hóa từ page_size.
        actual_coord_w = page_size.get('coord_width', 100)
        actual_coord_h = page_size.get('coord_height', 140)
        render_dpi = max(96, min(160, int(target_dpi)))

        # Tính figsize từ coord system (không phải từ page_size cố định)
        # Giữ aspect ratio: fig_height/fig_width = coord_h/coord_w
        fig_width = page_size['width'] / float(render_dpi)
        fig_height = fig_width * (actual_coord_h / actual_coord_w)  # Scale theo coord ratio
        
        # [FIX] Dùng coordinate system động
        coord_w = actual_coord_w
        coord_h = actual_coord_h
        
        # Tạo ảnh comic lớn/rõ nét hơn để tránh bị mờ
        fig, ax = plt.subplots(1, figsize=(fig_width, fig_height), dpi=render_dpi)
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
        plt.savefig(output_path, dpi=render_dpi, bbox_inches='tight', facecolor='white')
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

