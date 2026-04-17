"""
compose_pages.py
================
Pipeline 3 – Bỏ ảnh vào khung từ JSON layout.

Đọc file JSON layout và một folder chứa ảnh.
Ảnh được sắp xếp theo tên file (số thứ tự: 1, 2, 3, ...).
Ảnh thứ n được đặt vào khung có global_order = n.

Mỗi ảnh được scale + crop giữa (center-crop) để vừa khít khung,
giữ nguyên tỉ lệ gốc của ảnh (không kéo méo).

Cách chạy:
    python compose_pages.py layout.json images/
    python compose_pages.py layout.json images/ --out-dir output --scale 1.0 --format png
    python compose_pages.py layout.json images/ --page 1   # chỉ render trang 1
    python compose_pages.py layout.json images/ --bg-color 255,255,255
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

# Fix encoding Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[ERROR] Pillow chưa được cài. Chạy: pip install Pillow")
    sys.exit(1)

# ── Hằng số ───────────────────────────────────────────────────────────────────
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
BORDER_COLOR   = (20, 20, 20)
PAGE_BG        = (30, 30, 30)      # nền trang tối (để khung trống nổi bật)
EMPTY_PANEL_BG = (60, 60, 60)      # màu khung khi không có ảnh
EMPTY_LABEL_FG = (120, 120, 120)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf", "verdana.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _numeric_key(path: Path) -> int:
    """Trích số từ tên file để sắp xếp: '1.png' → 1, '012.jpg' → 12."""
    digits = re.search(r"\d+", path.stem)
    return int(digits.group()) if digits else 0


def collect_images(image_dir: str) -> list[Path]:
    """
    Thu thập tất cả ảnh trong folder, sắp xếp theo số trong tên file.
    Trả về list[Path] đã sắp xếp.
    """
    folder = Path(image_dir)
    if not folder.is_dir():
        print(f"[ERROR] Không tìm thấy folder: {image_dir}")
        sys.exit(1)

    images = [p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]
    images.sort(key=_numeric_key)
    return images


def fit_image_to_panel(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """
    Scale + center-crop ảnh để vừa khít panel (cover mode).
    Không kéo méo – giữ tỉ lệ gốc của ảnh.
    """
    src_w, src_h = img.size
    if src_w == 0 or src_h == 0 or panel_w == 0 or panel_h == 0:
        return Image.new("RGB", (max(1, panel_w), max(1, panel_h)), EMPTY_PANEL_BG)

    # Scale để ảnh bao phủ toàn bộ panel (cover)
    scale = max(panel_w / src_w, panel_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Center-crop
    left = (new_w - panel_w) // 2
    top  = (new_h - panel_h) // 2
    crop = img_resized.crop((left, top, left + panel_w, top + panel_h))
    return crop


# ── Render một trang ──────────────────────────────────────────────────────────

def render_page_with_images(
    page_data: dict,
    coord_w: float,
    coord_h: float,
    output_px_w: int,
    output_px_h: int,
    image_map: dict,          # global_order → Path
    border_px: int = 3,
    bg_color: tuple = PAGE_BG,
) -> Image.Image:
    """
    Render một trang với ảnh thật bên trong từng panel.

    Args:
        page_data:    dict trang từ JSON.
        coord_w/h:    hệ toạ độ logic.
        output_px_w:  chiều rộng ảnh output (px).
        output_px_h:  chiều cao ảnh output (px).
        image_map:    {global_order: Path} – ánh xạ khung → file ảnh.
        border_px:    độ dày viền.
        bg_color:     màu nền trang.
    """
    sx = output_px_w / coord_w
    sy = output_px_h / coord_h

    canvas = Image.new("RGB", (output_px_w, output_px_h), bg_color)
    draw   = ImageDraw.Draw(canvas)

    panels = page_data.get("panels", [])

    placed   = 0
    skipped  = 0

    for panel in panels:
        bbox  = panel["bbox"]
        gorder = panel["global_order"]

        # Tọa độ pixel
        px = int(bbox["x"] * sx)
        py = int(bbox["y"] * sy)
        pw = max(1, int(bbox["w"] * sx))
        ph = max(1, int(bbox["h"] * sy))

        img_path = image_map.get(gorder)

        if img_path is not None:
            try:
                img_src = Image.open(img_path).convert("RGB")
                img_fit = fit_image_to_panel(img_src, pw, ph)
                canvas.paste(img_fit, (px, py))
                placed += 1
            except Exception as exc:
                print(f"  ⚠️ Lỗi đọc ảnh '{img_path.name}': {exc}")
                draw.rectangle([px, py, px + pw, py + ph], fill=EMPTY_PANEL_BG)
                skipped += 1
        else:
            # Không có ảnh → khung trống tối
            draw.rectangle([px, py, px + pw, py + ph], fill=EMPTY_PANEL_BG)

            # Hiển thị nhãn "Khung #N" ở giữa
            font = _load_font(max(10, min(pw, ph) // 8))
            label = f"#{gorder}"
            bb = draw.textbbox((0, 0), label, font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            tx = px + (pw - tw) // 2
            ty = py + (ph - th) // 2
            if pw > 20 and ph > 20:
                draw.text((tx, ty), label, font=font, fill=EMPTY_LABEL_FG)

        # Vẽ viền trên mỗi panel
        draw.rectangle(
            [px, py, px + pw, py + ph],
            outline=BORDER_COLOR,
            width=border_px,
        )

    # ── Header trang ─────────────────────────────────────────────────────────
    header_h = max(28, output_px_h // 30)
    font_hdr = _load_font(max(11, header_h - 6))
    header_txt = (
        f"Trang {page_data['page_number']}  ·  "
        f"{page_data['panels_count']} khung  ·  "
        f"{placed} ảnh / {len(panels)} khung"
    )
    draw.rectangle([0, 0, output_px_w, header_h], fill=(15, 15, 15))
    hbb = draw.textbbox((0, 0), header_txt, font=font_hdr)
    htx = (output_px_w - (hbb[2] - hbb[0])) // 2
    hty = (header_h - (hbb[3] - hbb[1])) // 2
    draw.text((htx, hty), header_txt, font=font_hdr, fill=(230, 230, 230))

    return canvas, placed, skipped


# ── Pipeline chính ────────────────────────────────────────────────────────────

def compose_all(
    json_path: str,
    image_dir: str,
    out_dir: str      = "output",
    scale: float      = 1.0,
    fmt: str          = "png",
    page_filter: int  = None,
    bg_color: tuple   = PAGE_BG,
):
    """
    Đọc JSON layout + folder ảnh → xuất trang truyện tranh với ảnh thật.

    Args:
        json_path:    Đường dẫn file JSON layout.
        image_dir:    Folder chứa ảnh (sắp xếp theo tên số).
        out_dir:      Thư mục lưu ảnh output.
        scale:        Tỉ lệ kích thước (1.0 = coord full res).
        fmt:          'png' hoặc 'jpg'.
        page_filter:  Nếu set, chỉ render trang đó.
        bg_color:     Màu nền trang (RGB tuple).
    """
    # ── Đọc JSON ──────────────────────────────────────────────────────────────
    data  = json.loads(Path(json_path).read_text(encoding="utf-8"))
    meta  = data["meta"]
    pages = data["pages"]

    coord_w = float(meta["coord_w"])
    coord_h = float(meta["coord_h"])
    total_panels = int(meta["total_panels"])

    # ── Thu thập ảnh ──────────────────────────────────────────────────────────
    all_images = collect_images(image_dir)
    n_images   = len(all_images)

    # Ánh xạ global_order → Path  (1-indexed)
    image_map: dict[int, Path] = {}
    for idx, img_path in enumerate(all_images, start=1):
        image_map[idx] = img_path

    # ── Cài đặt output ────────────────────────────────────────────────────────
    out_w     = max(200, int(coord_w * scale))
    out_h     = max(200, int(coord_h * scale))
    border_px = max(2, int(out_w * 0.003))

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ext = fmt.lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg"):
        ext = "png"

    print(f"\n{'='*60}")
    print(f"  Pipeline 3 – Bỏ Ảnh Vào Khung")
    print(f"{'='*60}")
    print(f"  File JSON    : {json_path}")
    print(f"  Folder ảnh   : {image_dir}  ({n_images} ảnh)")
    print(f"  Tổng khung   : {total_panels}")
    if n_images < total_panels:
        print(f"  ⚠️  Số ảnh ({n_images}) ít hơn số khung ({total_panels})"
              f" → {total_panels - n_images} khung cuối để trống")
    elif n_images > total_panels:
        print(f"  ℹ️  Số ảnh ({n_images}) nhiều hơn số khung ({total_panels})"
              f" → {n_images - total_panels} ảnh cuối bị bỏ qua")
    print(f"  Coord space  : {coord_w:.0f} × {coord_h:.0f}")
    print(f"  Ảnh output   : {out_w} × {out_h} px  (scale={scale})")
    print(f"  Thư mục out  : {out_dir}/")
    print(f"{'='*60}\n")

    rendered       = []
    total_placed   = 0
    total_skipped  = 0

    for page in pages:
        pnum = page["page_number"]
        if page_filter is not None and pnum != page_filter:
            continue

        img, placed, skipped = render_page_with_images(
            page_data    = page,
            coord_w      = coord_w,
            coord_h      = coord_h,
            output_px_w  = out_w,
            output_px_h  = out_h,
            image_map    = image_map,
            border_px    = border_px,
            bg_color     = bg_color,
        )

        fname = f"page_{pnum:03d}.{ext}"
        fpath = Path(out_dir) / fname
        save_kwargs = {"quality": 95} if ext in ("jpg", "jpeg") else {}
        img.save(str(fpath), **save_kwargs)
        rendered.append(str(fpath))

        total_placed  += placed
        total_skipped += skipped

        panels_in_page = page["panels_count"]
        g_start = page["panels"][0]["global_order"]  if page["panels"] else "-"
        g_end   = page["panels"][-1]["global_order"] if page["panels"] else "-"
        status  = f"{placed}/{panels_in_page} ảnh"
        print(f"  ✅ Trang {pnum:03d}: {status}  "
              f"(khung #{g_start}–#{g_end})  →  {fpath}")

    print(f"\n{'='*60}")
    print(f"  Đã đặt  : {total_placed} ảnh vào khung")
    if total_skipped:
        print(f"  Lỗi     : {total_skipped} ảnh không đọc được")
    print(f"  Xuất    : {len(rendered)} trang  →  '{out_dir}/'")
    print(f"{'='*60}\n")

    return rendered


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_color(s: str) -> tuple:
    """'255,255,255' → (255, 255, 255)"""
    try:
        parts = [int(x.strip()) for x in s.split(",")]
        if len(parts) == 3:
            return tuple(parts)
    except Exception:
        pass
    raise argparse.ArgumentTypeError(
        f"Màu không hợp lệ: '{s}'. Dùng định dạng R,G,B (vd: 255,255,255)"
    )


def main():
    p = argparse.ArgumentParser(
        description="Bỏ ảnh vào khung từ JSON layout  (Pipeline 3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python compose_pages.py layout.json images/
  python compose_pages.py layout.json images/ --out-dir output --scale 1.0
  python compose_pages.py layout.json images/ --page 2 --format jpg
  python compose_pages.py layout.json images/ --bg-color 255,255,255
        """,
    )
    p.add_argument("json_file",   type=str,
                   help="Đường dẫn file JSON layout (từ generate_layout.py)")
    p.add_argument("image_dir",   type=str,
                   help="Folder chứa ảnh (sắp xếp theo tên số: 1.jpg, 2.png, ...)")
    p.add_argument("--out-dir",   type=str, default="output",
                   help="Thư mục lưu ảnh kết quả (mặc định: output/)")
    p.add_argument("--scale",     type=float, default=1.0,
                   help="Tỉ lệ kích thước ảnh (mặc định: 1.0 = full res)")
    p.add_argument("--format",    type=str, default="png", choices=["png", "jpg"],
                   help="Định dạng ảnh đầu ra (mặc định: png)")
    p.add_argument("--page",      type=int, default=None,
                   help="Chỉ render một trang cụ thể (mặc định: tất cả)")
    p.add_argument("--bg-color",  type=_parse_color, default=PAGE_BG,
                   metavar="R,G,B",
                   help="Màu nền trang RGB (mặc định: 30,30,30)")

    args = p.parse_args()

    if not Path(args.json_file).exists():
        print(f"[ERROR] Không tìm thấy file JSON: {args.json_file}")
        sys.exit(1)

    compose_all(
        json_path   = args.json_file,
        image_dir   = args.image_dir,
        out_dir     = args.out_dir,
        scale       = args.scale,
        fmt         = args.format,
        page_filter = args.page,
        bg_color    = args.bg_color,
    )


if __name__ == "__main__":
    main()
