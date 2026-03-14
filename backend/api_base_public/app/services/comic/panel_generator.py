"""
Panel Generator Module - Module 3
Mapping scene_type → panel specification (aspect ratio, shape, angle)
Theo yêu cầu: Automatic Comic Page Layout Generation Based on Image Content Analysis
"""

import random
from typing import Dict, List, Tuple


class PanelGenerator:
    """
    Generate panel specifications từ scene_type
    
    Mapping chính xác theo yêu cầu đề bài:
    - close_up: rectangular 3:4 (portrait) 90°
    - dialogue: rectangular 4:3 (landscape) 90°
    - group: rectangular 16:9 (wide) 90°
    - action: dynamic angle <90° (diagonal/triangle)
    - normal: rectangular 1:1 (square) 90°
    """
    
    # Scene → Panel mapping (EXACT theo yêu cầu)
    SCENE_TO_PANEL_MAP = {
        'close_up': {
            'shape_type': 'rectangular',
            'angle_type': '90',
            'aspect_ratio': 3/4,           # Portrait 3:4
            'area_ratio': (0.15, 0.25),    # 15-25% trang (nhỏ)
            'priority': 'high',
            'description': 'Portrait panel cho cận cảnh nhân vật'
        },
        'dialogue': {
            'shape_type': 'rectangular',
            'angle_type': '90',
            'aspect_ratio': 4/3,           # Landscape 4:3
            'area_ratio': (0.20, 0.30),    # 20-30%
            'priority': 'medium',
            'description': 'Landscape panel cho hội thoại'
        },
        'group': {
            'shape_type': 'rectangular',
            'angle_type': '90',
            'aspect_ratio': 16/9,          # Wide 16:9
            'area_ratio': (0.30, 0.45),    # 30-45% (dominant panel)
            'priority': 'dominant',
            'description': 'Wide panel cho nhóm nhân vật'
        },
        'action': {
            'shape_type': 'dynamic',
            'angle_type': '<90',           # Diagonal/triangle
            'aspect_ratio': 'adaptive',    # Giữ nguyên aspect của ảnh
            'area_ratio': (0.25, 0.40),    # 25-40%
            'priority': 'high',
            'description': 'Dynamic angle panel cho hành động'
        },
        'normal': {
            'shape_type': 'rectangular',
            'angle_type': '90',
            'aspect_ratio': 1.0,           # Square 1:1
            'area_ratio': (0.18, 0.28),    # 18-28%
            'priority': 'medium',
            'description': 'Square panel cho cảnh thường'
        }
    }
    
    def __init__(self, seed: int = None):
        """
        Args:
            seed: Random seed cho reproducibility
        """
        if seed is not None:
            random.seed(seed)
        
        self.panel_counter = 0
        self.generation_history = []
    
    def generate_panel(self, scene_type: str, image_aspect: float = None,
                      override_area: float = None) -> Dict:
        """
        Tạo panel spec từ scene_type (EXACT MAPPING theo đề bài)
        
        Args:
            scene_type: str in ['close_up', 'group', 'action', 'dialogue', 'normal']
            image_aspect: float - Aspect ratio của ảnh (width/height), 
                         required cho action panels
            override_area: float - Override area_ratio nếu cần custom
        
        Returns:
            Dict với:
                - panel_id: str
                - scene_type: str
                - shape_type: 'rectangular' | 'dynamic'
                - angle_type: '90' | '<90'
                - aspect_ratio: float
                - area_ratio: float (0-1)
                - priority: 'dominant' | 'high' | 'medium'
                - description: str
        """
        if scene_type not in self.SCENE_TO_PANEL_MAP:
            raise ValueError(
                f"Unknown scene_type: {scene_type}. "
                f"Must be one of {list(self.SCENE_TO_PANEL_MAP.keys())}"
            )
        
        config = self.SCENE_TO_PANEL_MAP[scene_type]
        
        # Generate unique panel ID
        self.panel_counter += 1
        panel_id = f"{scene_type}_{self.panel_counter:04d}"
        
        # Area ratio (random trong range hoặc override)
        if override_area is not None:
            area_ratio = override_area
        else:
            area_min, area_max = config['area_ratio']
            area_ratio = random.uniform(area_min, area_max)
        
        # Aspect ratio (adaptive cho action panels)
        if config['aspect_ratio'] == 'adaptive':
            if image_aspect is None:
                # Fallback cho action panels khi không có image_aspect
                aspect_ratio = 1.5  # Default landscape
            else:
                aspect_ratio = image_aspect  # Giữ nguyên aspect của ảnh
        else:
            aspect_ratio = config['aspect_ratio']
        
        panel_spec = {
            'panel_id': panel_id,
            'scene_type': scene_type,
            'shape_type': config['shape_type'],
            'angle_type': config['angle_type'],
            'aspect_ratio': aspect_ratio,
            'area_ratio': area_ratio,
            'priority': config['priority'],
            'description': config['description']
        }
        
        # Store history
        self.generation_history.append(panel_spec)
        
        return panel_spec
    
    def generate_panels_batch(self, scene_analyses: List[Dict]) -> List[Dict]:
        """
        Tạo panels cho nhiều ảnh từ scene analysis
        
        Args:
            scene_analyses: List[Dict] - Output từ SceneClassifier.classify_batch()
                Mỗi dict phải có:
                    - scene_type: str
                    - image_path: str (optional)
                    - width, height: int (để tính aspect)
        
        Returns:
            List[Dict] - Panel specs cho từng ảnh
        """
        panel_specs = []
        
        for analysis in scene_analyses:
            scene_type = analysis.get('scene_type')
            
            if not scene_type:
                print(f"Warning: No scene_type in analysis, skipping")
                continue
            
            # Calculate image aspect ratio
            width = analysis.get('width', None)
            height = analysis.get('height', None)
            
            if width and height and height > 0:
                image_aspect = width / height
            else:
                image_aspect = None
            
            # Generate panel
            try:
                panel = self.generate_panel(scene_type, image_aspect)
                
                # Add image info to panel
                panel['image_id'] = analysis.get('image_id', None)
                panel['image_path'] = analysis.get('image_path', None)
                
                panel_specs.append(panel)
                
            except Exception as e:
                print(f"Error generating panel for {scene_type}: {e}")
                continue
        
        return panel_specs
    
    def enforce_dominant_panel(self, panel_specs: List[Dict]) -> List[Dict]:
        """
        Đảm bảo có 1 dominant panel (30-45% area)
        
        Logic:
        - Nếu đã có panel priority='dominant' → giữ nguyên
        - Nếu không có → chọn panel lớn nhất và scale lên
        
        Args:
            panel_specs: List[Dict] - Panel specs
        
        Returns:
            List[Dict] - Panel specs với dominant panel đã adjust
        """
        if not panel_specs:
            return panel_specs
        
        # Check xem đã có dominant panel chưa
        dominant_panels = [p for p in panel_specs if p['priority'] == 'dominant']
        
        if dominant_panels:
            # Đã có dominant panel từ scene_type='group'
            dominant = dominant_panels[0]
            
            # Ensure area trong 30-45%
            if dominant['area_ratio'] < 0.30:
                dominant['area_ratio'] = 0.35  # Scale up
            elif dominant['area_ratio'] > 0.45:
                dominant['area_ratio'] = 0.40  # Scale down
            
            return panel_specs
        
        # Không có dominant → chọn panel lớn nhất
        largest_panel = max(panel_specs, key=lambda p: p['area_ratio'])
        
        # Scale lên để đạt dominant size (35% trung bình)
        target_area = 0.35
        
        if largest_panel['area_ratio'] < target_area:
            largest_panel['area_ratio'] = target_area
            largest_panel['priority'] = 'dominant'  # Upgrade priority
        
        return panel_specs
    
    def validate_panel_count(self, panel_specs: List[Dict]) -> Dict:
        """
        Validate số panels trong range 4-7
        
        Returns:
            Dict với:
                - is_valid: bool
                - panel_count: int
                - recommendation: str
        """
        count = len(panel_specs)
        
        is_valid = 4 <= count <= 7
        
        if count < 4:
            recommendation = f"Cần thêm {4 - count} panels để đạt minimum 4 panels/trang"
        elif count > 7:
            recommendation = f"Nên giảm {count - 7} panels để đạt maximum 7 panels/trang"
        else:
            recommendation = "Panel count hợp lệ (4-7 panels)"
        
        return {
            'is_valid': is_valid,
            'panel_count': count,
            'recommendation': recommendation
        }
    
    def get_statistics(self) -> Dict:
        """
        Thống kê panels đã generate
        
        Returns:
            Dict với counts cho mỗi scene_type, shape_type, priority
        """
        from collections import Counter
        
        if not self.generation_history:
            return {'total_panels': 0}
        
        scene_types = [p['scene_type'] for p in self.generation_history]
        shape_types = [p['shape_type'] for p in self.generation_history]
        priorities = [p['priority'] for p in self.generation_history]
        
        stats = {
            'total_panels': len(self.generation_history),
            'scene_type_counts': dict(Counter(scene_types)),
            'shape_type_counts': dict(Counter(shape_types)),
            'priority_counts': dict(Counter(priorities)),
            'avg_area_ratio': sum(p['area_ratio'] for p in self.generation_history) / len(self.generation_history),
            'avg_aspect_ratio': sum(
                p['aspect_ratio'] for p in self.generation_history 
                if isinstance(p['aspect_ratio'], (int, float))
            ) / sum(
                1 for p in self.generation_history 
                if isinstance(p['aspect_ratio'], (int, float))
            )
        }
        
        return stats
    
    def reset_history(self):
        """Clear generation history"""
        self.generation_history = []
        self.panel_counter = 0
    
    def __repr__(self):
        return f"PanelGenerator(panels_generated={len(self.generation_history)})"


def test_panel_generator():
    """Test function for PanelGenerator"""
    print("=" * 80)
    print("PANEL GENERATOR TEST")
    print("=" * 80)
    
    generator = PanelGenerator(seed=42)
    
    # Test 1: Generate panels for each scene type
    print("\nTest 1: Generate panels for each scene type")
    print("-" * 80)
    
    scene_types = ['close_up', 'dialogue', 'group', 'action', 'normal']
    
    for scene_type in scene_types:
        panel = generator.generate_panel(scene_type, image_aspect=1.5)
        
        print(f"\n{scene_type.upper()}:")
        print(f"  Panel ID: {panel['panel_id']}")
        print(f"  Shape: {panel['shape_type']} ({panel['angle_type']})")
        print(f"  Aspect: {panel['aspect_ratio']:.2f}")
        print(f"  Area: {panel['area_ratio']:.1%}")
        print(f"  Priority: {panel['priority']}")
    
    # Test 2: Generate batch
    print("\n" + "=" * 80)
    print("Test 2: Generate batch from scene analyses")
    print("-" * 80)
    
    mock_analyses = [
        {'scene_type': 'group', 'width': 800, 'height': 600, 'image_id': 'img001.jpg'},
        {'scene_type': 'dialogue', 'width': 600, 'height': 800, 'image_id': 'img002.jpg'},
        {'scene_type': 'action', 'width': 1000, 'height': 700, 'image_id': 'img003.jpg'},
        {'scene_type': 'close_up', 'width': 600, 'height': 900, 'image_id': 'img004.jpg'},
        {'scene_type': 'normal', 'width': 700, 'height': 700, 'image_id': 'img005.jpg'}
    ]
    
    panels = generator.generate_panels_batch(mock_analyses)
    
    print(f"\nGenerated {len(panels)} panels:")
    for panel in panels:
        print(f"  {panel['image_id']}: {panel['scene_type']} → "
              f"{panel['shape_type']} {panel['aspect_ratio']:.2f} ({panel['area_ratio']:.1%})")
    
    # Test 3: Enforce dominant panel
    print("\n" + "=" * 80)
    print("Test 3: Enforce dominant panel")
    print("-" * 80)
    
    panels_adjusted = generator.enforce_dominant_panel(panels)
    
    dominant_panels = [p for p in panels_adjusted if p['priority'] == 'dominant']
    print(f"\nDominant panels: {len(dominant_panels)}")
    for dp in dominant_panels:
        print(f"  {dp['panel_id']}: {dp['scene_type']} - {dp['area_ratio']:.1%}")
    
    # Test 4: Validation
    print("\n" + "=" * 80)
    print("Test 4: Validate panel count")
    print("-" * 80)
    
    validation = generator.validate_panel_count(panels_adjusted)
    print(f"\nValid: {validation['is_valid']}")
    print(f"Count: {validation['panel_count']}")
    print(f"Recommendation: {validation['recommendation']}")
    
    # Statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    
    stats = generator.get_statistics()
    print(f"\nTotal panels: {stats['total_panels']}")
    print(f"\nScene type distribution:")
    for scene, count in stats['scene_type_counts'].items():
        print(f"  {scene}: {count}")
    print(f"\nShape type distribution:")
    for shape, count in stats['shape_type_counts'].items():
        print(f"  {shape}: {count}")
    print(f"\nAverage area ratio: {stats['avg_area_ratio']:.1%}")
    print(f"Average aspect ratio: {stats['avg_aspect_ratio']:.2f}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED ✓")
    print("=" * 80)


if __name__ == '__main__':
    test_panel_generator()
