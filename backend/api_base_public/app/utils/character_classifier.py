"""
Character Classifier - Phân biệt nhân vật chính và phụ  
✅ ENHANCED: Face Recognition để identify character names
Tích hợp với smart_crop.py để xác định nhân vật quan trọng
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import pickle

# ✅ Try import face recognition libraries
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ face_recognition not available - install: pip install face-recognition")


class CharacterClassifier:
    """
    ✅ ENHANCED: Phân loại + nhận diện nhân vật trong manga/comic
    
    Features:
    1. Character classification (PRIMARY/SECONDARY/BACKGROUND)
    2. Face recognition (identify character names)
    3. Character tracking across pages
    """
    
    def __init__(self, character_database_path: Optional[str] = None):
        """
        Args:
            character_database_path: Path to character face encodings database (pickle file)
        """
        self.character_history = {}  # Track characters across pages
        
        # ✅ NEW: Face recognition database
        self.face_encodings_db = {}  # {character_name: [encoding1, encoding2, ...]}
        self.face_recognition_enabled = FACE_RECOGNITION_AVAILABLE
        
        if character_database_path and Path(character_database_path).exists():
            self._load_character_database(character_database_path)
        else:
            print("ℹ️ No character database loaded - face recognition disabled")
            print("   Create database with: create_character_database()")
    
    def _load_character_database(self, db_path: str):
        """✅ NEW: Load character face encodings từ database"""
        try:
            with open(db_path, 'rb') as f:
                self.face_encodings_db = pickle.load(f)
            print(f"✅ Loaded character database: {len(self.face_encodings_db)} characters")
            for name, encodings in self.face_encodings_db.items():
                print(f"   - {name}: {len(encodings)} face samples")
        except Exception as e:
            print(f"⚠️ Failed to load character database: {e}")
            self.face_encodings_db = {}
    
    def save_character_database(self, db_path: str):
        """✅ NEW: Save character database to file"""
        try:
            with open(db_path, 'wb') as f:
                pickle.dump(self.face_encodings_db, f)
            print(f"✅ Saved character database: {db_path}")
        except Exception as e:
            print(f"❌ Failed to save database: {e}")
    
    def add_character_to_database(self, 
                                   character_name: str, 
                                   face_image_paths: List[str]):
        """
        ✅ NEW: Thêm nhân vật mới vào database
        
        Args:
            character_name: Tên nhân vật (e.g., "Luffy", "Zoro")
            face_image_paths: List đường dẫn ảnh mặt nhân vật (nhiều ảnh = tốt hơn)
        """
        if not self.face_recognition_enabled:
            print("❌ Face recognition not available")
            return
        
        encodings = []
        
        for img_path in face_image_paths:
            try:
                image = face_recognition.load_image_file(img_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if len(face_encodings) > 0:
                    encodings.append(face_encodings[0])
                    print(f"   ✅ Added face from {Path(img_path).name}")
                else:
                    print(f"   ⚠️ No face found in {Path(img_path).name}")
                    
            except Exception as e:
                print(f"   ❌ Error processing {img_path}: {e}")
        
        if encodings:
            self.face_encodings_db[character_name] = encodings
            print(f"✅ Added {character_name}: {len(encodings)} face encodings")
        else:
            print(f"❌ No valid faces found for {character_name}")
    
    def identify_character(self, face_encoding: np.ndarray) -> Tuple[Optional[str], float]:
        """
        ✅ NEW: Nhận diện tên nhân vật từ face encoding
        
        Returns:
            (character_name, confidence) hoặc (None, 0.0) nếu không nhận ra
        """
        if not self.face_encodings_db:
            return None, 0.0
        
        best_match_name = None
        best_match_distance = float('inf')
        
        # Compare với tất cả character trong database
        for character_name, known_encodings in self.face_encodings_db.items():
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            min_distance = np.min(distances)
            
            if min_distance < best_match_distance:
                best_match_distance = min_distance
                best_match_name = character_name
        
        # Threshold: <0.6 = same person, 0.6-0.7 = uncertain, >0.7 = different
        if best_match_distance < 0.6:
            confidence = 1.0 - best_match_distance
            return best_match_name, confidence
        else:
            return None, 0.0
        
    def classify_characters(self, 
                           image_path: str,
                           character_boxes: List[Dict],
                           text_boxes: List[Dict],
                           page_number: int = 1) -> List[Dict]:
        """
        ✅ ENHANCED: Phân loại nhân vật + Face Recognition
        
        Args:
            image_path: Đường dẫn ảnh
            character_boxes: List boxes của nhân vật từ detect_people()
            text_boxes: List boxes của text từ detect_text()
            page_number: Số trang (để track across pages)
            
        Returns:
            List nhân vật được phân loại với priority score + character names
        """
        if not character_boxes:
            return []
        
        img = cv2.imread(str(image_path))
        if img is None:
            return character_boxes
        
        h, w = img.shape[:2]
        image_center = (w / 2, h / 2)
        
        # ✅ NEW: Load image for face recognition if enabled
        if self.face_recognition_enabled and self.face_encodings_db:
            try:
                rgb_image = face_recognition.load_image_file(str(image_path))
                all_face_locations = face_recognition.face_locations(rgb_image)
                all_face_encodings = face_recognition.face_encodings(rgb_image, all_face_locations)
            except Exception as e:
                print(f"⚠️ Face recognition failed: {e}")
                all_face_locations = []
                all_face_encodings = []
        else:
            all_face_locations = []
            all_face_encodings = []
        
        classified = []
        
        for char_box in character_boxes:
            x1, y1, x2, y2 = char_box['box']
            char_w = x2 - x1
            char_h = y2 - y1
            char_area = char_w * char_h
            
            # 1. SIZE SCORE (30%) - Nhân vật lớn = quan trọng hơn
            size_ratio = char_area / (w * h)
            size_score = min(size_ratio * 20, 1.0)  # Normalize to 0-1
            
            # 2. POSITION SCORE (25%) - Gần trung tâm = quan trọng hơn
            char_center = ((x1 + x2) / 2, (y1 + y2) / 2)
            distance_to_center = np.sqrt(
                (char_center[0] - image_center[0])**2 + 
                (char_center[1] - image_center[1])**2
            )
            max_distance = np.sqrt(w**2 + h**2) / 2
            position_score = 1.0 - (distance_to_center / max_distance)
            
            # 3. FOCUS SCORE (20%) - Vùng sắc nét = nhân vật chính
            char_region = img[int(y1):int(y2), int(x1):int(x2)]
            if char_region.size > 0:
                gray = cv2.cvtColor(char_region, cv2.COLOR_BGR2GRAY)
                laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                focus_score = min(laplacian.var() / 500, 1.0)
            else:
                focus_score = 0.5
            
            # 4. TEXT PROXIMITY SCORE (15%) - Gần text (speech bubble) = nhân vật đang nói
            text_proximity_score = self._calculate_text_proximity(
                char_box, text_boxes, w, h
            )
            
            # 5. FACE DETECTION SCORE (10%) - Có mặt rõ ràng = quan trọng hơn
            face_score = self._detect_face_quality(char_region)
            
            # ✅ NEW: Face Recognition - Identify character name
            character_name = None
            face_confidence = 0.0
            
            if all_face_encodings:
                # Find matching face trong character box
                for face_loc, face_enc in zip(all_face_locations, all_face_encodings):
                    top, right, bottom, left = face_loc
                    
                    # Check if face is within character box
                    if (left >= x1 and right <= x2 and top >= y1 and bottom <= y2):
                        character_name, face_confidence = self.identify_character(face_enc)
                        if character_name:
                            break
            
            # Tính OVERALL PRIORITY
            priority = (
                size_score * 0.30 +
                position_score * 0.25 +
                focus_score * 0.20 +
                text_proximity_score * 0.15 +
                face_score * 0.10
            )
            
            # Phân loại
            if priority >= 0.7:
                character_type = "PRIMARY"
                character_label = "🌟 Nhân vật chính"
                crop_priority = 3.5  # Very high
            elif priority >= 0.5:
                character_type = "SECONDARY"
                character_label = "⭐ Nhân vật phụ"
                crop_priority = 2.5  # High
            else:
                character_type = "BACKGROUND"
                character_label = "👤 Nhân vật nền"
                crop_priority = 1.5  # Medium
            
            classified.append({
                **char_box,
                'character_type': character_type,
                'character_label': character_label,
                'character_name': character_name,  # ✅ NEW
                'face_confidence': face_confidence,  # ✅ NEW
                'priority_score': priority,
                'crop_priority': crop_priority,
                'scores': {
                    'size': size_score,
                    'position': position_score,
                    'focus': focus_score,
                    'text_proximity': text_proximity_score,
                    'face_quality': face_score
                }
            })
        
        # Sort by priority (cao nhất trước)
        classified.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Update tracking history
        self._update_character_history(page_number, classified)
        
        return classified
    
    def _calculate_text_proximity(self, 
                                   char_box: Dict, 
                                   text_boxes: List[Dict],
                                   img_w: int, 
                                   img_h: int) -> float:
        """
        Tính độ gần với text bubbles
        Nhân vật gần text = đang nói = quan trọng hơn
        """
        if not text_boxes:
            return 0.5  # Neutral nếu không có text
        
        cx1, cy1, cx2, cy2 = char_box['box']
        char_center = ((cx1 + cx2) / 2, (cy1 + cy2) / 2)
        
        min_distance = float('inf')
        
        for text_box in text_boxes:
            tx1, ty1, tx2, ty2 = text_box['box']
            text_center = ((tx1 + tx2) / 2, (ty1 + ty2) / 2)
            
            distance = np.sqrt(
                (char_center[0] - text_center[0])**2 + 
                (char_center[1] - text_center[1])**2
            )
            
            min_distance = min(min_distance, distance)
        
        # Normalize distance (closer = higher score)
        max_distance = np.sqrt(img_w**2 + img_h**2)
        proximity_score = 1.0 - (min_distance / max_distance)
        
        # Boost score if very close (within speech bubble range)
        if min_distance < min(img_w, img_h) * 0.15:  # Within 15% of image size
            proximity_score = min(proximity_score * 1.5, 1.0)
        
        return proximity_score
    
    def _detect_face_quality(self, char_region: np.ndarray) -> float:
        """
        Phát hiện chất lượng khuôn mặt trong vùng nhân vật
        Khuôn mặt rõ ràng = nhân vật quan trọng
        """
        if char_region.size == 0:
            return 0.0
        
        try:
            # Load Haar Cascade face detector
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            gray = cv2.cvtColor(char_region, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=3,
                minSize=(20, 20)
            )
            
            if len(faces) > 0:
                # Có mặt rõ ràng
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                face_w, face_h = largest_face[2], largest_face[3]
                face_ratio = (face_w * face_h) / (char_region.shape[0] * char_region.shape[1])
                
                # Face chiếm 10-50% của character box = tốt
                if 0.1 <= face_ratio <= 0.5:
                    return 0.9
                elif face_ratio > 0.05:
                    return 0.7
                else:
                    return 0.5
            else:
                # Không detect được mặt - có thể là full body hoặc side view
                return 0.4
                
        except Exception as e:
            print(f"⚠️  Face detection error: {e}")
            return 0.5
    
    def _update_character_history(self, page_number: int, characters: List[Dict]):
        """
        Track nhân vật qua các trang
        Nhân vật xuất hiện nhiều = có thể là nhân vật chính
        """
        self.character_history[page_number] = {
            'primary_count': sum(1 for c in characters if c['character_type'] == 'PRIMARY'),
            'secondary_count': sum(1 for c in characters if c['character_type'] == 'SECONDARY'),
            'total_count': len(characters)
        }
    
    def get_statistics(self) -> Dict:
        """Lấy thống kê nhân vật qua các trang"""
        if not self.character_history:
            return {}
        
        total_primary = sum(p['primary_count'] for p in self.character_history.values())
        total_secondary = sum(p['secondary_count'] for p in self.character_history.values())
        total_chars = sum(p['total_count'] for p in self.character_history.values())
        
        return {
            'total_pages': len(self.character_history),
            'total_characters': total_chars,
            'total_primary': total_primary,
            'total_secondary': total_secondary,
            'avg_chars_per_page': total_chars / len(self.character_history),
            'primary_ratio': total_primary / total_chars if total_chars > 0 else 0
        }
    
    def visualize_classification(self, 
                                 image_path: str, 
                                 classified_chars: List[Dict],
                                 text_boxes: List[Dict],
                                 output_path: Optional[str] = None) -> np.ndarray:
        """
        Vẽ visualization để show phân loại nhân vật
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return None
        
        # Draw text boxes (màu xanh dương)
        for text_box in text_boxes:
            x1, y1, x2, y2 = map(int, text_box['box'])
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 200, 0), 2)
            cv2.putText(img, "TEXT", (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)
        
        # Draw characters với màu khác nhau theo type
        for char in classified_chars:
            x1, y1, x2, y2 = map(int, char['box'])
            
            # Màu theo type
            if char['character_type'] == 'PRIMARY':
                color = (0, 255, 0)  # Xanh lá (quan trọng nhất)
                thickness = 4
            elif char['character_type'] == 'SECONDARY':
                color = (0, 165, 255)  # Cam
                thickness = 3
            else:
                color = (128, 128, 128)  # Xám
                thickness = 2
            
            # Draw box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
            
            # Label
            label = f"{char['character_label']} ({char['priority_score']:.2f})"
            
            # Background cho text
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(img, (x1, y1 - text_h - 10), 
                         (x1 + text_w, y1), color, -1)
            
            # Text
            cv2.putText(img, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw scores detail (nhỏ hơn)
            scores_text = f"S:{char['scores']['size']:.2f} P:{char['scores']['position']:.2f} F:{char['scores']['focus']:.2f}"
            cv2.putText(img, scores_text, (x1, y2 + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Legend
        legend_y = 30
        cv2.putText(img, "🌟 PRIMARY (nhân vật chính)", (10, legend_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(img, "⭐ SECONDARY (nhân vật phụ)", (10, legend_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        cv2.putText(img, "👤 BACKGROUND (nền)", (10, legend_y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)
        
        if output_path:
            cv2.imwrite(output_path, img)
            print(f"✅ Saved visualization: {output_path}")
        
        return img


def integrate_with_smart_crop():
    """
    Hướng dẫn tích hợp với smart_crop.py
    """
    example_code = '''
# =============================================================================
# TÍCH HỢP VÀO smart_crop.py
# =============================================================================

# 1. Import ở đầu file
from character_classifier import CharacterClassifier

# 2. Trong hàm detect_important_regions(), thêm:

def detect_important_regions(image_path: Path, 
                            method: str = 'auto',
                            classify_characters: bool = True) -> Dict:
    """
    ... existing docstring ...
    
    Args:
        classify_characters: Nếu True, phân loại nhân vật chính/phụ
    """
    
    # ... existing code để detect text và characters ...
    
    text_boxes = detect_text(image_path, method)
    character_boxes = detect_people(image_path)
    
    # [MỚI] Phân loại nhân vật
    if classify_characters and character_boxes:
        classifier = CharacterClassifier()
        character_boxes = classifier.classify_characters(
            image_path=str(image_path),
            character_boxes=character_boxes,
            text_boxes=text_boxes,
            page_number=1
        )
        
        print(f"\\n🎭 Phân loại nhân vật:")
        for char in character_boxes:
            print(f"   {char['character_label']}: Priority {char['priority_score']:.2f}")
    
    # ... rest of existing code ...
    
    return {
        'text': text_boxes,
        'bubbles': bubble_boxes,
        'characters': character_boxes,  # Now with classification!
        'overall_confidence': overall_conf,
        'priority_score': priority,
        'method_used': method
    }

# 3. Trong smart_crop_with_priority(), sử dụng crop_priority mới:

def smart_crop_with_priority(image_path: Path, ...) -> Dict:
    # ... existing code ...
    
    # Priority được auto-adjust dựa trên character classification
    # PRIMARY characters: 3.5 (cao nhất)
    # TEXT boxes: 3.0
    # SECONDARY characters: 2.5
    # Bubbles: 2.5
    # BACKGROUND characters: 1.5
    
    # Crop sẽ ưu tiên giữ nhân vật chính!
'''
    
    print(example_code)
    return example_code


if __name__ == '__main__':
    print("=" * 70)
    print("🎭 CHARACTER CLASSIFIER - DEMO")
    print("=" * 70)
    print("\nModule này giúp phân biệt:")
    print("  🌟 PRIMARY - Nhân vật chính (quan trọng nhất)")
    print("  ⭐ SECONDARY - Nhân vật phụ (quan trọng)")
    print("  👤 BACKGROUND - Nhân vật nền (có thể crop)")
    print("\nDựa trên:")
    print("  • Kích thước (30%)")
    print("  • Vị trí trong ảnh (25%)")
    print("  • Độ focus/sắc nét (20%)")
    print("  • Gần text/speech bubble (15%)")
    print("  • Chất lượng khuôn mặt (10%)")
    print("\n" + "=" * 70)
    print("\n💡 Cách dùng:")
    print("\nOption 1 - Standalone test:")
    print("""
from character_classifier import CharacterClassifier
from smart_crop import detect_text, detect_people

# Detect
text_boxes = detect_text('image.jpg')
character_boxes = detect_people('image.jpg')

# Classify
classifier = CharacterClassifier()
classified = classifier.classify_characters(
    'image.jpg', 
    character_boxes, 
    text_boxes
)

# Show results
for char in classified:
    print(f"{char['character_label']}: {char['priority_score']:.2f}")

# Visualize
classifier.visualize_classification(
    'image.jpg', 
    classified, 
    text_boxes,
    'output_classified.jpg'
)
    """)
    
    print("\nOption 2 - Tích hợp vào smart_crop.py:")
    print("   Xem hướng dẫn chi tiết trong code!")
    
    print("\n" + "=" * 70)
