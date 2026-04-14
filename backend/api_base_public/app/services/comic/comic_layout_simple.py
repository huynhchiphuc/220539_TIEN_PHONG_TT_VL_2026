import os
import random
import re
from PIL import Image, ImageDraw, ImageOps, ImageFont

# Import smart crop if available
try:
    from app.services.ai.smart_crop import analyze_shot_type
    SMART_CROP_AVAILABLE = True
except ImportError:
    try:
        from smart_crop import analyze_shot_type
        SMART_CROP_AVAILABLE = True
    except ImportError:
        SMART_CROP_AVAILABLE = False


def local_center_crop(img, target_aspect):
    """
    Fallback center crop function if smart_crop is not available.
    Crop ảnh từ trung tâm về aspect ratio mong muốn.
    """
    current_w, current_h = img.size
    current_aspect = current_w / current_h
    
    if abs(current_aspect - target_aspect) < 0.01:
        return img
    
    if current_aspect > target_aspect:
        # Ảnh quá ngang, crop 2 bên
        new_w = int(current_h * target_aspect)
        left = (current_w - new_w) // 2
        return img.crop((left, 0, left + new_w, current_h))
    else:
        # Ảnh quá dọc, crop trên/dưới
        new_h = int(current_w / target_aspect)
        top = (current_h - new_h) // 2
        return img.crop((0, top, current_w, top + new_h))


def self_draw_shot_label(pil_img, img_path):
    """
    Hàm phụ trợ dán nhãn Shot Type lên ảnh cho Simple Mode.
    Sử dụng font mặc định nếu không load được font.
    """
    if not SMART_CROP_AVAILABLE:
        return pil_img
        
    try:
        shot_info = analyze_shot_type(img_path)
        label = shot_info.get('shot_type', 'unknown').upper().replace('_', ' ')
        
        draw = ImageDraw.Draw(pil_img)
        # Vẽ một label nhỏ ở góc
        # Tải font mặc định hoặc font hệ thống nếu được
        font_size = max(24, pil_img.width // 40)
        # Thử load font Arial hoặc font mặc định
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()

        # Tính toán kích thước label
        text_bbox = draw.textbbox((10, 10), label, font=font)
        bg_rect = [text_bbox[0]-5, text_bbox[1]-5, text_bbox[2]+5, text_bbox[3]+5]
        
        draw.rectangle(bg_rect, fill="black")
        draw.text((10, 10), label, fill="white", font=font)
    except Exception as e:
        print(f"Warning: Label drawing failed: {e}")
        pass
    return pil_img

def classify_aspect_ratio(aspect):
    """
    Phân loại ảnh theo tỷ lệ khung hình với nhiều trường hợp chi tiết hơn.
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


def compute_row_height(aspects, content_width, gap):
    """
    Tính chiều cao chính xác của một row khi N ảnh xếp ngang nhau.
    
    Công thức: row_h = (content_width - gap * (N-1)) / sum(aspects)
    Điều này đảm bảo: sum(aspect_i * row_h) + gap*(N-1) = content_width  ✓
    
    Args:
        aspects: List[float] - tỷ lệ w/h của từng ảnh
        content_width: int - chiều rộng khả dụng (đã trừ margin)
        gap: int - khoảng cách giữa ảnh
    Returns:
        float: row height
    """
    n = len(aspects)
    used_by_gaps = gap * (n - 1)
    available_for_images = content_width - used_by_gaps
    total_aspect = sum(aspects)
    if total_aspect <= 0:
        return 0.0
    return available_for_images / total_aspect


def group_images_into_rows(images_data, content_width, gap, target_row_h,
                            min_row_h, max_single_row_h, adaptive_layout,
                            panels_per_page=0, max_per_row=4, use_smart_crop=False):
    """
    Nhóm ảnh thành rows bằng toán học aspect ratio.
    
    Với mỗi vị trí i, thử N = 1..max_per_row ảnh, tính:
        row_h = (content_width - gap*(N-1)) / sum(aspects[i..i+N-1])
    Chọn N cho score = |row_h - target_row_h| / target_row_h nhỏ nhất.
    
    Returns:
        List[dict]: [{'group': [...], 'row_h': float}, ...]
    """
    row_groups = []
    i = 0
    n_total = len(images_data)

    while i < n_total:
        # Ảnh panoramic/wide_landscape luôn đứng một mình, không nhóm
        current_img = images_data[i]
        is_solo = (not adaptive_layout or
                   current_img['type'] in ('ultra_panoramic', 'panoramic', 'cinema_landscape', 'wide_landscape'))
        
        if is_solo and current_img['type'] in ('ultra_panoramic', 'panoramic', 'cinema_landscape', 'wide_landscape'):
            print(f"   🎬 {os.path.basename(current_img['path'])}: aspect={current_img['aspect']:.2f} → RIÊNG 1 DÒNG ({current_img['type']})")

        if is_solo:
            best_n = 1
        else:
            best_n = 1
            best_score = float('inf')

            for candidate_n in range(1, min(max_per_row + 1, n_total - i + 1)):
                group = images_data[i:i + candidate_n]
                aspects = [d['aspect'] for d in group]
                row_h = compute_row_height(aspects, content_width, gap)

                # Nếu ảnh THỨ 2 trở đi trong nhóm là panoramic/wide → dừng mở rộng
                if candidate_n > 1 and any(d['type'] in ('ultra_panoramic', 'panoramic', 'cinema_landscape', 'wide_landscape')
                                            for d in group[1:]):
                    break

                # Nếu row quá thấp (thêm ảnh khiến row bị bẹt) → dừng thêm
                if candidate_n > 1 and row_h < min_row_h:
                    break

                # Score = khoảng cách chuẩn hóa so với target
                score = abs(row_h - target_row_h) / target_row_h

                # [FIX CLI] Ưu tiên 2 ảnh/dòng để hình to rõ. 
                # Nếu chọn 3 ảnh, chỉ chấp nhận nếu TẤT CẢ là ảnh dọc (Portrait)
                if candidate_n == 3 and panels_per_page > 3:
                    is_all_portrait = all(d.get('aspect', 1.0) < 0.95 for d in group)
                    if not is_all_portrait:
                        score += 2.0  # Phạt nặng để ưu tiên chia 2 hàng to hơn

                # Phạt nếu row vẫn rất cao dù đã nhóm (ảnh đứng 1 mình và cao wquá)
                if candidate_n == 1 and row_h > target_row_h * 1.8:
                    score += 0.3
                # Phạt nếu row quá thấp
                if row_h < target_row_h * 0.4:
                    score += 0.5

                if score < best_score:
                    best_score = score
                    best_n = candidate_n

        group_data = images_data[i:i + best_n]
        aspects = [d['aspect'] for d in group_data]
        row_h = compute_row_height(aspects, content_width, gap)

        # Nếu ảnh đơn lẻ quá cao → center-crop bảo vệ layout (CHỈ KHI BẬT SMART CROP)
        if use_smart_crop and best_n == 1 and row_h > max_single_row_h:
            target_ar = content_width / max_single_row_h
            item = group_data[0]
            item['img'] = local_center_crop(item['img'], target_ar)
            item['width'], item['height'] = item['img'].size
            item['aspect'] = item['width'] / item['height']
            aspects = [item['aspect']]
            row_h = min(max_single_row_h,
                        compute_row_height(aspects, content_width, gap))

        row_groups.append({'group': group_data, 'row_h': row_h})
        i += best_n

    return row_groups


def create_dummy_images(folder_path, count=5):
    """
    Hàm tạo ảnh giả lập để test chương trình.
    Tạo ra các ảnh ngẫu nhiên ngang/dọc với màu sắc khác nhau.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
    created_files = []
    
    print(f"--- Đang tạo {count} ảnh mẫu tại thư mục '{folder_path}' ---")
    
    for i in range(count):
        # Giả lập logic: Ảnh chẵn là ngang, ảnh lẻ là dọc (hoặc ngẫu nhiên)
        if i % 3 == 0: 
            # Ảnh ngang (Landscape)
            w, h = 800, 600
            text = "LANDSCAPE"
        else:
            # Ảnh dọc (Portrait)
            w, h = 600, 900
            text = "PORTRAIT"
            
        img = Image.new('RGB', (w, h), color=colors[i % len(colors)])
        draw = ImageDraw.Draw(img)
        # Vẽ khung
        draw.rectangle([10, 10, w-10, h-10], outline="white", width=5)
        # Vẽ chữ số thứ tự
        draw.text((w//2, h//2), f"IMG {i+1} ({text})", fill="white", anchor="mm", font_size=50)
        
        filename = os.path.join(folder_path, f"input_{i:03d}.jpg")
        img.save(filename)
        created_files.append(filename)
        print(f"Đã tạo: {filename}")
        
    return created_files

def process_comic_layout(input_folder, output_filename="comic_page_result.jpg",
                         page_width=1000, margin=20, gap=20, page_height=2700,
                         panels_per_page=8, use_smart_crop=False,
                         adaptive_layout=True, analyze_shot_type=False,
                         classify_characters=False, reading_direction='ltr',
                         draw_border=True, border_width=4, border_color="black"):
    """
    Hàm chính xử lý dàn trang truyện tranh với PHÂN TRANG và math-based layout.

    Thuật toán mới (v2):
    - Nhóm ảnh bằng công thức aspect ratio thực tế:
        row_h = (content_width - gap*(N-1)) / sum(aspect_i)
      → chọn N cho row_h gần target_row_h nhất
    - Phân trang greedy với dung sai 5%
    - Render: dàn đều khoảng cách (dynamic gap) hoặc căn giữa dọc
    
    Args:
        reading_direction: 'ltr' (left-to-right, default) hoặc 'rtl' (right-to-left, manga)
    """
    import math

    # ── 1. Load ảnh ──────────────────────────────────────────────────────────
    valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    def natural_key(path):
        name = os.path.basename(path)
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', name)]

    image_files = sorted([
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
        if f.lower().endswith(valid_exts)
    ], key=natural_key)
    
    # Thứ tự ảnh giữ nguyên theo câu chuyện; RTL chỉ ảnh hưởng vị trí panel trong mỗi hàng
    if reading_direction == 'rtl':
        print("📖 Reading direction: RTL (Right-to-Left, Manga style)")
    else:
        print("📖 Reading direction: LTR (Left-to-Right, Western style)")

    if not image_files:
        print("Không tìm thấy ảnh nào trong thư mục đầu vào!")
        return []

    print(f"\n─── Bắt đầu xử lý {len(image_files)} ảnh ───")

    images_data = []
    for f in image_files:
        try:
            img = Image.open(f)
            img = ImageOps.exif_transpose(img).convert('RGB')
            w, h = img.size
            
            # Ảnh nhỏ hơn 200x200 vẫn được giữ lại nếu người dùng đã xác nhận ở frontend.
            if w < 200 or h < 200:
                print(f"   ⚠️  {os.path.basename(f)} có kích thước nhỏ ({w}x{h}), vẫn giữ theo lựa chọn người dùng")

            orig_aspect = w / h

            if use_smart_crop and SMART_CROP_AVAILABLE:
                # Keep original aspect ratio for layout fidelity.
                # Smart crop is only used later when needed for extreme rows.
                print(f"   📐 {os.path.basename(f)}: giữ nguyên tỉ lệ gốc {orig_aspect:.2f}")

            aspect = w / h
            images_data.append({
                'img': img,
                'path': f,
                'width': w,
                'height': h,
                'aspect': aspect,
                'type': classify_aspect_ratio(aspect),
            })
        except Exception as e:
            print(f"   ⚠️  Lỗi mở file {os.path.basename(f)}: {e}")

    if not images_data:
        return []

    # ── 2. Thông số layout ────────────────────────────────────────────────────
    content_width    = page_width  - 2 * margin
    available_height = page_height - 2 * margin

    # target_row_h: chiều cao lý tưởng 1 row = chia đều trang theo panels_per_page
    # Ví dụ panels_per_page=3 → target=33% trang; panels_per_page=8 → target=12.5% trang
    # Đây là cách duy nhất đảm bảo layout scale đúng theo setting của user.
    target_row_h = available_height / panels_per_page

    min_row_h        = available_height * 0.06   # Tối thiểu 6% trang

    # max_single_row_h: ảnh đơn lẻ tối đa cao bao nhiêu
    # Không dùng target*2.5 vì khi panels_per_page lớn (=8) thì target nhỏ
    # → target*2.5 chỉ = 31% trang → ảnh portrait bị crop quá tệ.
    # Dùng công thức: floor theo panels: ít panel → cho phép ảnh cao hơn.
    # panels=3 → 85%,  panels=5 → 75%,  panels=8 → 60%
    max_single_factor = max(0.55, 0.90 - (panels_per_page - 1) * 0.05)
    max_single_row_h  = available_height * max_single_factor

    # max_per_row: số ảnh tối đa mỗi row, scale theo panels_per_page
    # VERTICAL PRIORITY (ưu tiên layout dọc - nhiều rows, ít panels/row)
    # panels=3-5 → max 3/row (1-2 rows)
    # panels=6-8 → max 2/row (3-4 rows)  ← Ưu tiên dọc
    # panels=3 → max 3/row (1 row)
    # Cho phép thử tối đa 3 ảnh/hàng, nhưng thuật toán bên trong 
    # sẽ phạt nặng nếu gom 3 ảnh mà không phải toàn bộ là ảnh dọc.
    if panels_per_page <= 2:
        max_per_row = 2
    else:
        max_per_row = 3
    
    print(f"   📐 Target row height : {int(target_row_h)}px  (panels_per_page={panels_per_page})")
    print(f"   📏 Content area      : {content_width} × {available_height}px")
    print(f"   🔢 Max per row       : {max_per_row} (vertical priority)")

    # ── 3. Nhóm ảnh thành rows ────────────────────────────────────────────────
    row_groups = group_images_into_rows(
        images_data, content_width, gap,
        target_row_h, min_row_h, max_single_row_h,
        adaptive_layout, panels_per_page=panels_per_page,
        max_per_row=max_per_row,
        use_smart_crop=use_smart_crop,
    )

    print(f"\n   📦 Chia thành {len(row_groups)} rows từ {len(images_data)} ảnh")
    for idx, rg in enumerate(row_groups):
        n = len(rg['group'])
        types = '+'.join(d['type'] for d in rg['group'])
        print(f"      Row {idx+1}: {n} ảnh [{types}] → row_h={rg['row_h']:.0f}px")

    # ── 4. Phân trang (ưu tiên đúng số panel/trang) ───────────────────────────
    pages = []
    remaining = list(row_groups)

    def _clone_row_with_group(group_items):
        cloned_group = list(group_items)
        cloned_aspects = [d['aspect'] for d in cloned_group]
        cloned_row_h = compute_row_height(cloned_aspects, content_width, gap)
        return {'group': cloned_group, 'row_h': cloned_row_h}

    PANEL_TOLERANCE = 1  # Cho phép lệch +1 panel để giảm trang cuối bị ảnh quá to.

    def _is_portraitish(item):
        return float(item.get('aspect', 1.0)) <= 0.98

    while remaining:
        page_rows = []
        panel_count = 0

        while remaining:
            rg = remaining[0]
            proj_panels = panel_count + len(rg['group'])

            # Ưu tiên gom đủ panels_per_page. Chiều cao sẽ được scale ở bước render.
            if proj_panels <= panels_per_page:
                page_rows.append(remaining.pop(0))
                panel_count = proj_panels
            else:
                # Cho phép overflow +1 trong trường hợp còn thiếu 1 slot,
                # và row kế tiếp là cặp ảnh dọc -> tránh đẩy 1 ảnh sang trang sau làm ảnh phóng to.
                room_left = panels_per_page - panel_count
                is_portrait_pair = (
                    len(rg['group']) == 2
                    and all(_is_portraitish(d) for d in rg['group'])
                )
                if (
                    room_left == 1
                    and is_portrait_pair
                    and proj_panels <= (panels_per_page + PANEL_TOLERANCE)
                ):
                    page_rows.append(remaining.pop(0))
                    panel_count = proj_panels
                    continue

                room_left = panels_per_page - panel_count
                if room_left > 0:
                    # Tách row để lấp đầy trang hiện tại thay vì bỏ phí slot.
                    head_group = rg['group'][:room_left]
                    tail_group = rg['group'][room_left:]

                    if head_group:
                        page_rows.append(_clone_row_with_group(head_group))
                        panel_count += len(head_group)

                    # Cập nhật lại row còn dư cho trang sau.
                    if tail_group:
                        remaining[0] = _clone_row_with_group(tail_group)
                    else:
                        remaining.pop(0)
                elif not page_rows:
                    # Trường hợp bất thường: trang chưa có gì thì vẫn phải lấy 1 row.
                    page_rows.append(remaining.pop(0))
                break   

        pages.append(page_rows)

    # ── 4.1 Cân bằng liên trang (tránh trang cuối có ảnh dọc quá to) ─────────
    # Nếu trang kế bắt đầu bằng cặp ảnh dọc, ưu tiên kéo lên trang trước
    # để giảm cảm giác "trang cuối phóng to". Cho phép vượt nhẹ so với panels_per_page.
    REBALANCE_SOFT_LIMIT = panels_per_page + 1
    REBALANCE_PORTRAIT_PAIR_LIMIT = panels_per_page + 2

    idx = 0
    while idx < len(pages) - 1:
        curr = pages[idx]
        nxt = pages[idx + 1]
        if not nxt:
            idx += 1
            continue

        curr_count = sum(len(rg['group']) for rg in curr)
        first_next = nxt[0]
        first_next_count = len(first_next['group'])
        first_is_portrait_pair = (
            first_next_count == 2
            and all(_is_portraitish(d) for d in first_next['group'])
        )

        moved = False

        # Rule A: kéo cặp ảnh dọc (cho phép vượt thêm 2 panel).
        if first_is_portrait_pair and (curr_count + first_next_count) <= REBALANCE_PORTRAIT_PAIR_LIMIT:
            curr.append(nxt.pop(0))
            moved = True
            print(f"   🔁 Rebalance: kéo 1 row ảnh dọc từ trang {idx+2} lên trang {idx+1} (panels {curr_count}→{curr_count + first_next_count})")

        # Rule B: row thường chỉ cho vượt nhẹ +1 panel.
        elif (curr_count + first_next_count) <= REBALANCE_SOFT_LIMIT:
            curr.append(nxt.pop(0))
            moved = True
            print(f"   🔁 Rebalance: kéo 1 row từ trang {idx+2} lên trang {idx+1} (panels {curr_count}→{curr_count + first_next_count})")

        if moved and not nxt:
            pages.pop(idx + 1)
            continue

        idx += 1

    print(f"\n   📄 Tổng số trang: {len(pages)}")

    # ── 5. Render từng page ───────────────────────────────────────────────────
    output_files = []
    base_name = output_filename.rsplit('.', 1)[0] if '.' in output_filename else output_filename
    ext        = output_filename.rsplit('.', 1)[1] if '.' in output_filename else 'jpg'

    for page_idx, page_rows in enumerate(pages, 1):
        n_rows = len(page_rows)
        page_panel_count = sum(len(rg['group']) for rg in page_rows)

        # Nếu tổng chiều cao tự nhiên quá lớn, scale toàn bộ rows để vẫn giữ đủ panel/trang.
        # Mục tiêu: không đánh rơi panel chỉ vì tràn chiều cao.
        natural_row_total = sum(rg['row_h'] for rg in page_rows)
        base_gaps = gap * (n_rows - 1) if n_rows > 1 else 0
        row_scale = 1.0
        if natural_row_total > 0:
            max_row_space = max(1.0, available_height - base_gaps)
            if natural_row_total > max_row_space:
                row_scale = max_row_space / natural_row_total
                row_scale = max(0.2, min(1.0, row_scale))

        # Tổng chiều cao tự nhiên của tất cả rows trên trang
        total_row_h = sum(rg['row_h'] * row_scale for rg in page_rows)
        total_gaps  = gap * (n_rows - 1) if n_rows > 1 else 0
        total_content = total_row_h + total_gaps

        # ── Tính dynamic gap để lấp đầy trang ──────────────────────────────
        extra = available_height - total_content  # Không gian còn dư

        if n_rows > 1 and extra > 0:
            # Phân phối dư vào các gap giữa rows (không phân phối vào margin)
            # Giới hạn gap tối đa = gap ban đầu × 1.5 (giảm từ 4.0 xuống)
            max_extra_gap = gap * 1.5
            extra_per_gap = extra / (n_rows - 1)
            dynamic_gap = min(max_extra_gap, gap + extra_per_gap)
        else:
            dynamic_gap = float(gap)

        # Tính lại total content với dynamic_gap để căn giữa dọc trang
        total_content_final = total_row_h + dynamic_gap * (n_rows - 1)
        white_space = max(0, int(round(available_height - total_content_final)))
        top_padding = margin + max(0, (available_height - total_content_final) // 2)

        canvas = Image.new('RGB', (page_width, page_height), 'white')
        current_y = int(top_padding)

        for rix, rg in enumerate(page_rows):
            group_data  = rg['group']
            row_h       = max(1, int(round(rg['row_h'] * row_scale)))
            aspects     = [d['aspect'] for d in group_data]

            # ── Render ảnh trong row ─────────────────────────────────────────
            # Tính chiều rộng từng ảnh (exact math: sum = content_width)
            img_widths = [int(asp * row_h) for asp in aspects]

            # FIXED: Justify layout - spread đều panels và gaps
            n_panels = len(img_widths)
            if n_panels > 1:
                # Tính total gaps cần thiết
                n_gaps = n_panels - 1
                total_gaps = gap * n_gaps
                total_img_widths = sum(img_widths)
                
                # Remainder sau khi trừ gaps
                remainder = content_width - total_img_widths - total_gaps
                
                if remainder > 0:
                    # Distribute remainder đều vào các panels
                    per_panel = remainder // n_panels
                    leftover = remainder % n_panels
                    
                    img_widths = [w + per_panel for w in img_widths]
                    # Cộng leftover vào panel cuối
                    img_widths[-1] += leftover
                elif remainder < 0:
                    # Trường hợp tổng quá lớn (hiếm), trừ từ panel lớn nhất
                    img_widths[-1] = max(1, img_widths[-1] + remainder)
            else:
                # Single panel: fill toàn bộ content_width
                img_widths[0] = content_width

            # Paste với justify alignment
            # 🆕 Reverse panel order trong row nếu RTL
            panels_to_render = list(zip(group_data, img_widths))
            if reading_direction == 'rtl':
                panels_to_render = list(reversed(panels_to_render))
            
            x = margin
            for idx2, (d, img_w) in enumerate(panels_to_render):
                if img_w <= 0:
                    continue
                resized = d['img'].resize((img_w, row_h), Image.Resampling.LANCZOS)

                if analyze_shot_type:
                    resized = self_draw_shot_label(resized, d['path'])

                canvas.paste(resized, (x, current_y))
                
                if draw_border:
                    draw = ImageDraw.Draw(canvas)
                    draw.rectangle([x, current_y, x + img_w - 1, current_y + row_h - 1], outline=border_color, width=border_width)

                x += img_w + gap

            # Cập nhật y cho row tiếp theo
            dg = int(round(dynamic_gap)) if rix < n_rows - 1 else 0
            current_y += row_h + dg

        # ── Lưu file ─────────────────────────────────────────────────────────
# Đồng nhất tên file luôn có suffix (vd: page_001.jpg) để tránh dính cache với ảnh cũ của chế độ AI
        if len(pages) == 1:
            page_filename = f"{base_name}_001.{ext}"
        else:
            page_filename = f"{base_name}_{page_idx:03d}.{ext}"

        canvas.save(page_filename, quality=95)
        output_files.append(page_filename)
        print(f"   ✅ Trang {page_idx}/{len(pages)}: "
              f"{n_rows} rows · {page_panel_count} panels · "
              f"gap={int(dynamic_gap)}px · "
              f"trống≈{white_space}px → {page_filename}")

    print(f"\n🎉 HOÀN THÀNH! {len(pages)} trang ({page_width}×{page_height}px).")
    return output_files

# --- KHỐI CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    # Tên thư mục chứa ảnh
    input_dir = "comic_inputs"
    
    # 1. Tạo ảnh giả lập (Bạn có thể comment dòng này nếu đã có ảnh thật)
    create_dummy_images(input_dir, count=15)  # Tạo nhiều ảnh hơn để test pagination
    
    # 2. Chạy xử lý với pagination
    process_comic_layout(
        input_folder=input_dir,
        output_filename="trang_truyen_hoan_chinh.jpg",
        page_width=1200,      # Chiều rộng trang
        margin=40,            # Lề giấy trắng
        gap=30,               # Khoảng cách giữa các tranh
        page_height=2900,     # Chiều cao CỐ ĐỊNH
        panels_per_page=8     # Tối đa 8 panels/page
    )
