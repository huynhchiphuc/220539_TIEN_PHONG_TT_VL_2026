"""
Service xử lý tạo khung truyện tự động (Auto Frame).

Module này tách biệt toàn bộ logic render ảnh và lưu DB
ra khỏi router, tuân thủ nguyên tắc Single Responsibility.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from app.services.comic.file_ops import OUTPUT_FOLDER, UPLOAD_FOLDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESOLUTION_MAP: dict[str, int] = {
    "1K": 1000,
    "2K": 2000,
    "4K": 4000,
}

ASPECT_RATIO_MAP: dict[str, tuple[int, int]] = {
    "1:1": (1, 1),
    "2:3": (2, 3),
    "3:4": (3, 4),
    "4:5": (4, 5),
    "9:16": (9, 16),
}

DEFAULT_RESOLUTION = "2K"
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_BORDER_RATIO = 0.003
DEFAULT_GUTTER_BASE = 6.0
DEFAULT_GUTTER_RANGE = 18.0


# ---------------------------------------------------------------------------
# Font loading helper
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Tải font chữ với fallback an toàn trên mọi hệ điều hành.

    Args:
        size: Kích thước font (px).

    Returns:
        Font object của PIL.
    """
    for font_name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except IOError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# AutoFrameService
# ---------------------------------------------------------------------------

class AutoFrameService:
    """Service tạo khung truyện trắng tự động theo cấu hình.

    Tách toàn bộ logic render ảnh và lưu cơ sở dữ liệu
    ra khỏi router để tuân thủ Single Responsibility Principle.
    """

    @staticmethod
    def compute_page_dimensions(
        resolution: str,
        aspect_ratio: str,
    ) -> tuple[int, int, float, float]:
        """Tính kích thước trang (pixel) và hệ tọa độ logic.

        Args:
            resolution: Mức độ phân giải (``"1K"``, ``"2K"``, ``"4K"``).
            aspect_ratio: Tỉ lệ khung hình (ví dụ: ``"9:16"``).

        Returns:
            Tuple ``(page_width, page_height, coord_w, coord_h)``.
        """
        base_width = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP[DEFAULT_RESOLUTION])
        ratio_w, ratio_h = ASPECT_RATIO_MAP.get(aspect_ratio, ASPECT_RATIO_MAP[DEFAULT_ASPECT_RATIO])
        page_width = base_width
        page_height = int(base_width * ratio_h / ratio_w)
        coord_w = 1000.0
        coord_h = max(500.0, coord_w * (ratio_h / ratio_w))
        return page_width, page_height, coord_w, coord_h

    @staticmethod
    def render_page(
        panels_vertices: list,
        page_width: int,
        page_height: int,
        coord_w: float,
        coord_h: float,
        border_width: int,
        draw_panel_numbers: bool,
        panel_number_font_scale: float,
    ) -> tuple[Image.Image, list[dict]]:
        """Render một trang khung truyện trắng và thu thập metadata panel.

        Args:
            panels_vertices: Danh sách tọa độ đỉnh (logic) của từng panel.
            page_width: Chiều rộng trang (px).
            page_height: Chiều cao trang (px).
            coord_w: Chiều rộng hệ tọa độ logic.
            coord_h: Chiều cao hệ tọa độ logic.
            border_width: Độ dày đường viền (px).
            draw_panel_numbers: Có vẽ số thứ tự panel không.
            panel_number_font_scale: Hệ số phóng to/thu nhỏ font số panel.

        Returns:
            Tuple gồm ``(canvas, panel_entries)`` — ảnh PIL và metadata của trang.
        """
        sx = page_width / coord_w
        sy = page_height / coord_h

        canvas = Image.new("RGB", (page_width, page_height), "white")
        draw = ImageDraw.Draw(canvas)

        radius = max(10, int(page_width * 0.012 * panel_number_font_scale))
        font_size = int(radius * 1.5)
        font = _load_font(font_size)

        panel_entries: list[dict] = []

        for panel_idx, vertices in enumerate(panels_vertices, 1):
            pts = [
                (
                    int(max(0, min(page_width, x * sx))),
                    int(max(0, min(page_height, y * sy))),
                )
                for x, y in vertices
            ]
            if len(pts) >= 3:
                draw.polygon(pts, fill="white", outline="black", width=border_width)

                if draw_panel_numbers:
                    cx = int(sum(p[0] for p in pts) / len(pts))
                    cy = int(sum(p[1] for p in pts) / len(pts))
                    draw.ellipse(
                        (cx - radius, cy - radius, cx + radius, cy + radius),
                        fill="#111111",
                        outline="white",
                        width=max(1, border_width // 2),
                    )
                    draw.text((cx, cy), str(panel_idx), fill="white", anchor="mm", font=font)

            # Thu thập metadata
            scaled_vertices = []
            min_x = min_y = float("inf")
            max_x = max_y = float("-inf")
            for x, y in vertices:
                px = float(max(0, min(page_width, x * sx)))
                py = float(max(0, min(page_height, y * sy)))
                scaled_vertices.append({"x": px, "y": py})
                min_x = min(min_x, px)
                min_y = min(min_y, py)
                max_x = max(max_x, px)
                max_y = max(max_y, py)

            panel_entries.append(
                {
                    "panel_id": panel_idx,
                    "panel_order": panel_idx,
                    "vertices": scaled_vertices,
                    "bbox": {
                        "x": min_x,
                        "y": min_y,
                        "w": max(0.0, max_x - min_x),
                        "h": max(0.0, max_y - min_y),
                    },
                }
            )

        return canvas, panel_entries

    @staticmethod
    def generate_frames(
        session_id: str,
        user_id: int,
        panels_per_page: int,
        pages_count: int,
        diagonal_prob: float,
        resolution: str,
        aspect_ratio: str,
        draw_panel_numbers: bool,
        panel_number_font_scale: float,
    ) -> dict[str, Any]:
        """Tạo toàn bộ trang khung truyện trắng và lưu vào disk.

        Args:
            session_id: ID session do router sinh (``uuid4().hex``).
            user_id: ID người dùng (dùng khi lưu DB).
            panels_per_page: Số panel mỗi trang.
            pages_count: Số trang cần tạo.
            diagonal_prob: Xác suất dùng đường chéo khi chia panel (0–1).
            resolution: Mức phân giải (``"1K"``, ``"2K"``, ``"4K"``).
            aspect_ratio: Tỉ lệ khung hình (ví dụ: ``"9:16"``).
            draw_panel_numbers: Có vẽ số thứ tự panel không.
            panel_number_font_scale: Hệ số phóng to/thu nhỏ font số panel.

        Returns:
            Dict kết quả gồm:
            - ``session_id``: ID session đã dùng.
            - ``generated_files``: danh sách tên file đã tạo.
            - ``pages_layout``: metadata layout của từng trang.
            - ``output_folder``: đường dẫn thư mục output.
            - ``upload_folder``: đường dẫn thư mục upload.

        Raises:
            ImportError: Nếu comic engine chưa được cài đặt.
            Exception: Nếu có lỗi khi tạo layout hoặc render.
        """
        try:
            from app.services.comic.comic_book_auto_fill import create_auto_frame_layout
        except ImportError as exc:
            raise ImportError(f"Comic engine unavailable: {exc}") from exc

        if session_id is None:
            session_id = uuid4().hex

        upload_folder = os.path.join(UPLOAD_FOLDER, session_id)
        output_folder = os.path.join(OUTPUT_FOLDER, session_id)
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)

        page_width, page_height, coord_w, coord_h = AutoFrameService.compute_page_dimensions(
            resolution, aspect_ratio
        )
        border_width = max(2, int(page_width * DEFAULT_BORDER_RATIO))
        gutter = max(
            DEFAULT_GUTTER_BASE,
            min(30.0, DEFAULT_GUTTER_BASE + DEFAULT_GUTTER_RANGE * diagonal_prob),
        )

        generated_files: list[str] = []
        pages_layout: list[dict] = []

        for page_idx in range(1, pages_count + 1):
            panels_vertices = create_auto_frame_layout(
                target_count=panels_per_page,
                coord_w=coord_w,
                coord_h=coord_h,
                diagonal_prob=diagonal_prob,
                gutter=gutter,
            )

            canvas, panel_entries = AutoFrameService.render_page(
                panels_vertices=panels_vertices,
                page_width=page_width,
                page_height=page_height,
                coord_w=coord_w,
                coord_h=coord_h,
                border_width=border_width,
                draw_panel_numbers=draw_panel_numbers,
                panel_number_font_scale=panel_number_font_scale,
            )

            # Thêm thông tin page_number vào từng panel entry
            for entry in panel_entries:
                entry["page_number"] = page_idx

            pages_layout.append(
                {
                    "page_number": page_idx,
                    "width": page_width,
                    "height": page_height,
                    "panels_count": len(panel_entries),
                    "reading_direction": "ltr",
                    "panel_numbering": bool(draw_panel_numbers),
                    "panels": panel_entries,
                }
            )

            page_name = f"page_{page_idx:03d}.jpg"
            save_path = os.path.join(output_folder, page_name)
            canvas.save(save_path, quality=95)
            canvas.close()
            generated_files.append(page_name)

            logger.debug("Rendered page %d/%d → %s", page_idx, pages_count, page_name)

        return {
            "session_id": session_id,
            "generated_files": generated_files,
            "pages_layout": pages_layout,
            "output_folder": output_folder,
            "upload_folder": upload_folder,
        }

    @staticmethod
    def save_to_db(
        session_id: str,
        user_id: int,
        panels_per_page: int,
        diagonal_prob: float,
        resolution: str,
        aspect_ratio: str,
        upload_folder: str,
        output_folder: str,
        generated_files: list[str],
        pages_layout: list[dict],
    ) -> int | None:
        """Lưu session và các trang vào database.

        Args:
            session_id: ID session.
            user_id: ID người dùng.
            panels_per_page: Số panel mỗi trang.
            diagonal_prob: Xác suất đường chéo.
            resolution: Mức phân giải.
            aspect_ratio: Tỉ lệ khung hình.
            upload_folder: Đường dẫn thư mục upload.
            output_folder: Đường dẫn thư mục output.
            generated_files: Danh sách tên file đã tạo.
            pages_layout: Metadata layout từng trang.

        Returns:
            ``project_id`` nếu lưu thành công, ``None`` nếu thất bại.
        """
        from app.db.mysql_connection import get_mysql_connection

        project_id = None
        try:
            conn = get_mysql_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO upload_sessions "
                "(session_id, user_id, total_images, upload_folder_path, status, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, user_id, 0, upload_folder, "completed", datetime.now()),
            )

            cursor.execute(
                """
                INSERT INTO comic_projects
                (session_id, user_id, project_name, layout_mode, panels_per_page, diagonal_prob,
                 resolution, aspect_ratio, reading_direction, output_folder_path, total_pages,
                 status, processing_completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    user_id,
                    f"Auto Frame {session_id[:8]}",
                    "advanced",
                    panels_per_page,
                    diagonal_prob,
                    resolution,
                    aspect_ratio,
                    "ltr",
                    output_folder,
                    len(generated_files),
                    "completed",
                    datetime.now(),
                ),
            )
            project_id = cursor.lastrowid

            for page_meta, page_name in zip(pages_layout, generated_files):
                cursor.execute(
                    """
                    INSERT INTO comic_pages
                    (project_id, page_number, page_type, panels_count,
                     layout_structure, output_image_path, width, height)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        project_id,
                        page_meta["page_number"],
                        "content",
                        page_meta["panels_count"],
                        json.dumps(page_meta, ensure_ascii=False),
                        None,
                        page_meta["width"],
                        page_meta["height"],
                    ),
                )

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Auto-frames session %s saved to DB (project_id=%s)", session_id, project_id)
        except Exception as exc:
            logger.warning("DB save failed for auto-frames session=%s: %s", session_id, exc)

        return project_id
