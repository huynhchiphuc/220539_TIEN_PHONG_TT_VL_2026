import math
import random
import itertools
import numpy as np
import matplotlib.patches as patches
from dataclasses import dataclass
from typing import List, Tuple, Callable

from app.services.comic.comic_utils import (
    calculate_adaptive_diagonal_angle,
    PANEL_MAX_ASPECT,
    PANEL_MIN_ASPECT
)

@dataclass
class Point:
    x: float
    y: float
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

        original_vertices = np.array(self.vertices)
        ox_min, oy_min = original_vertices.min(axis=0)
        ox_max, oy_max = original_vertices.max(axis=0)
        min_panel_side = max(1e-6, min(ox_max - ox_min, oy_max - oy_min))
        # Thu nhỏ vừa đủ để tạo khe nhìn rõ nhưng không cắt mạnh vào nội dung/text sát biên.
        inset_gap = min(float(gap), max(0.25, min_panel_side * 0.04))

        try:
            from shapely.geometry import Polygon as ShapelyPolygon
            poly = ShapelyPolygon(self.vertices)
            
            # buffer với giá trị âm thu nhỏ polygon đồng đều từ mọi viền (chuẩn xác toán học)
            # Dùng join_style=2 (mitre) để giữ các góc nhọn của bounding box không bị bo tròn
            shrunk_poly = poly.buffer(-inset_gap, join_style=2)
            
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
            # Vẽ border theo biên ngoài để giảm nguy cơ đè lên chữ trong ảnh.
            polygon = patches.Polygon(original_vertices, linewidth=1.2, 
                                     edgecolor='black', facecolor='none', 
                                     zorder=3, joinstyle='miter')
            ax.add_patch(polygon)

def _make_gutter_quad(ax0, ay0, ax1, ay1,
                      bx0, by0, bx1, by1,
                      gutter: float):
    """
    Tạo 2 cạnh song song cách đường cắt gutter/2 về mỗi phía.
    Trả về (side_A_p0, side_A_p1, side_B_p0, side_B_p1).
    """
    dx = ax1 - ax0
    dy = ay1 - ay0
    # Trung điểm đường cắt (dùng cạnh trên a)
    length = np.hypot(dx, dy)
    if length < 1e-6:
        return (np.array([ax0, ay0]), np.array([ax1, ay1]),
                np.array([bx0, by0]), np.array([bx1, by1]))
    nx, ny = -dy / length, dx / length       # normal hướng vào trong
    half = gutter / 2.0

    def _pt(px, py, sign):
        return np.array([px + sign * nx * half, py + sign * ny * half])

    # side_A: cạnh của panel phía trên (normal âm = hướng lên)
    sA0 = _pt(ax0, ay0, -1)
    sA1 = _pt(ax1, ay1, -1)
    # side_B: cạnh của panel phía dưới (normal dương = hướng xuống)
    sB0 = _pt(bx0, by0, +1)
    sB1 = _pt(bx1, by1, +1)
    return sA0, sA1, sB0, sB1

