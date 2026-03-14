"""
Scene Classification Module - Module 2 (✅ ENHANCED WITH AI)
Phân loại scene dựa trên image analysis metrics + AI models
Theo yêu cầu: Automatic Comic Page Layout Generation Based on Image Content Analysis
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter

# ✅ Try import AI models
try:
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    import torch
    AI_MODEL_AVAILABLE = True
except ImportError:
    AI_MODEL_AVAILABLE = False
    print("⚠️ transformers/torch not available - using rule-based classification only")


class SceneClassifier:
    """
    ✅ ENHANCED: Phân loại cảnh truyện tranh thành 5 loại với AI models
    
    Methods:
    1. Rule-based (original): Threshold-based classification
    2. AI-based (NEW): CLIP zero-shot classification
    3. Hybrid (NEW): Combine both methods
    
    Scene types:
    - close_up: Cận cảnh nhân vật
    - group: Nhiều nhân vật
    - action: Chuyển động mạnh
    - dialogue: Nhiều văn bản (hội thoại)
    - normal: Cảnh thường
    """
    
    # Thresholds for rule-based classification
    THRESHOLDS = {
        'character_area_ratio': 0.6,   # Cho close_up
        'character_count': 3,          # Cho group
        'motion_score': 0.7,           # Cho action
        'text_density': 0.5            # Cho dialogue
    }
    
    SCENE_TYPES = ['close_up', 'group', 'action', 'dialogue', 'normal']
    
    # ✅ NEW: Text descriptions for CLIP zero-shot classification
    CLIP_SCENE_DESCRIPTIONS = {
        'close_up': [
            "a close-up portrait of a character",
            "manga close-up face shot",
            "character facial expression close-up",
            "detailed character portrait"
        ],
        'group': [
            "multiple characters in a scene",
            "manga group scene with many people",
            "characters gathered together",
            "group of people interacting"
        ],
        'action': [
            "dynamic action scene with motion",
            "manga action sequence with movement",
            "fighting or action scene",
            "character in motion attacking"
        ],
        'dialogue': [
            "characters talking with speech bubbles",
            "manga dialogue scene with text",
            "conversation between characters",
            "characters speaking with text"
        ],
        'normal': [
            "normal manga panel scene",
            "casual everyday scene",
            "standard manga panel",
            "regular scene without special emphasis"
        ]
    }
    
    def __init__(self, method: str = 'rule_based', thresholds: Dict[str, float] = None):
        """
        Args:
            method: 'rule_based', 'ai_model', or 'hybrid'
            thresholds: Optional dict để override default thresholds
        """
        self.method = method
        
        if thresholds:
            self.THRESHOLDS.update(thresholds)
        
        self.scene_history = []
        self.classification_details = []
        
        # ✅ Initialize AI model if requested
        self.clip_model = None
        self.clip_processor = None
        
        if method in ['ai_model', 'hybrid'] and AI_MODEL_AVAILABLE:
            self._initialize_clip_model()
    
    def _initialize_clip_model(self):
        """✅ NEW: Load CLIP model for zero-shot classification"""
        try:
            print("🔄 Loading CLIP model for scene classification...")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.clip_model = self.clip_model.cuda()
                print("   ✅ CLIP loaded on GPU")
            else:
                print("   ✅ CLIP loaded on CPU")
                
        except Exception as e:
            print(f"   ⚠️ Failed to load CLIP: {e}")
            print("   Falling back to rule-based classification")
            self.method = 'rule_based'
    
    def classify_scene(self, image_analysis: Dict) -> str:
        """
        ✅ ENHANCED: Phân loại scene với multiple methods
        
        Args:
            image_analysis: Dict chứa metrics hoặc image_path
        
        Returns:
            scene_type: str in ['close_up', 'group', 'action', 'dialogue', 'normal']
        """
        # Select classification method
        if self.method == 'rule_based':
            scene_type = self._classify_rule_based(image_analysis)
        
        elif self.method == 'ai_model' and self.clip_model is not None:
            # Try AI first, fallback to rule-based if fails
            try:
                scene_type = self._classify_clip(image_analysis)
            except Exception as e:
                print(f"   ⚠️ CLIP classification failed: {e}, using rule-based")
                scene_type = self._classify_rule_based(image_analysis)
        
        elif self.method == 'hybrid' and self.clip_model is not None:
            # Combine both methods
            scene_type = self._classify_hybrid(image_analysis)
        
        else:
            # Default to rule-based
            scene_type = self._classify_rule_based(image_analysis)
        
        # Store history
        self.scene_history.append(scene_type)
        
        return scene_type
    
    def _classify_rule_based(self, image_analysis: Dict) -> str:
        """Original rule-based classification"""
        # Extract metrics với default values
        char_ratio = image_analysis.get('character_area_ratio', 0.0)
        char_count = image_analysis.get('character_count', 0)
        motion = image_analysis.get('motion_score', 0.0)
        text_dens = image_analysis.get('text_density', 0.0)
        
        # Priority 1: Close-up (character fills frame)
        if char_ratio > self.THRESHOLDS['character_area_ratio']:
            scene_type = 'close_up'
            reason = f"character_area_ratio={char_ratio:.2f} > {self.THRESHOLDS['character_area_ratio']}"
        
        # Priority 2: Group scene (multiple characters)
        elif char_count >= self.THRESHOLDS['character_count']:
            scene_type = 'group'
            reason = f"character_count={char_count} >= {self.THRESHOLDS['character_count']}"
        
        # Priority 3: Action scene (high motion)
        elif motion > self.THRESHOLDS['motion_score']:
            scene_type = 'action'
            reason = f"motion_score={motion:.2f} > {self.THRESHOLDS['motion_score']}"
        
        # Priority 4: Dialogue (text-heavy)
        elif text_dens > self.THRESHOLDS['text_density']:
            scene_type = 'dialogue'
            reason = f"text_density={text_dens:.2f} > {self.THRESHOLDS['text_density']}"
        
        # Default: Normal panel
        else:
            scene_type = 'normal'
            reason = "No threshold exceeded - default to normal"
        
        # Store details for debugging
        detail = {
            'scene_type': scene_type,
            'reason': reason,
            'method': 'rule_based',
            'metrics': {
                'character_area_ratio': char_ratio,
                'character_count': char_count,
                'motion_score': motion,
                'text_density': text_dens
            }
        }
        
        if 'image_path' in image_analysis:
            detail['image_path'] = image_analysis['image_path']
        
        self.classification_details.append(detail)
        
        return scene_type
    
    def _classify_clip(self, image_analysis: Dict) -> str:
        """✅ NEW: CLIP-based zero-shot classification"""
        if 'image_path' not in image_analysis:
            raise ValueError("image_path required for CLIP classification")
        
        image_path = image_analysis['image_path']
        image = Image.open(image_path).convert('RGB')
        
        # Prepare all text descriptions
        all_texts = []
        text_to_scene = {}
        for scene_type, descriptions in self.CLIP_SCENE_DESCRIPTIONS.items():
            for desc in descriptions:
                all_texts.append(desc)
                text_to_scene[desc] = scene_type
        
        # Run CLIP
        inputs = self.clip_processor(
            text=all_texts, 
            images=image, 
            return_tensors="pt", 
            padding=True
        )
        
        if torch.cuda.is_available() and self.clip_model.device.type == 'cuda':
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        outputs = self.clip_model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)[0]
        
        # Get top prediction
        top_idx = probs.argmax().item()
        top_text = all_texts[top_idx]
        scene_type = text_to_scene[top_text]
        confidence = probs[top_idx].item()
        
        # Store details
        detail = {
            'scene_type': scene_type,
            'reason': f"CLIP prediction: '{top_text}' (conf: {confidence:.2f})",
            'method': 'clip',
            'confidence': confidence,
            'image_path': image_path
        }
        self.classification_details.append(detail)
        
        return scene_type
    
    def _classify_hybrid(self, image_analysis: Dict) -> str:
        """✅ NEW: Hybrid classification (combine rule-based + CLIP)"""
        # Get both predictions
        rule_scene = self._classify_rule_based(image_analysis)
        
        try:
            clip_scene = self._classify_clip(image_analysis)
        except Exception as e:
            # If CLIP fails, use rule-based
            return rule_scene
        
        # If both agree, return with high confidence
        if rule_scene == clip_scene:
            detail = {
                'scene_type': rule_scene,
                'reason': f"Both methods agree: {rule_scene}",
                'method': 'hybrid',
                'agreement': True
            }
            self.classification_details.append(detail)
            return rule_scene
        
        # If disagree, prioritize CLIP for visual features
        # But respect rule-based for strong signals (e.g., group with 5+ chars)
        char_count = image_analysis.get('character_count', 0)
        text_count = image_analysis.get('text_count', 0)
        
        # Strong signals that should override
        if char_count >= 5:
            final_scene = 'group'
        elif text_count >= 3:
            final_scene = 'dialogue'
        else:
            final_scene = clip_scene  # Trust CLIP for visual nuances
        
        detail = {
            'scene_type': final_scene,
            'reason': f"Hybrid: rule={rule_scene}, clip={clip_scene}, final={final_scene}",
            'method': 'hybrid',
            'agreement': False
        }
        self.classification_details.append(detail)
        
        return final_scene
    
    def classify_batch(self, image_analyses: List[Dict]) -> List[Dict]:
        """
        Phân loại nhiều ảnh, track context
        
        Args:
            image_analyses: List[Dict] - Mỗi dict là kết quả từ ImageAnalyzer
        
        Returns:
            List[Dict] với thêm key 'scene_type'
        """
        results = []
        
        for analysis in image_analyses:
            scene_type = self.classify_scene(analysis)
            
            result = analysis.copy()
            result['scene_type'] = scene_type
            results.append(result)
        
        return results
    
    def get_scene_statistics(self) -> Dict:
        """
        Thống kê scene distribution từ history
        
        Returns:
            Dict với counts và percentages cho mỗi scene type
        """
        if not self.scene_history:
            return {scene: {'count': 0, 'percentage': 0.0} 
                    for scene in self.SCENE_TYPES}
        
        counts = Counter(self.scene_history)
        total = len(self.scene_history)
        
        stats = {}
        for scene in self.SCENE_TYPES:
            count = counts.get(scene, 0)
            stats[scene] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0.0
            }
        
        return stats
    
    def get_classification_details(self) -> List[Dict]:
        """Return chi tiết classification cho debugging"""
        return self.classification_details
    
    def reset_history(self):
        """Clear history và details"""
        self.scene_history = []
        self.classification_details = []
    
    def suggest_panel_count(self, scene_types: List[str]) -> int:
        """
        Đề xuất số panels cho trang dựa trên scene types
        
        Logic:
        - Nhiều action/group → ít panels (4-5) để panel lớn
        - Nhiều dialogue/close_up → nhiều panels (6-7) để fit text
        - Normal → trung bình (5-6)
        """
        if not scene_types:
            return 5
        
        scene_counts = Counter(scene_types)
        
        # Action/group = panels lớn → ít panels
        large_panel_scenes = scene_counts.get('action', 0) + scene_counts.get('group', 0)
        
        # Dialogue/close_up = panels nhỏ → nhiều panels
        small_panel_scenes = scene_counts.get('dialogue', 0) + scene_counts.get('close_up', 0)
        
        # Calculate score
        total = len(scene_types)
        large_ratio = large_panel_scenes / total
        small_ratio = small_panel_scenes / total
        
        if large_ratio > 0.5:
            return 4  # Ưu tiên panels lớn
        elif small_ratio > 0.5:
            return 6  # Nhiều panels nhỏ
        else:
            return 5  # Balanced
    
    def validate_scene_distribution(self, scene_types: List[str]) -> Dict:
        """
        Kiểm tra distribution có hợp lý không
        
        Returns:
            {
                'is_valid': bool,
                'warnings': List[str],
                'distribution': Dict
            }
        """
        if not scene_types:
            return {
                'is_valid': False,
                'warnings': ['Empty scene_types list'],
                'distribution': {}
            }
        
        counts = Counter(scene_types)
        total = len(scene_types)
        warnings = []
        
        # Check: Too many action scenes (>40% unusual)
        action_ratio = counts.get('action', 0) / total
        if action_ratio > 0.4:
            warnings.append(f"High action ratio: {action_ratio:.1%} (>40%)")
        
        # Check: Too many dialogue scenes (>50% text-heavy)
        dialogue_ratio = counts.get('dialogue', 0) / total
        if dialogue_ratio > 0.5:
            warnings.append(f"High dialogue ratio: {dialogue_ratio:.1%} (>50%)")
        
        # Check: All same scene type (lack variety)
        if len(counts) == 1:
            warnings.append(f"No scene variety - all {scene_types[0]}")
        
        # Check: Too few normal scenes (might be over-classified)
        normal_ratio = counts.get('normal', 0) / total
        if normal_ratio == 0 and total > 10:
            warnings.append("No normal scenes detected - classification might be too aggressive")
        
        distribution = {scene: counts.get(scene, 0) / total 
                       for scene in self.SCENE_TYPES}
        
        is_valid = len(warnings) == 0
        
        return {
            'is_valid': is_valid,
            'warnings': warnings,
            'distribution': distribution
        }
    
    def __repr__(self):
        stats = self.get_scene_statistics()
        return (f"SceneClassifier(total_classified={len(self.scene_history)}, "
                f"distribution={stats})")


def test_scene_classifier():
    """Test function for SceneClassifier"""
    print("=" * 60)
    print("SCENE CLASSIFIER TEST")
    print("=" * 60)
    
    classifier = SceneClassifier()
    
    # Test cases
    test_cases = [
        {
            'name': 'Close-up scene',
            'metrics': {
                'character_area_ratio': 0.75,
                'character_count': 1,
                'motion_score': 0.3,
                'text_density': 0.2
            },
            'expected': 'close_up'
        },
        {
            'name': 'Group scene',
            'metrics': {
                'character_area_ratio': 0.4,
                'character_count': 4,
                'motion_score': 0.5,
                'text_density': 0.3
            },
            'expected': 'group'
        },
        {
            'name': 'Action scene',
            'metrics': {
                'character_area_ratio': 0.3,
                'character_count': 2,
                'motion_score': 0.85,
                'text_density': 0.1
            },
            'expected': 'action'
        },
        {
            'name': 'Dialogue scene',
            'metrics': {
                'character_area_ratio': 0.25,
                'character_count': 2,
                'motion_score': 0.2,
                'text_density': 0.65
            },
            'expected': 'dialogue'
        },
        {
            'name': 'Normal scene',
            'metrics': {
                'character_area_ratio': 0.35,
                'character_count': 1,
                'motion_score': 0.4,
                'text_density': 0.3
            },
            'expected': 'normal'
        }
    ]
    
    print("\nTest Classification:")
    print("-" * 60)
    
    for i, test in enumerate(test_cases, 1):
        result = classifier.classify_scene(test['metrics'])
        status = "✓" if result == test['expected'] else "✗"
        
        print(f"\n{i}. {test['name']}")
        print(f"   Metrics: {test['metrics']}")
        print(f"   Expected: {test['expected']}")
        print(f"   Result: {result} {status}")
    
    # Statistics
    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    
    stats = classifier.get_scene_statistics()
    for scene_type, data in stats.items():
        print(f"{scene_type:12s}: {data['count']:2d} ({data['percentage']:5.1f}%)")
    
    # Validation
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    
    validation = classifier.validate_scene_distribution(classifier.scene_history)
    print(f"Valid: {validation['is_valid']}")
    if validation['warnings']:
        print("Warnings:")
        for w in validation['warnings']:
            print(f"  - {w}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    test_scene_classifier()
