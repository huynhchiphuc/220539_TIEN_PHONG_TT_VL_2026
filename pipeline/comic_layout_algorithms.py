"""
comic_layout_algorithms.py
==========================
Chứa thuật toán sinh layout panel cho pipeline.

Chỉ export:
    create_auto_frame_layout()  ← dùng bởi generate_layout.py
"""

import math as _math
import random
from dataclasses import dataclass as _dc

# ── Giới hạn aspect ratio cứng ────────────────────────────────────────────────
# Panel phải nằm trong khoảng này (w/h).
# < 0.56 ≈ panel dọc quá dài (rộng < 56% chiều cao) → bất hợp lý
# > 2.20 ≈ panel ngang quá dẹt → bất hợp lý
_HARD_MIN_AR = 0.56
_HARD_MAX_AR = 2.20


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

    Thuật toán: Recursive polygon subdivision với đường cắt vuông góc.
    Mọi panel đầu ra đảm bảo aspect ratio nằm trong [HARD_MIN_AR, HARD_MAX_AR].

    Args:
        target_count:  số panel cần tạo
        coord_w/h:     không gian toạ độ (pixel)
        diagonal_prob: cường độ ngẫu nhiên khi chia (0..1)
        gutter:        độ rộng rãnh giữa panel (px trong coord space)
        seed:          random seed (None = random thực sự)

    Returns:
        list[list[tuple[float, float]]]: mỗi phần tử là danh sách (x, y)
        vertices trong coord space [0..coord_w] x [0..coord_h] cho 1 panel.
    """
    _rng = random.Random(seed)
    # Panel tối thiểu phải chiếm ít nhất 18% chiều rộng/cao trang
    # (giảm từ 12% → 18% để buộc các lần cắt phải cân bằng hơn)
    _min_panel_w = max(100.0, coord_w * 0.18)
    _min_panel_h = max(100.0, coord_h * 0.18)
    _ideal_aspect = max(0.55, min(2.1, coord_w / max(1e-6, coord_h)))

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

    # ── Helpers hình học ──────────────────────────────────────────────────────

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

    # ── Kiểm tra AR của một polygon ──────────────────────────────────────────

    def _get_ar(poly) -> float:
        x0, y0, x1, y1 = poly.bbox()
        w = max(1e-6, x1 - x0)
        h = max(1e-6, y1 - y0)
        return w / h

    def _ar_ok(poly) -> bool:
        """Trả về True nếu panel có aspect ratio hợp lệ (không quá dài/dẹt)."""
        ar = _get_ar(poly)
        return _HARD_MIN_AR <= ar <= _HARD_MAX_AR

    # ── Điều kiện để tiếp tục chia ───────────────────────────────────────────

    def _can_split(poly):
        x0, y0, x1, y1 = poly.bbox()
        return ((x1 - x0) >= _min_panel_w * 1.3 and
                (y1 - y0) >= _min_panel_h * 1.3 and
                poly.area() >= _min_panel_w * _min_panel_h)

    # ── Slice một polygon thành 2 ─────────────────────────────────────────────
    # Ratio được thu hẹp về [0.28, 0.72] để tránh cắt quá lệch một bên

    def _slice(poly, ratio=0.5, rand=0.5, axis=None):
        v0, v1, v2, v3 = poly.vertices
        x0, y0, x1, y1 = poly.bbox()
        bw, bh = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        if axis is None:
            if bw > bh * 1.25:    axis = 'vertical'
            elif bh > bw * 1.25:  axis = 'horizontal'
            else:                 axis = 'horizontal' if _rng.random() < 0.5 else 'vertical'

        # Thu hẹp ratio: không cho cắt quá lệch (tránh tạo sliver panels)
        ratio = max(0.28, min(0.72, ratio))
        t1 = ratio
        t2 = t1  # Đường cắt thẳng vuông góc

        if axis == 'horizontal':
            lc, rc = _lerp(v0, v3, t1), _lerp(v1, v2, t2)
            tl, tr, bl, br = _offset_edge(lc, rc, gutter * 0.5)
            return _Poly([v0, v1, tr, tl]), _Poly([bl, br, v2, v3])
        tc, bc = _lerp(v0, v1, t1), _lerp(v3, v2, t2)
        at, ab, bt2, bb = _offset_edge(tc, bc, gutter * 0.5)
        return _Poly([v0, bt2, bb, v3]), _Poly([at, v1, v2, ab])

    # ── Hàm đánh giá "độ xấu" của một panel ─────────────────────────────────

    def _badness(poly) -> float:
        x0, y0, x1, y1 = poly.bbox()
        w, h = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        ar = w / h
        # Điểm cơ bản: lệch xa ideal aspect ratio
        s = abs(_math.log(max(1e-6, ar / _ideal_aspect)))
        # Soft penalty zone bước vào vùng cấm (cách ngưỡng cứng 10%)
        soft_min = _HARD_MIN_AR + 0.10   # = 0.66
        soft_max = _HARD_MAX_AR - 0.10   # = 2.10
        if ar < soft_min:
            s += ((soft_min - ar) / soft_min) * 18.0
        if ar > soft_max:
            s += ((ar - soft_max) / soft_max) * 12.0
        # Penalty kích thước tối thiểu
        if w < _min_panel_w:
            s += ((_min_panel_w - w) / _min_panel_w) * 3.0
        if h < _min_panel_h:
            s += ((_min_panel_h - h) / _min_panel_h) * 3.0
        return s

    # ── Chọn tỉ lệ chia ──────────────────────────────────────────────────────

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

    # ── Tìm cách cắt tốt nhất ────────────────────────────────────────────────

    def _best_split(poly, lq, rq, rand):
        x0, y0, x1, y1 = poly.bbox()
        bw, bh = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
        target = lq / max(1, lq + rq)

        if bw > bh * 1.2:   axes = ['vertical', 'horizontal']
        elif bh > bw * 1.2: axes = ['horizontal', 'vertical']
        else:               axes = ['horizontal', 'vertical']

        candidates = []
        samples = 12 + int(10 * rand)  # thêm mẫu để có nhiều lựa chọn hơn

        for axis in axes:
            for _ in range(samples):
                r = max(0.28, min(0.72, target + _rng.uniform(-0.10, 0.10) * rand))
                try:
                    lp, rp = _slice(poly, ratio=r, rand=rand, axis=axis)
                except Exception:
                    continue

                # ── Hard filter: loại bỏ ngay nếu AR vi phạm giới hạn cứng ──
                if not _ar_ok(lp) or not _ar_ok(rp):
                    continue

                al, ar_ = max(1e-6, lp.area()), max(1e-6, rp.area())
                bal = abs(al / (al + ar_) - target) * 8.0
                qp = (3.0 if lq > 1 and not _can_split(lp) else 0.0) + \
                     (3.0 if rq > 1 and not _can_split(rp) else 0.0)
                score = bal + _badness(lp) + _badness(rp) + qp
                score += _rng.uniform(0.0, 0.20) * rand
                candidates.append((score, lp, rp))

        if not candidates:
            # Fallback: nới lỏng giới hạn AR một chút nếu không tìm được gì
            # (vẫn giữ ngưỡng tuyệt đối thấp hơn 10% so với HARD limit)
            _fallback_min = _HARD_MIN_AR * 0.90
            _fallback_max = _HARD_MAX_AR * 1.10
            for axis in axes:
                for _ in range(samples):
                    r = max(0.30, min(0.70, target + _rng.uniform(-0.08, 0.08)))
                    try:
                        lp, rp = _slice(poly, ratio=r, rand=rand, axis=axis)
                    except Exception:
                        continue
                    if _get_ar(lp) < _fallback_min or _get_ar(rp) < _fallback_min:
                        continue
                    if _get_ar(lp) > _fallback_max or _get_ar(rp) > _fallback_max:
                        continue
                    al, ar_ = max(1e-6, lp.area()), max(1e-6, rp.area())
                    bal = abs(al / (al + ar_) - target) * 8.0
                    score = bal + _badness(lp) + _badness(rp)
                    candidates.append((score, lp, rp))

        if not candidates:
            return None

        candidates.sort(key=lambda c: c[0])
        top_k = min(len(candidates), max(1, 2 + int(4 * rand)))
        w_ = [1.0 / (i + 1) for i in range(top_k)]
        return _rng.choices(candidates[:top_k], weights=w_, k=1)[0][1:]

    # ── Duyệt cây ────────────────────────────────────────────────────────────

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

    # ── Chạy thuật toán ───────────────────────────────────────────────────────

    root_poly = _Poly([
        _Pt(4.0, 4.0), _Pt(coord_w - 4.0, 4.0),
        _Pt(coord_w - 4.0, coord_h - 4.0), _Pt(4.0, coord_h - 4.0),
    ])
    root = _Tree(root_poly)
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
