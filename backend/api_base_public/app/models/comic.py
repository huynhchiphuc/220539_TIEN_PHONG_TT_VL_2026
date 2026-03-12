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
    aspect_ratio: str = 'auto'
    margin: int = Field(default=40, ge=0, le=200)
    gap: int = Field(default=30, ge=0, le=100)
    single_page_mode: bool = False
    auto_page_size: bool = True
