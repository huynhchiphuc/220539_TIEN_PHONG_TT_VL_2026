"""
comic_utils.py  –  Tiện ích cho Pipeline
Chứa hàm phân loại aspect ratio dùng bởi generate_layout.py.
"""


def _classify_ar(aspect: float) -> str:
    """Phân loại aspect ratio thành nhãn mô tả."""
    if aspect > 2.8:   return 'ultra_panoramic'
    if aspect > 2.2:   return 'panoramic'
    if aspect > 1.8:   return 'cinema_landscape'
    if aspect > 1.5:   return 'wide_landscape'
    if aspect > 1.25:  return 'landscape'
    if aspect > 1.05:  return 'wide_square'
    if aspect >= 0.95: return 'square'
    if aspect >= 0.8:  return 'tall_square'
    if aspect >= 0.6:  return 'portrait'
    if aspect >= 0.45: return 'tall_portrait'
    if aspect >= 0.3:  return 'thin_portrait'
    return 'ultrathin_portrait'
