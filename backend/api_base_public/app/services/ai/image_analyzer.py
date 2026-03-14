"""
Image Analyzer Extended Module - Module 1 (Enhanced)
Bổ sung motion_score, text_density, emotion_score vào image analysis
Theo yêu cầu: Automatic Comic Page Layout Generation Based on Image Content Analysis
"""

import cv2
import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional
import os


class ImageAnalyzer:
    """
    Enhanced image analyzer với đầy đủ metrics yêu cầu:
    - character_count ✓ (từ smart_crop.detect_people)
    - character_area_ratio ✓ (từ smart_crop.analyze_shot_type)
    - motion_score ✓ (NEW - edge density + blur detection)
    - text_density ✓ (NEW - text area / image area)
    - emotion_score ✓ (NEW - facial expression analysis)
    - scene_type (từ SceneClassifier)
    """
    
    def __init__(self, use_yolo=False, use_easyocr=True):
        """
        Args:
            use_yolo: Dùng YOLO cho character detection (chính xác hơn)
            use_easyocr: Dùng EasyOCR cho text detection (chính xác hơn)
        """
        self.use_yolo = use_yolo
        self.use_easyocr = use_easyocr
        
        # Import smart_crop functions
        try:
            from smart_crop import detect_people, detect_text_boxes, analyze_shot_type
            self.detect_people = detect_people
            self.detect_text_boxes = detect_text_boxes
            self.analyze_shot_type = analyze_shot_type
        except ImportError:
            raise ImportError("smart_crop.py module required")
    
    def analyze_image(self, image_path: str) -> Dict:
        """
        Phân tích đầy đủ 1 ảnh theo yêu cầu đề bài
        
        Args:
            image_path: Đường dẫn ảnh
        
        Returns:
            Dict với:
                - image_id: str
                - width, height: int
                - character_count: int
                - character_area_ratio: float (0-1)
                - motion_score: float (0-1)
                - text_density: float (0-1)
                - emotion_score: float (0-1)
                - has_text: bool
                - has_characters: bool
                - shot_type: str ('wide'|'medium'|'close_up')
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Load image
        img = Image.open(image_path)
        width, height = img.size
        image_area = width * height
        
        # 1. CHARACTER DETECTION & AREA RATIO
        char_boxes = self.detect_people(image_path, use_yolo=self.use_yolo)
        character_count = len(char_boxes)
        
        total_char_area = 0
        for detection in char_boxes:
            box = detection['box']
            x1, y1, x2, y2 = box
            char_area = (x2 - x1) * (y2 - y1)
            total_char_area += char_area
        
        character_area_ratio = min(1.0, total_char_area / image_area) if image_area > 0 else 0.0
        
        # 2. SHOT TYPE ANALYSIS
        shot_info = self.analyze_shot_type(image_path, use_yolo=self.use_yolo)
        shot_type = shot_info['shot_type']
        
        # 3. TEXT DETECTION & DENSITY
        text_boxes = self.detect_text_boxes(image_path, use_easyocr=self.use_easyocr)
        
        total_text_area = 0
        for detection in text_boxes:
            box = detection['box']
            x1, y1, x2, y2 = box
            text_area = (x2 - x1) * (y2 - y1)
            total_text_area += text_area
        
        text_density = min(1.0, total_text_area / image_area) if image_area > 0 else 0.0
        
        # 4. MOTION SCORE (NEW)
        motion_score = self.calculate_motion_score(image_path)
        
        # 5. EMOTION SCORE (NEW)
        emotion_score = self.calculate_emotion_score(image_path, char_boxes)
        
        result = {
            'image_id': os.path.basename(image_path),
            'image_path': image_path,
            'width': width,
            'height': height,
            'character_count': character_count,
            'character_area_ratio': round(character_area_ratio, 4),
            'motion_score': round(motion_score, 4),
            'text_density': round(text_density, 4),
            'emotion_score': round(emotion_score, 4),
            'has_text': len(text_boxes) > 0,
            'has_characters': character_count > 0,
            'shot_type': shot_type,
            'text_count': len(text_boxes),
            'character_boxes': char_boxes,
            'text_boxes': text_boxes
        }
        
        return result
    
    def calculate_motion_score(self, image_path: str) -> float:
        """
        Tính motion_score dựa trên:
        1. Edge density (Canny edge detection) - 60%
        2. Blur detection (Laplacian variance) - 40%
        
        Returns:
            float (0-1): 0 = static/calm, 1 = high motion/action
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return 0.0
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # ============================================================
        # COMPONENT 1: Edge Density (60%)
        # ============================================================
        # High edge density → nhiều chi tiết, đường chuyển động
        edges = cv2.Canny(gray, threshold1=50, threshold2=150)
        edge_pixels = np.sum(edges > 0)
        total_pixels = edges.size
        edge_density = edge_pixels / total_pixels
        
        # Normalize: Typical range 0.05-0.25, normalize to 0-1
        edge_score = min(1.0, edge_density / 0.20)
        
        # ============================================================
        # COMPONENT 2: Blur Detection (40%)
        # ============================================================
        # Motion blur → low Laplacian variance
        # Sharp image → high variance
        # Inverted: lower variance = higher motion score
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = laplacian.var()
        
        # Normalize: Typical sharp image 100-500, blurred <100
        # Invert: low variance = high motion
        blur_score = max(0.0, 1.0 - min(1.0, laplacian_var / 300))
        
        # ============================================================
        # WEIGHTED COMBINATION
        # ============================================================
        motion_score = edge_score * 0.6 + blur_score * 0.4
        
        return float(motion_score)
    
    def calculate_emotion_score(self, image_path: str, char_boxes: list) -> float:
        """
        Tính emotion_score dựa trên facial expression analysis
        
        Simplified approach (không cần deep learning model):
        1. Detect faces trong character boxes
        2. Phân tích facial landmarks (nếu có)
        3. Mock emotion score based on face presence & expression cues
        
        Returns:
            float (0-1): 0 = neutral/calm, 1 = intense emotion
        
        NOTE: Full implementation cần face expression classifier (CNN)
              Hiện tại dùng heuristic approach
        """
        if not char_boxes:
            return 0.5  # Neutral khi không có nhân vật
        
        img = cv2.imread(str(image_path))
        if img is None:
            return 0.5
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load face cascade
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except:
            return 0.5
        
        emotion_scores = []
        
        for detection in char_boxes:
            box = detection['box']
            x1, y1, x2, y2 = [int(c) for c in box]
            
            # Crop character region
            char_roi = gray[y1:y2, x1:x2]
            
            if char_roi.size == 0:
                continue
            
            # Detect faces in character region
            faces = face_cascade.detectMultiScale(
                char_roi,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(20, 20)
            )
            
            if len(faces) == 0:
                # No face detected → assume neutral
                emotion_scores.append(0.5)
                continue
            
            # Analyze largest face
            face = max(faces, key=lambda f: f[2] * f[3])
            fx, fy, fw, fh = face
            face_roi = char_roi[fy:fy+fh, fx:fx+fw]
            
            # ============================================================
            # HEURISTIC EMOTION ESTIMATION
            # ============================================================
            # 1. Face area ratio (larger face = more emotional intensity)
            face_area_ratio = (fw * fh) / (char_roi.shape[0] * char_roi.shape[1])
            
            # 2. Contrast/intensity variance (high variance = more expression)
            intensity_std = np.std(face_roi)
            contrast_score = min(1.0, intensity_std / 50)
            
            # 3. Edge density in face (more edges = more expression)
            face_edges = cv2.Canny(face_roi, 30, 100)
            face_edge_density = np.sum(face_edges > 0) / face_edges.size
            edge_score = min(1.0, face_edge_density / 0.15)
            
            # Combine scores
            emotion = (
                face_area_ratio * 0.3 +
                contrast_score * 0.4 +
                edge_score * 0.3
            )
            
            emotion_scores.append(emotion)
        
        # Average across all characters
        if emotion_scores:
            avg_emotion = np.mean(emotion_scores)
        else:
            avg_emotion = 0.5
        
        return float(avg_emotion)
    
    def analyze_batch(self, image_paths: list) -> list:
        """
        Phân tích nhiều ảnh
        
        Args:
            image_paths: List[str] - Đường dẫn các ảnh
        
        Returns:
            List[Dict] - Kết quả analysis cho từng ảnh
        """
        results = []
        
        for i, img_path in enumerate(image_paths):
            try:
                result = self.analyze_image(img_path)
                result['batch_index'] = i
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    print(f"Analyzed {i+1}/{len(image_paths)} images...")
                    
            except Exception as e:
                print(f"Error analyzing {img_path}: {e}")
                results.append({
                    'image_id': os.path.basename(img_path),
                    'image_path': img_path,
                    'error': str(e),
                    'batch_index': i
                })
        
        print(f"Analysis complete: {len(results)} images")
        return results
    
    def get_statistics(self, analyses: list) -> Dict:
        """
        Thống kê metrics từ batch analysis
        
        Returns:
            Dict với min, max, mean, std cho mỗi metric
        """
        if not analyses:
            return {}
        
        # Extract metrics (ignore error entries)
        valid_analyses = [a for a in analyses if 'error' not in a]
        
        if not valid_analyses:
            return {'error': 'No valid analyses'}
        
        metrics = {
            'character_count': [a['character_count'] for a in valid_analyses],
            'character_area_ratio': [a['character_area_ratio'] for a in valid_analyses],
            'motion_score': [a['motion_score'] for a in valid_analyses],
            'text_density': [a['text_density'] for a in valid_analyses],
            'emotion_score': [a['emotion_score'] for a in valid_analyses]
        }
        
        stats = {}
        
        for metric_name, values in metrics.items():
            if values:
                stats[metric_name] = {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'median': float(np.median(values))
                }
        
        # Scene type distribution
        shot_types = [a['shot_type'] for a in valid_analyses]
        from collections import Counter
        stats['shot_type_distribution'] = dict(Counter(shot_types))
        
        return stats


def test_image_analyzer():
    """Test function for ImageAnalyzer"""
    print("=" * 80)
    print("IMAGE ANALYZER TEST")
    print("=" * 80)
    
    # Find test images
    test_dirs = ['images', 'uploads', 'outputs']
    test_image = None
    
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            files = [f for f in os.listdir(dir_name) 
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                test_image = os.path.join(dir_name, files[0])
                break
    
    if not test_image:
        print("❌ No test images found in images/, uploads/, or outputs/")
        return
    
    print(f"\nTest image: {test_image}")
    print("-" * 80)
    
    analyzer = ImageAnalyzer(use_yolo=False, use_easyocr=False)
    
    try:
        result = analyzer.analyze_image(test_image)
        
        print("\nANALYSIS RESULT:")
        print("-" * 80)
        print(f"Image: {result['image_id']}")
        print(f"Size: {result['width']}x{result['height']}")
        print(f"\nMETRICS:")
        print(f"  Character count: {result['character_count']}")
        print(f"  Character area ratio: {result['character_area_ratio']:.3f}")
        print(f"  Motion score: {result['motion_score']:.3f}")
        print(f"  Text density: {result['text_density']:.3f}")
        print(f"  Emotion score: {result['emotion_score']:.3f}")
        print(f"\nCONTEXT:")
        print(f"  Shot type: {result['shot_type']}")
        print(f"  Has text: {result['has_text']} ({result['text_count']} boxes)")
        print(f"  Has characters: {result['has_characters']}")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_image_analyzer()
