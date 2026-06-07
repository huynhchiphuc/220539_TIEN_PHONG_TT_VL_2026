from pydantic import BaseModel, Field
from typing import Optional


class GenerateRequest(BaseModel):
    session_id: str
    layout_mode: str = Field(default='advanced', pattern='^(advanced|simple)$')
    panels_per_page: int = Field(default=5, ge=2, le=10)
    diagonal_prob: float = Field(default=0.3, ge=0.0, le=1.0)
    adaptive_layout: bool = True
    use_smart_crop: bool = False
    reading_direction: str = Field(default='ltr', pattern='^(ltr|rtl)$')
    analyze_shot_type: bool = False
    classify_characters: bool = False
    classify_scenes: bool = False
    use_face_recognition: bool = False
    scene_classification_method: str = Field(default='rule_based', pattern='^(rule_based|ai_model|hybrid)$')
    target_dpi: int = Field(default=150)
    resolution: str = Field(default='2K', pattern='^(1K|2K|4K)$')
    aspect_ratio: str = Field(default='9:16', pattern='^(auto|1:1|2:3|3:4|4:5|9:16)$')
    margin: int = Field(default=40, ge=0, le=200)
    gap: int = Field(default=30, ge=0, le=100)
    single_page_mode: bool = False
    auto_page_size: bool = True
    draw_speech_bubbles_outside: bool = True
    enable_perspective_warp: bool = False
    # ADVANCED mode: kiểm tra tỉ lệ ảnh đầu vào và nghiêng khung nhẹ (1–3 độ)
    frame_tilt_degree: float = Field(default=2.0, ge=1.0, le=3.0)


class AutoFrameRequest(BaseModel):
    panels_per_page: int = Field(default=5, ge=2, le=10)
    diagonal_prob: float = Field(default=0.3, ge=0.0, le=1.0)
    aspect_ratio: str = Field(default='9:16', pattern='^(1:1|2:3|3:4|4:5|9:16)$')
    resolution: str = Field(default='2K', pattern='^(1K|2K|4K)$')
    pages_count: int = Field(default=1, ge=1, le=50)
    draw_panel_numbers: bool = True
    panel_number_font_scale: float = Field(default=1.0, ge=0.5, le=2.0)
