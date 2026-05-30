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
    _min_panel_w = max(80.0, coord_w * 0.12)
    _min_panel_h = max(80.0, coord_h * 0.12)
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
        t2 = t1
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
    # Dùng page_rand = 0.5 cố định → chia panel đều
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
