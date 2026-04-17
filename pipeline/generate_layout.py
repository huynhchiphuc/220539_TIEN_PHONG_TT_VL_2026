"""
generate_layout.py
==================
Pipeline sinh JSON layout trang truyện tranh.

Nhận đầu vào:  số trang, số khung/trang, tỉ lệ trang (aspect ratio)
Xuất đầu ra:   file JSON chứa cấu trúc khung của tất cả trang

Cấu trúc JSON đầu ra:
{
  "meta": {
    "total_pages"    : int,
    "panels_per_page": int,
    "total_panels"   : int,
    "page_aspect"    : str,          // "9:16" | "2:3" | "1:1" | ...
    "coord_w"        : float,
    "coord_h"        : float,
    "generated_at"   : str           // ISO timestamp
  },
  "pages": [
    {
      "page_number"  : int,
      "panels_count" : int,
      "panels"       : [
        {
          "global_order"  : int,     // thứ tự tuyệt đối trên toàn bộ truyện
          "page_order"    : int,     // thứ tự trong trang
          "page_number"   : int,
          "aspect_ratio"  : float,   // w / h của khung
          "aspect_label"  : str,     // "landscape" | "portrait" | "square" | ...
          "width_ratio"   : float,   // % chiều rộng trang (0-1)
          "height_ratio"  : float,   // % chiều cao trang (0-1)
          "bbox": {
            "x": float, "y": float,  // góc trái-trên (px trong coord space)
            "w": float, "h": float   // kích thước (px trong coord space)
          },
          "vertices": [              // 4 đỉnh tứ giác [x, y]
            [x0, y0], [x1, y1], [x2, y2], [x3, y3]
          ]
        },
        ...
      ]
    },
    ...
  ]
}

Chạy:
    python generate_layout.py --pages 5 --panels 6 --aspect 9:16 --out layout.json
    python generate_layout.py --pages 3 --panels 4 --aspect 2:3
"""

import argparse
import json
import math
import sys
import io
from datetime import datetime
from pathlib import Path

# Fix encoding trên Windows (chạy không cần PYTHONUTF8=1)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── Import layout engine ───────────────────────────────────────────────────────
try:
    from comic_layout_algorithms import create_auto_frame_layout
    from comic_utils import _classify_ar
except ImportError as e:
    print(f"[ERROR] Không import được engine: {e}")
    print("Hãy chạy script này trong thư mục pipeline/")
    sys.exit(1)

# ── Giá trị mặc định ──────────────────────────────────────────────────────────
ASPECT_PRESETS = {
    "9:16": (9, 16),
    "2:3":  (2, 3),
    "3:4":  (3, 4),
    "4:5":  (4, 5),
    "1:1":  (1, 1),
    "16:9": (16, 9),
}
DEFAULT_COORD_W = 1000.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_aspect(aspect_str: str) -> tuple[int, int]:
    """Phân tích chuỗi 'W:H' → (W, H). Hỗ trợ cả preset lẫn giá trị tùy ý."""
    if aspect_str in ASPECT_PRESETS:
        return ASPECT_PRESETS[aspect_str]
    parts = aspect_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Sai định dạng aspect ratio: '{aspect_str}'. Dùng 'W:H' (vd: 9:16).")
    return int(parts[0]), int(parts[1])


def compute_coord_dimensions(aspect_w: int, aspect_h: int) -> tuple[float, float]:
    """Tính hệ tọa độ logic: coord_w cố định = 1000, coord_h theo tỉ lệ."""
    coord_w = DEFAULT_COORD_W
    coord_h = coord_w * aspect_h / aspect_w
    return coord_w, coord_h


def bbox_from_vertices(vertices: list) -> dict:
    """Tính bounding box từ danh sách đỉnh."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return {
        "x": round(x_min, 4),
        "y": round(y_min, 4),
        "w": round(x_max - x_min, 4),
        "h": round(y_max - y_min, 4),
    }


def classify_panel_aspect(bbox: dict) -> tuple[float, str]:
    """Tính tỉ lệ khung và nhãn phân loại từ bbox."""
    w = bbox["w"]
    h = bbox["h"]
    if h <= 0:
        return 1.0, "square"
    ar = round(w / h, 4)
    label = _classify_ar(ar)
    return ar, label


# ── Engine chính ──────────────────────────────────────────────────────────────

def generate_layout(
    total_pages: int,
    panels_per_page: int,
    aspect_str: str = "9:16",
    seed: int = None,
) -> dict:
    """
    Sinh cấu trúc layout cho toàn bộ truyện.

    Args:
        total_pages:     Tổng số trang.
        panels_per_page: Số khung mỗi trang.
        aspect_str:      Tỉ lệ trang (vd: '9:16').
        seed:            Random seed (None = ngẫu nhiên).

    Returns:
        dict: Toàn bộ dữ liệu layout theo cấu trúc JSON đã mô tả.
    """
    aspect_w, aspect_h = parse_aspect(aspect_str)
    coord_w, coord_h   = compute_coord_dimensions(aspect_w, aspect_h)

    # Gutter tự động ~ 1% chiều rộng
    gutter = max(6.0, coord_w * 0.010)

    total_panels_generated = 0
    pages_out = []

    print(f"\n{'='*60}")
    print(f"  Pipeline Sinh Layout Trang Truyện")
    print(f"{'='*60}")
    print(f"  Trang       : {total_pages}")
    print(f"  Khung/trang : {panels_per_page}")
    print(f"  Tỉ lệ trang : {aspect_str}  ({aspect_w}:{aspect_h})")
    print(f"  Coord space : {coord_w:.0f} x {coord_h:.0f}")
    print(f"  Gutter      : {gutter:.1f}")
    print(f"{'='*60}\n")

    for page_idx in range(1, total_pages + 1):
        page_seed = (seed + page_idx) if seed is not None else None

        # Sinh vertices các panel (hình chữ nhật, không xéo)
        panels_vertices: list[list[tuple]] = create_auto_frame_layout(
            target_count=panels_per_page,
            coord_w=coord_w,
            coord_h=coord_h,
            diagonal_prob=0.0,     # hoàn toàn tắt đường chéo
            gutter=gutter,
            seed=page_seed,
        )

        panels_out = []
        for panel_order, vertices in enumerate(panels_vertices, start=1):
            total_panels_generated += 1
            bbox = bbox_from_vertices(vertices)
            ar, ar_label = classify_panel_aspect(bbox)

            panels_out.append({
                "global_order"  : total_panels_generated,
                "page_order"    : panel_order,
                "page_number"   : page_idx,
                "aspect_ratio"  : ar,
                "aspect_label"  : ar_label,
                "width_ratio"   : round(bbox["w"] / coord_w, 6),
                "height_ratio"  : round(bbox["h"] / coord_h, 6),
                "bbox"          : bbox,
                "vertices"      : [[round(x, 4), round(y, 4)] for x, y in vertices],
            })

        pages_out.append({
            "page_number"  : page_idx,
            "panels_count" : len(panels_out),
            "panels"       : panels_out,
        })

        print(f"  ✅ Trang {page_idx:03d}/{total_pages}: {len(panels_out)} khung  "
              f"→ global #{total_panels_generated - len(panels_out) + 1}"
              f" – #{total_panels_generated}")

    result = {
        "meta": {
            "total_pages"     : total_pages,
            "panels_per_page" : panels_per_page,
            "total_panels"    : total_panels_generated,
            "page_aspect"     : aspect_str,
            "coord_w"         : coord_w,
            "coord_h"         : coord_h,
            "generated_at"    : datetime.now().isoformat(timespec="seconds"),
        },
        "pages": pages_out,
    }

    print(f"\n{'='*60}")
    print(f"  Tổng khung sinh được : {total_panels_generated}")
    print(f"{'='*60}\n")
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Sinh JSON layout khung truyện tranh.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python generate_layout.py --pages 5 --panels 6 --aspect 9:16
  python generate_layout.py -p 10 -n 4 -a 2:3 -o my_layout.json --seed 42
  python generate_layout.py --pages 1 --panels 3 --aspect 1:1 --pretty
        """,
    )
    p.add_argument("-p", "--pages",   type=int, default=3,
                   help="Số trang cần sinh (mặc định: 3)")
    p.add_argument("-n", "--panels",  type=int, default=5,
                   help="Số khung mỗi trang (mặc định: 5)")
    p.add_argument("-a", "--aspect",  type=str, default="9:16",
                   help="Tỉ lệ khung hình W:H (mặc định: 9:16). "
                        "Preset hỗ trợ: 9:16, 2:3, 3:4, 4:5, 1:1, 16:9")
    p.add_argument("-o", "--out",     type=str, default="",
                   help="Tên file JSON đầu ra (mặc định: layout_<pages>p_<panels>f_<aspect>.json)")
    p.add_argument("--seed",          type=int, default=None,
                   help="Random seed để tái tạo kết quả (mặc định: ngẫu nhiên)")
    p.add_argument("--pretty",        action="store_true",
                   help="In JSON dạng đẹp (indent=2), mặc định là minified")
    return p


def main():
    args = build_parser().parse_args()

    # Validate
    if args.pages < 1:
        print("[ERROR] --pages phải >= 1"); sys.exit(1)
    if args.panels < 1:
        print("[ERROR] --panels phải >= 1"); sys.exit(1)

    # Tên file output mặc định
    out_path = args.out
    if not out_path:
        safe_aspect = args.aspect.replace(":", "x")
        out_path = f"layout_{args.pages}p_{args.panels}f_{safe_aspect}.json"

    # Sinh layout
    data = generate_layout(
        total_pages=args.pages,
        panels_per_page=args.panels,
        aspect_str=args.aspect,
        seed=args.seed,
    )

    # Ghi file
    indent = 2 if args.pretty else None
    Path(out_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
    print(f"  📄 Đã ghi file: {out_path}")
    print(f"  📦 Kích thước : {Path(out_path).stat().st_size:,} bytes\n")


if __name__ == "__main__":
    main()
