"""
render_preview.py
=================
Đọc file JSON layout và xuất ảnh demo từng trang.

Mỗi trang → 1 file ảnh (PNG/JPG) với:
  - Nền trắng
  - Khung đen rõ ràng (hình chữ nhật vuông góc)
  - Số thứ tự global + page, tỉ lệ aspect, nhãn loại khung
  - Màu nền pastel xen kẽ để phân biệt khung

Cách chạy:
    python render_preview.py layout_5p_6f_9x16.json
    python render_preview.py layout.json --out-dir preview_out --scale 0.4 --format png
    python render_preview.py layout.json --page 1          # chỉ render trang 1
"""

import argparse
import io
import json
import math
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

# ── Bảng màu pastel cho từng khung ───────────────────────────────────────────
PANEL_COLORS = [
    (214, 234, 248),   # xanh dương nhạt
    (213, 245, 227),   # xanh lá nhạt
    (253, 235, 208),   # cam nhạt
    (245, 215, 240),   # tím nhạt
    (255, 249, 196),   # vàng nhạt
    (215, 245, 245),   # cyan nhạt
    (255, 220, 220),   # hồng nhạt
    (230, 220, 255),   # lavender nhạt
    (220, 250, 220),   # mint nhạt
    (255, 235, 200),   # peach nhạt
]
BORDER_COLOR  = (30, 30, 30)      # viền đen đậm
TEXT_COLOR    = (20, 20, 20)      # chữ đen
LABEL_BG      = (30, 30, 30, 180) # nền label (RGBA)
LABEL_TXT     = (255, 255, 255)   # chữ trên label
PAGE_BG       = (240, 240, 240)   # nền trang


def _load_font(size: int):
    """Load font với fallback an toàn."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "verdana.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw) -> list[str]:
    """Bẻ dòng văn bản để vừa với max_width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def render_page(page_data: dict, coord_w: float, coord_h: float,
                output_px_w: int, output_px_h: int,
                border_px: int = 3) -> Image.Image:
    """
    Render một trang thành ảnh PIL.

    Args:
        page_data:    dict trang từ JSON (có key 'panels').
        coord_w/h:    hệ tọa độ logic từ meta.
        output_px_w:  chiều rộng ảnh output (px).
        output_px_h:  chiều cao ảnh output (px).
        border_px:    độ dày viền panel.

    Returns:
        PIL.Image.Image
    """
    sx = output_px_w / coord_w   # scale x: coord → pixel
    sy = output_px_h / coord_h   # scale y: coord → pixel

    canvas = Image.new("RGB", (output_px_w, output_px_h), PAGE_BG)
    draw   = ImageDraw.Draw(canvas, "RGBA")

    panels = page_data.get("panels", [])

    for idx, panel in enumerate(panels):
        color = PANEL_COLORS[idx % len(PANEL_COLORS)]
        bbox  = panel["bbox"]

        # Tọa độ pixel
        px = int(bbox["x"] * sx)
        py = int(bbox["y"] * sy)
        pw = max(1, int(bbox["w"] * sx))
        ph = max(1, int(bbox["h"] * sy))

        # Vẽ nền panel
        draw.rectangle([px, py, px + pw, py + ph], fill=color)

        # Vẽ viền
        draw.rectangle(
            [px, py, px + pw, py + ph],
            outline=BORDER_COLOR,
            width=border_px,
        )

        # ── Nội dung text trong panel ────────────────────────────────────────
        panel_cx = px + pw // 2
        panel_cy = py + ph // 2

        # Font sizes tỉ lệ theo kích thước panel
        base_size = max(12, min(pw, ph) // 8)
        font_big   = _load_font(max(14, base_size))
        font_small = _load_font(max(10, int(base_size * 0.65)))

        # Dòng 1: số thứ tự lớn
        line1 = f"#{panel['global_order']}"
        bb1 = draw.textbbox((0, 0), line1, font=font_big)
        w1, h1 = bb1[2] - bb1[0], bb1[3] - bb1[1]

        # Dòng 2: thứ tự trong trang
        line2 = f"Trang {panel['page_number']}  ·  Khung {panel['page_order']}"
        bb2 = draw.textbbox((0, 0), line2, font=font_small)
        w2, h2 = bb2[2] - bb2[0], bb2[3] - bb2[1]

        # Dòng 3: aspect ratio + label
        line3 = f"{panel['aspect_ratio']}  ({panel['aspect_label']})"
        bb3 = draw.textbbox((0, 0), line3, font=font_small)
        w3, h3 = bb3[2] - bb3[0], bb3[3] - bb3[1]

        # Dòng 4: kích thước tương đối
        line4 = f"W {panel['width_ratio']*100:.1f}%  ×  H {panel['height_ratio']*100:.1f}%"
        bb4 = draw.textbbox((0, 0), line4, font=font_small)
        w4, h4 = bb4[2] - bb4[0], bb4[3] - bb4[1]

        # Dòng 5: file name
        line5 = panel.get("file_name", "no_name")
        bb5 = draw.textbbox((0, 0), line5, font=font_small)
        w5, h5 = bb5[2] - bb5[0], bb5[3] - bb5[1]

        gap = max(2, base_size // 5)
        total_h = h1 + gap + h2 + gap + h3 + gap + h4 + gap + h5

        # Bỏ qua text nếu panel quá nhỏ
        if pw < 40 or ph < 30:
            continue

        # Vẽ text (clip trong panel)
        ty = panel_cy - total_h // 2

        def draw_center(text, font, y_pos, color=TEXT_COLOR):
            bb = draw.textbbox((0, 0), text, font=font)
            tw = bb[2] - bb[0]
            tx = panel_cx - tw // 2
            # Clip ngang
            tx = max(px + 4, min(tx, px + pw - tw - 4))
            # Chỉ vẽ nếu còn nằm trong panel dọc
            if y_pos + (bb[3] - bb[1]) <= py + ph - 4:
                draw.text((tx, y_pos), text, font=font, fill=color)
            return bb[3] - bb[1]

        ty += draw_center(line1, font_big,   ty) + gap
        ty += draw_center(line2, font_small, ty) + gap
        ty += draw_center(line3, font_small, ty) + gap
        ty += draw_center(line4, font_small, ty) + gap
        draw_center(line5, font_small, ty)

    # ── Header trang ─────────────────────────────────────────────────────────
    header_h = max(28, output_px_h // 30)
    font_hdr = _load_font(max(11, header_h - 6))
    header_txt = (
        f"Trang {page_data['page_number']}  ·  "
        f"{page_data['panels_count']} khung"
    )
    draw.rectangle([0, 0, output_px_w, header_h], fill=(30, 30, 30))
    hbb = draw.textbbox((0, 0), header_txt, font=font_hdr)
    htx = (output_px_w - (hbb[2] - hbb[0])) // 2
    hty = (header_h - (hbb[3] - hbb[1])) // 2
    draw.text((htx, hty), header_txt, font=font_hdr, fill=(255, 255, 255))

    return canvas


def render_all(
    json_path: str,
    out_dir: str     = "preview",
    scale: float     = 0.5,
    fmt: str         = "png",
    page_filter: int = None,
):
    """
    Đọc JSON layout và xuất ảnh cho từng trang.

    Args:
        json_path:   Đường dẫn file JSON.
        out_dir:     Thư mục lưu ảnh.
        scale:       Tỉ lệ scale kích thước output (1.0 = coord full res, 0.5 = nhỏ hơn).
        fmt:         'png' hoặc 'jpg'.
        page_filter: Nếu set, chỉ render trang đó.
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    meta = data["meta"]
    pages = data["pages"]

    coord_w = float(meta["coord_w"])
    coord_h = float(meta["coord_h"])

    # Kích thước ảnh output
    out_w = max(200, int(coord_w * scale))
    out_h = max(200, int(coord_h * scale))
    border_px = max(2, int(out_w * 0.003))

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ext = fmt.lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg"):
        ext = "png"

    print(f"\n{'='*56}")
    print(f"  Render Preview từ JSON Layout")
    print(f"{'='*56}")
    print(f"  File JSON    : {json_path}")
    print(f"  Tổng trang   : {meta['total_pages']}")
    print(f"  Tổng khung   : {meta['total_panels']}")
    print(f"  Coord space  : {coord_w:.0f} × {coord_h:.0f}")
    print(f"  Ảnh output   : {out_w} × {out_h} px  (scale={scale})")
    print(f"  Thư mục out  : {out_dir}/")
    print(f"{'='*56}\n")

    rendered = []
    for page in pages:
        pnum = page["page_number"]
        if page_filter is not None and pnum != page_filter:
            continue

        img = render_page(page, coord_w, coord_h, out_w, out_h, border_px)

        fname = f"page_{pnum:03d}.{ext}"
        fpath = Path(out_dir) / fname
        save_kwargs = {"quality": 95} if ext in ("jpg", "jpeg") else {}
        img.save(str(fpath), **save_kwargs)
        rendered.append(str(fpath))

        total_p = page["panels_count"]
        g_start = page["panels"][0]["global_order"]  if page["panels"] else "-"
        g_end   = page["panels"][-1]["global_order"] if page["panels"] else "-"
        print(f"  ✅ Trang {pnum:03d}: {total_p} khung  "
              f"(global #{g_start} – #{g_end})  →  {fpath}")

    print(f"\n  Đã xuất {len(rendered)} ảnh vào thư mục '{out_dir}/'\n")
    return rendered


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Xuất ảnh demo từ file JSON layout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python render_preview.py layout_5p_6f_9x16.json
  python render_preview.py layout.json --out-dir preview --scale 0.4
  python render_preview.py layout.json --page 2 --format jpg
        """,
    )
    p.add_argument("json_file", type=str,
                   help="Đường dẫn file JSON layout (từ generate_layout.py)")
    p.add_argument("--out-dir", type=str, default="preview",
                   help="Thư mục lưu ảnh (mặc định: preview/)")
    p.add_argument("--scale", type=float, default=0.5,
                   help="Tỉ lệ kích thước ảnh so với coord space (mặc định: 0.5)")
    p.add_argument("--format", type=str, default="png", choices=["png", "jpg"],
                   help="Định dạng ảnh đầu ra (mặc định: png)")
    p.add_argument("--page", type=int, default=None,
                   help="Chỉ render một trang cụ thể (mặc định: tất cả)")
    args = p.parse_args()

    if not Path(args.json_file).exists():
        print(f"[ERROR] Không tìm thấy file: {args.json_file}")
        sys.exit(1)

    render_all(
        json_path=args.json_file,
        out_dir=args.out_dir,
        scale=args.scale,
        fmt=args.format,
        page_filter=args.page,
    )


if __name__ == "__main__":
    main()
