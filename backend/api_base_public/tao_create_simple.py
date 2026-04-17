import argparse
import json
import os
import sys

# Đảm bảo có thể import được các module trong app/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.comic.comic_layout_simple import process_comic_layout

# ── Kích thước giấy chuẩn (px @ 150 DPI) ──────────────────────────────────────
# Mặc định của công ty: A5 portrait (148×210mm)
PAGE_PRESETS = {
    'a5':    {'aspect': '148:210', 'label': 'A5 (148×210mm)'},   # 874×1240px @150dpi
    'a4':    {'aspect': '210:297', 'label': 'A4 (210×297mm)'},   # 1240×1754px @150dpi
    'a6':    {'aspect': '105:148', 'label': 'A6 (105×148mm)'},
    '9:16':  {'aspect': '9:16',   'label': '9:16 (Mobile)'},
    '12:16': {'aspect': '12:16',  'label': '12:16 (Tablet)'},
    '16:9':  {'aspect': '16:9',   'label': '16:9 (Landscape)'},
}


def resolve_aspect(aspect_str: str) -> str:
    """Chuyển đổi tên preset (vd: 'a5') thành tỉ lệ số (vd: '148:210')."""
    key = aspect_str.strip().lower()
    if key in PAGE_PRESETS:
        return PAGE_PRESETS[key]['aspect']
    return aspect_str  # Trả lại nguyên nếu là ratio rồi


def load_config(config_path: str, input_folder: str):
    """
    Đọc file JSON cấu hình và trả về (panels_override, initial_image_info, aspect_override).

    Hỗ trợ 2 format:
    ┌─ Format MỚI (đầy đủ) ────────────────────────────────────────────────┐
    │ {                                                                     │
    │   "panels": 5,                                                        │
    │   "aspect": "9:16",       ← tuỳ chọn, ghi đè --aspect CLI           │
    │   "images": [                                                         │
    │     {"filename": "001.png", "aspect": 1.4, "shot_type": "wide"},     │
    │     ...                                                               │
    │   ]                                                                   │
    │ }                                                                     │
    └───────────────────────────────────────────────────────────────────────┘
    ┌─ Format CŨ (backward-compat, mảng phẳng) ───────────────────────────┐
    │ [                                                                     │
    │   {"filename": "001.png", "aspect": 1.4, "shot_type": "wide"},       │
    │   ...                                                                 │
    │ ]                                                                     │
    └───────────────────────────────────────────────────────────────────────┘
    Trả về (panels_override, image_info_list, aspect_override)
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    panels_override = None
    aspect_override = None
    image_list_raw  = []

    if isinstance(raw, dict):
        # ── Format mới ──
        panels_override = raw.get('panels', None)
        if panels_override is not None:
            panels_override = int(panels_override)
        aspect_override = raw.get('aspect', None)   # Có thể là "9:16", "A5", ...
        image_list_raw  = raw.get('images', [])
    elif isinstance(raw, list):
        # ── Format cũ (mảng phẳng) ──
        image_list_raw = raw
    else:
        raise ValueError("File JSON không đúng định dạng (phải là object {} hoặc array [])")

    initial_image_info = []
    for item in image_list_raw:
        fname = item.get('filename') or item.get('path', '')
        initial_image_info.append({
            'path':      fname,   # sẽ được resolve sang đường dẫn tuyệt đối sau
            'aspect':    float(item.get('aspect', 1.0)),
            'shot_type': item.get('shot_type', 'medium'),
        })

    return panels_override, initial_image_info, aspect_override


def main():
    parser = argparse.ArgumentParser(
        description="CLI tạo Comic từ thư mục ảnh hoặc file cấu hình JSON (Chế độ SIMPLE GRID).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Không có config: scan toàn bộ folder, 9:16 mặc định, 5 panels/trang
  python tao_create_simple.py --folder uploads/aaa --output outputs/aaa

  # Với config JSON (chứa panels + thứ tự ảnh):
  python tao_create_simple.py --folder uploads/aaa --output outputs/aaa --config config_mau.json

  # Ghi đè aspect/panels từ CLI (CLI > JSON > mặc định):
  python tao_create_simple.py --folder uploads/aaa --output outputs/aaa --config config_mau.json --panels 6 --aspect a5
        """
    )

    parser.add_argument("--folder",  required=True, help="Thư mục chứa ảnh đầu vào")
    parser.add_argument("--output",  required=True, help="Thư mục lưu kết quả")
    parser.add_argument("--panels",  type=int,      default=None,
                        help="Số khung tối đa mỗi trang (Ghi đè giá trị trong JSON nếu có)")
    parser.add_argument("--aspect",  type=str,      default=None,
                        help="Tỉ lệ trang: '9:16' (mặc định), 'A5', 'A4', '12:16', ...")
    parser.add_argument("--config",  type=str,      default=None,
                        help="Đường dẫn file JSON cấu hình (panels, thứ tự ảnh, ...)")

    args = parser.parse_args()

    input_folder  = os.path.abspath(args.folder)
    output_folder = os.path.abspath(args.output)

    if not os.path.exists(input_folder):
        print(f"❌ LỖI: Thư mục input '{input_folder}' không tồn tại!")
        sys.exit(1)

    # ── Giá trị mặc định ────────────────────────────────────────────────────────
    panels_final = 5          # Mặc định 5 panels/trang (SIMPLE mode)
    aspect_final = '9:16'    # Mặc định 9:16 portrait mobile

    # ── Ưu tiên: JSON config < CLI args ──────────────────────────────────────────
    initial_image_info = None

    if args.config:
        config_path = os.path.abspath(args.config)
        if os.path.exists(config_path):
            try:
                panels_json, images_json, aspect_json = load_config(config_path, input_folder)
                if images_json:
                    initial_image_info = images_json
                if panels_json is not None:
                    panels_final = panels_json     # JSON ghi đè mặc định
                if aspect_json is not None:
                    aspect_final = aspect_json     # JSON ghi đè mặc định
                print(f"✅ Đã tải config: {args.config} "
                      f"({len(initial_image_info or [])} ảnh"
                      f"{', panels=' + str(panels_final) if panels_json else ''}"
                      f"{', aspect=' + str(aspect_final) if aspect_json else ''})")
            except Exception as e:
                print(f"⚠️  Lỗi đọc config JSON: {e} — sẽ dùng scan folder mặc định.")
        else:
            print(f"⚠️  File config '{args.config}' không tồn tại, bỏ qua.")

    # CLI arg ghi đè tất cả (nếu người dùng chỉ định rõ)
    if args.panels is not None:
        panels_final = args.panels
    if args.aspect is not None:
        aspect_final = args.aspect

    # Chuyển preset tên (a5, a4, ...) → tỉ lệ số "W:H"
    aspect_ratio_str = resolve_aspect(aspect_final)

    # Tính kích thước trang từ ratio
    w_ratio, h_ratio = 9, 16
    try:
        if ":" in aspect_ratio_str:
            parts = aspect_ratio_str.split(":")
            w_ratio, h_ratio = int(parts[0]), int(parts[1])
    except Exception:
        pass

    page_width  = 1200
    page_height = int(page_width * h_ratio / w_ratio)

    # Tạo output nếu chưa có
    os.makedirs(output_folder, exist_ok=True)

    # Base suffix để render thành page_001.jpg
    output_filename = os.path.join(output_folder, "page.jpg")

    # Log thông tin
    preset_label = PAGE_PRESETS.get(aspect_final.lower(), {}).get('label', aspect_ratio_str)
    print("=" * 62)
    print("✨  TIẾN TRÌNH CREATE COMIC ĐANG KHỞI CHẠY (CHẾ ĐỘ SIMPLE)")
    print(f"📂  Folder  : {input_folder}")
    print(f"💾  Output  : {output_folder}")
    print(f"📄  Panels  : {panels_final} khung/trang")
    print(f"📐  Trang   : {preset_label}  →  ratio {aspect_ratio_str}  ({page_width}×{page_height}px)")
    if args.config:
        print(f"📝  Config  : {args.config}")
    print("=" * 62)

    # ── Gọi hàm lõi ──────────────────────────────────────────────────────────────
    process_comic_layout(
        input_folder       = input_folder,
        output_filename    = output_filename,
        page_width         = page_width,
        margin             = 30,      # Viền trắng bao quanh trang
        gap                = 25,      # Khoảng cách giữa các phần tử
        page_height        = page_height,
        panels_per_page    = panels_final,
        use_smart_crop     = True,    # Kích hoạt Crop giữ mặt / nội dung trọng tâm
        analyze_shot_type  = False,   # [Đã TẮT] Không vẽ nhãn WIDE/MEDIUM lên khung ảnh
        initial_image_info = initial_image_info,
    )

    print("\n✅ HOÀN TẤT KỊCH BẢN SIMPLE! Các trang truyện tranh đã được xuất ra:")
    print("👉", output_folder)


if __name__ == "__main__":
    main()
