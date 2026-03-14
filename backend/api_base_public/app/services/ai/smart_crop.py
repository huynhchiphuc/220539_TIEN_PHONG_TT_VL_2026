"""
Smart Cropping cho Comic Book
Phát hiện vùng quan trọng (text + nhân vật + bong bóng chữ) và crop thông minh
"""
import os
import numpy as np
from PIL import Image
import cv2


def detect_text_boxes(image_path, use_easyocr=True, min_confidence=0.3):
    """
    🆕 IMPROVED: Phát hiện vùng chữ với multi-method và confidence scoring
    
    Args:
        image_path: Đường dẫn ảnh
        use_easyocr: True = dùng EasyOCR (accurate), False = multi-method ensemble
        min_confidence: Confidence tối thiểu (0-1)
    
    Returns:
        List[dict]: [{'box': (x1,y1,x2,y2), 'confidence': float, 'text': str, 'method': str}]
    """
    all_detections = []
    
    # METHOD 1: EasyOCR (most accurate for text)
    if use_easyocr:
        try:
            import easyocr
            if not hasattr(detect_text_boxes, 'reader'):
                print("🔄 Đang tải EasyOCR model...")
                detect_text_boxes.reader = easyocr.Reader(['vi', 'en'], gpu=False)
            
            # EasyOCR tự đọc ảnh, không cần cv2.imread
            results = detect_text_boxes.reader.readtext(str(image_path))
            for (bbox, text, prob) in results:
                if prob >= min_confidence:
                    pts = np.array(bbox)
                    x1, y1 = pts.min(axis=0)
                    x2, y2 = pts.max(axis=0)
                    all_detections.append({
                        'box': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': float(prob),
                        'text': text,
                        'method': 'easyocr'
                    })
            return all_detections
        except ImportError:
            print("⚠️  EasyOCR chưa cài, dùng fallback methods")
    
    # Đọc ảnh cho fallback methods
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    
    # METHOD 2: MSER (Maximally Stable Extremal Regions) - excellent for text
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # OpenCV 4.x uses different parameter names (no underscore)
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        for region in regions:
            x, y, w, h = cv2.boundingRect(region)
            # Filter text-like regions (aspect ratio 0.1-10)
            aspect = w / h if h > 0 else 0
            if 0.1 < aspect < 10 and w * h > 200:
                all_detections.append({
                    'box': (x, y, x+w, y+h),
                    'confidence': 0.7,  # MSER is reliable for text
                    'text': '',
                    'method': 'mser'
                })
    except Exception as e:
        print(f"⚠️  MSER detection failed: {e}")
    
    # METHOD 3: Contour-based detection (bright regions)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / h if h > 0 else 0
            # Text-like regions
            if 0.2 < aspect < 8:
                all_detections.append({
                    'box': (x, y, x+w, y+h),
                    'confidence': 0.5,
                    'text': '',
                    'method': 'contour'
                })
    
    # METHOD 4: EAST text detector (if available)
    try:
        # Placeholder for EAST - requires pre-trained model
        pass
    except:
        pass
    
    # 🆕 Remove duplicates and merge overlapping boxes
    merged = merge_overlapping_boxes(all_detections, iou_threshold=0.5)
    
    return merged


def detect_speech_bubbles(image_path, min_area=800, max_area=100000):
    """
    🆕 IMPROVED: Phát hiện bong bóng chữ với multiple methods
    
    Args:
        image_path: Đường dẫn ảnh
        min_area: Diện tích tối thiểu (px²)
        max_area: Diện tích tối đa (px²)
    
    Returns:
        List[dict]: [{'box': (x1,y1,x2,y2), 'confidence': float, 'type': str}]
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    all_bubbles = []
    
    # METHOD 1: White regions (classic speech bubbles)
    _, thresh_high = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    morph = cv2.morphologyEx(thresh_high, cv2.MORPH_CLOSE, kernel, iterations=2)
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (min_area <= area <= max_area):
            continue
        
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        x, y, bbox_w, bbox_h = cv2.boundingRect(cnt)
        aspect_ratio = bbox_w / bbox_h if bbox_h > 0 else 0
        
        # Improved filtering
        if circularity < 0.15 or aspect_ratio < 0.15 or aspect_ratio > 6:
            continue
        
        # Check if contains text (increase confidence)
        roi = gray[y:y+bbox_h, x:x+bbox_w]
        has_text = check_text_presence(roi)
        
        confidence = 0.6
        if has_text:
            confidence = 0.85
        if 0.3 < circularity < 0.9:
            confidence += 0.1
        
        all_bubbles.append({
            'box': (x, y, x+bbox_w, y+bbox_h),
            'confidence': min(confidence, 1.0),
            'type': 'speech_bubble'
        })
    
    # METHOD 2: Edge-based detection (outlined bubbles)
    edges = cv2.Canny(gray, 50, 150)
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges_dilated = cv2.dilate(edges, kernel_dilate, iterations=1)
    
    contours2, _ = cv2.findContours(edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours2:
        area = cv2.contourArea(cnt)
        if not (min_area <= area <= max_area):
            continue
        
        x, y, bbox_w, bbox_h = cv2.boundingRect(cnt)
        
        # Must be bubble-like shape
        aspect_ratio = bbox_w / bbox_h if bbox_h > 0 else 0
        if not (0.3 < aspect_ratio < 4):
            continue
        
        # Check interior is bright (typical of speech bubbles)
        roi = gray[y:y+bbox_h, x:x+bbox_w]
        mean_brightness = np.mean(roi)
        
        if mean_brightness > 180:
            all_bubbles.append({
                'box': (x, y, x+bbox_w, y+bbox_h),
                'confidence': 0.7,
                'type': 'outlined_bubble'
            })
    
    # Merge overlapping detections
    merged = merge_overlapping_boxes(all_bubbles, iou_threshold=0.6)
    
    return merged


def check_text_presence(roi_gray):
    """🆕 Kiểm tra xem region có chứa text không"""
    if roi_gray.size == 0:
        return False
    
    # Check for dark strokes (text) on bright background
    _, binary = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark_ratio = np.sum(binary == 0) / binary.size
    
    # Text regions typically have 10-40% dark pixels
    return 0.05 < dark_ratio < 0.5


def merge_overlapping_boxes(detections, iou_threshold=0.5):
    """🆕 Merge overlapping boxes với confidence weighting"""
    if not detections:
        return []
    
    # Sort by confidence
    sorted_dets = sorted(detections, key=lambda x: x.get('confidence', 0), reverse=True)
    merged = []
    
    while sorted_dets:
        current = sorted_dets.pop(0)
        current_box = current['box']
        
        # Find overlapping boxes
        to_remove = []
        for i, det in enumerate(sorted_dets):
            if box_iou(current_box, det['box']) > iou_threshold:
                # Merge: keep box with higher confidence
                to_remove.append(i)
        
        # Remove merged boxes
        for i in reversed(to_remove):
            sorted_dets.pop(i)
        
        merged.append(current)
    
    return merged


def box_iou(box1, box2):
    """🆕 Tính Intersection over Union của 2 boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def detect_all_text_regions(image_path, use_easyocr=True, detect_bubbles=True):
    """
    🆕 IMPROVED: Phát hiện tất cả vùng chứa text với confidence
    
    Returns:
        List[dict]: Combined text boxes + bubbles với confidence
    """
    all_regions = []
    
    # 1. Text boxes
    text_boxes = detect_text_boxes(image_path, use_easyocr)
    all_regions.extend(text_boxes)
    
    # 2. Speech bubbles
    if detect_bubbles:
        bubble_boxes = detect_speech_bubbles(image_path)
        all_regions.extend(bubble_boxes)
    
    return all_regions


def detect_people(image_path, use_yolo=True, min_confidence=0.3):
    """
    🆕 IMPROVED: Multi-model character detection với confidence
    
    Args:
        image_path: Đường dẫn ảnh
        use_yolo: True = dùng YOLO (best), False = multi-method
        min_confidence: Confidence tối thiểu
    
    Returns:
        List[dict]: [{'box': (x1,y1,x2,y2), 'confidence': float, 'method': str}]
    """
    all_detections = []
    
    # METHOD 1: YOLOv8 (most accurate)
    if use_yolo:
        try:
            from ultralytics import YOLO
            if not hasattr(detect_people, 'model'):
                print("🔄 Đang tải YOLO model...")
                detect_people.model = YOLO('yolov8n.pt')
            
            # YOLO tự đọc ảnh, không cần cv2.imread
            results = detect_people.model(str(image_path), verbose=False)
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == 0:  # person class
                        conf = float(box.conf[0])
                        if conf >= min_confidence:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            all_detections.append({
                                'box': (int(x1), int(y1), int(x2), int(y2)),
                                'confidence': conf,
                                'method': 'yolo'
                            })
            return all_detections
        except ImportError:
            print("⚠️  YOLO unavailable, using fallback methods")
        except Exception as e:
            print(f"⚠️  YOLO error: {e}")
    
    # Đọc ảnh cho fallback methods
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    
    # METHOD 2: Haar Cascade (face + upper body)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        upper_body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        for (x, y, w, h) in faces:
            all_detections.append({
                'box': (x, y, x+w, y+h),
                'confidence': 0.7,  # Face detection is quite reliable
                'method': 'haar_face'
            })
        
        bodies = upper_body_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))
        for (x, y, w, h) in bodies:
            all_detections.append({
                'box': (x, y, x+w, y+h),
                'confidence': 0.6,
                'method': 'haar_body'
            })
    except Exception as e:
        print(f"⚠️  Haar detection error: {e}")
    
    # METHOD 3: Skin color detection (backup)
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Skin color range in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        h, w = img.shape[:2]
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Must be significant size
            if area > (h * w * 0.02):  # At least 2% of image
                x, y, bbox_w, bbox_h = cv2.boundingRect(cnt)
                all_detections.append({
                    'box': (x, y, x+bbox_w, y+bbox_h),
                    'confidence': 0.4,  # Lower confidence for skin detection
                    'method': 'skin_color'
                })
    except Exception as e:
        print(f"⚠️  Skin detection error: {e}")
    
    # Merge overlapping detections
    merged = merge_overlapping_boxes(all_detections, iou_threshold=0.5)
    
    return merged


def get_important_region(image_path, detect_text=True, detect_person=True, detect_bubbles=True):
    """
    🆕 IMPROVED: Tìm vùng quan trọng với PRIORITY WEIGHTING
    
    Priority: TEXT > SPEECH BUBBLES > CHARACTERS
    - Text: weight 3.0 (must preserve)
    - Bubbles: weight 2.5 (important dialog)
    - Characters: weight 2.0 (main subjects)
    
    Returns:
        dict: {
            'region': (x1,y1,x2,y2),
            'confidence': float,
            'components': {text_boxes: [], bubbles: [], characters: []},
            'priority_score': float
        }
    """
    # Lấy kích thước ảnh mà không đọc toàn bộ pixel data
    with Image.open(image_path) as img:
        width, height = img.size
    
    components = {
        'text_boxes': [],
        'bubbles': [],
        'characters': []
    }
    
    weighted_regions = []
    
    # 1. Detect TEXT (highest priority)
    if detect_text:
        text_detections = detect_text_boxes(image_path, use_easyocr=False)
        for det in text_detections:
            box = det['box']
            conf = det['confidence']
            # Weight 3.0 for text
            weighted_regions.append({
                'box': box,
                'weight': 3.0 * conf,
                'type': 'text',
                'confidence': conf
            })
            components['text_boxes'].append(det)
    
    # 2. Detect SPEECH BUBBLES (high priority)
    if detect_bubbles:
        bubble_detections = detect_speech_bubbles(image_path)
        for det in bubble_detections:
            box = det['box']
            conf = det['confidence']
            # Weight 2.5 for bubbles
            weighted_regions.append({
                'box': box,
                'weight': 2.5 * conf,
                'type': 'bubble',
                'confidence': conf
            })
            components['bubbles'].append(det)
    
    # 3. Detect CHARACTERS (medium priority)
    if detect_person:
        # Thử YOLO trước (chính xác nhất), tự fallback sang Haar/skin nếu không có
        person_detections = detect_people(image_path, use_yolo=True)
        for det in person_detections:
            box = det['box']
            conf = det['confidence']
            # Weight 2.0 for characters
            weighted_regions.append({
                'box': box,
                'weight': 2.0 * conf,
                'type': 'character',
                'confidence': conf
            })
            components['characters'].append(det)
    
    if not weighted_regions:
        return None
    
    # Calculate weighted bounding box
    total_weight = sum(r['weight'] for r in weighted_regions)
    
    # Get overall bounding box
    all_boxes = [r['box'] for r in weighted_regions]
    x1 = min(box[0] for box in all_boxes)
    y1 = min(box[1] for box in all_boxes)
    x2 = max(box[2] for box in all_boxes)
    y2 = max(box[3] for box in all_boxes)
    
    # Adaptive padding based on content type
    region_w = x2 - x1
    region_h = y2 - y1
    
    # More padding for text (10-15%), less for characters (5-10%)
    has_text = len(components['text_boxes']) > 0 or len(components['bubbles']) > 0
    padding_factor = 0.15 if has_text else 0.08
    
    padding_x = int(region_w * padding_factor)
    padding_y = int(region_h * padding_factor)
    
    x1 = max(0, x1 - padding_x)
    y1 = max(0, y1 - padding_y)
    x2 = min(width, x2 + padding_x)
    y2 = min(height, y2 + padding_y)
    
    # Calculate priority score
    priority_score = total_weight / len(weighted_regions) if weighted_regions else 0
    
    # Calculate confidence
    avg_confidence = sum(r['confidence'] for r in weighted_regions) / len(weighted_regions)
    
    return {
        'region': (x1, y1, x2, y2),
        'confidence': avg_confidence,
        'components': components,
        'priority_score': priority_score,
        'text_count': len(components['text_boxes']),
        'bubble_count': len(components['bubbles']),
        'character_count': len(components['characters'])
    }


def analyze_shot_type(image_path, use_yolo=True):
    """
    Phân tích loại góc chụp (shot type) dựa trên tỷ lệ nhân vật trong ảnh
    
    Args:
        image_path: Đường dẫn ảnh
        use_yolo: Dùng YOLO để phát hiện nhân vật chính xác hơn (mặc định True, tự fallback nếu không có)
    
    Returns:
        dict: {
            'shot_type': 'wide' | 'medium' | 'close_up' | 'extreme_close_up',
            'character_ratio': float (0-1),
            'panel_weight': float (0.4-2.0),
            'description': str
        }
    """
    img = Image.open(image_path)
    width, height = img.size
    total_area = width * height
    
    # Phát hiện nhân vật (YOLO → Haar → skin color tự động fallback)
    person_boxes = detect_people(image_path, use_yolo=use_yolo)
    
    if not person_boxes:
        # Không có nhân vật → coi như cảnh rộng (landscape/establishing shot)
        return {
            'shot_type': 'wide',
            'character_ratio': 0.0,
            'panel_weight': 2.0,  # Panel lớn nhất
            'description': 'Establishing shot (không có nhân vật)'
        }
    
    # Tính tổng diện tích nhân vật (dùng UNION để tránh tính trùng khi overlap)
    total_character_area = 0
    for detection in person_boxes:
        box = detection['box']
        x1, y1, x2, y2 = box
        char_area = (x2 - x1) * (y2 - y1)
        total_character_area += char_area
    # Clamp để tránh tỷ lệ > 1 khi boxes overlap
    total_character_area = min(total_character_area, total_area)
    
    # Tính tỷ lệ nhân vật so với toàn bộ ảnh
    character_ratio = total_character_area / total_area
    
    # Phân loại shot type (4 mức)
    if character_ratio < 0.15:
        # Nhân vật rất nhỏ → Wide shot / Establishing shot
        return {
            'shot_type': 'wide',
            'character_ratio': character_ratio,
            'panel_weight': 1.8,  # Panel lớn để thể hiện bối cảnh
            'description': f'Wide shot ({character_ratio*100:.1f}% nhân vật) - Bối cảnh rộng'
        }
    elif character_ratio < 0.40:
        # Nhân vật trung bình → Medium shot
        return {
            'shot_type': 'medium',
            'character_ratio': character_ratio,
            'panel_weight': 1.0,  # Panel bình thường
            'description': f'Medium shot ({character_ratio*100:.1f}% nhân vật) - Cảnh thường'
        }
    elif character_ratio < 0.70:
        # Nhân vật lớn → Close-up / Detail shot
        return {
            'shot_type': 'close_up',
            'character_ratio': character_ratio,
            'panel_weight': 0.7,
            'description': f'Close-up ({character_ratio*100:.1f}% nhân vật) - Cận cảnh'
        }
    else:
        # Nhân vật chiếm gần toàn bộ khung → Extreme close-up (mắt, khuôn mặt, chi tiết)
        return {
            'shot_type': 'extreme_close_up',
            'character_ratio': character_ratio,
            'panel_weight': 0.6,  # Giữ tối thiểu 0.6 để tránh panel quá nhỏ
            'description': f'Extreme close-up ({character_ratio*100:.1f}% nhân vật) - Đặc tả chi tiết'
        }


def analyze_image_context(image_path, use_yolo=False):
    """
    🆕 IMPROVED: Phân tích toàn diện bối cảnh ảnh với confidence
    
    Returns:
        dict: {
            'shot_type_info': dict,
            'important_region_data': dict (with confidence, priority_score),
            'has_text': bool,
            'has_bubbles': bool,
            'has_characters': bool,
            'text_count': int,
            'bubble_count': int,
            'character_count': int
        }
    """
    shot_info = analyze_shot_type(image_path, use_yolo=use_yolo)
    
    # Phát hiện các vùng quan trọng với confidence
    important_region_data = get_important_region(
        image_path, 
        detect_text=True, 
        detect_person=True, 
        detect_bubbles=True
    )
    
    # Extract counts
    if important_region_data:
        text_count = important_region_data['text_count']
        bubble_count = important_region_data['bubble_count']
        character_count = important_region_data['character_count']
    else:
        text_count = bubble_count = character_count = 0
    
    return {
        'shot_type_info': shot_info,
        'important_region_data': important_region_data,
        'has_text': text_count > 0,
        'has_bubbles': bubble_count > 0,
        'has_characters': character_count > 0,
        'text_count': text_count,
        'bubble_count': bubble_count,
        'character_count': character_count,
        'priority_score': important_region_data['priority_score'] if important_region_data else 0,
        'confidence': important_region_data['confidence'] if important_region_data else 0
    }


def smart_crop_to_panel(image_path, panel_bounds, method='contain'):
    """
    🆕 IMPROVED: Crop ảnh thông minh với PRIORITY PRESERVATION
    
    Priority:
    1. MUST preserve text và speech bubbles (never crop)
    2. SHOULD preserve characters (crop only if necessary)
    3. MAY crop background
    
    Args:
        image_path: Đường dẫn ảnh
        panel_bounds: (x, y, w, h) của panel
        method: 'contain' = fit toàn bộ, 'cover' = fill panel, 'smart' = focus vùng quan trọng
    
    Returns:
        PIL.Image: Ảnh đã crop và resize
    """
    img = Image.open(image_path)
    img_w, img_h = img.size
    panel_x, panel_y, panel_w, panel_h = panel_bounds
    
    if method == 'smart':
        # Tìm vùng quan trọng với confidence
        important_data = get_important_region(image_path)
        
        if important_data:
            region = important_data['region']
            x1, y1, x2, y2 = region
            region_w = x2 - x1
            region_h = y2 - y1
            
            # Check priority: text/bubbles MUST be preserved
            has_critical_content = (important_data['text_count'] > 0 or 
                                   important_data['bubble_count'] > 0)
            
            # Tính aspect ratio
            region_aspect = region_w / region_h
            panel_aspect = panel_w / panel_h
            
            # VALIDATION: Check if cropping will cut off text/bubbles
            if has_critical_content:
                # Calculate required area to preserve text/bubbles
                components = important_data['components']
                critical_boxes = []
                
                # Collect all text and bubble boxes
                for text_det in components['text_boxes']:
                    critical_boxes.append(text_det['box'])
                for bubble_det in components['bubbles']:
                    critical_boxes.append(bubble_det['box'])
                
                if critical_boxes:
                    # Calculate minimum bounding box for critical content
                    crit_x1 = min(box[0] for box in critical_boxes)
                    crit_y1 = min(box[1] for box in critical_boxes)
                    crit_x2 = max(box[2] for box in critical_boxes)
                    crit_y2 = max(box[3] for box in critical_boxes)
                    
                    crit_w = crit_x2 - crit_x1
                    crit_h = crit_y2 - crit_y1
                    crit_aspect = crit_w / crit_h
                    
                    # If panel aspect doesn't match critical content, expand region
                    if abs(crit_aspect - panel_aspect) > 0.2:
                        # Add more padding to avoid cropping
                        extra_padding = 0.2
                        expand_x = int(crit_w * extra_padding)
                        expand_y = int(crit_h * extra_padding)
                        
                        x1 = max(0, crit_x1 - expand_x)
                        y1 = max(0, crit_y1 - expand_y)
                        x2 = min(img_w, crit_x2 + expand_x)
                        y2 = min(img_h, crit_y2 + expand_y)
                        
                        region_w = x2 - x1
                        region_h = y2 - y1
                        region_aspect = region_w / region_h
            
            # Crop vùng quan trọng
            cropped = img.crop((x1, y1, x2, y2))
            
            # Resize để fit panel
            if region_aspect > panel_aspect:
                # Vùng ngang hơn panel -> scale theo width
                new_w = int(panel_w)
                new_h = int(panel_w / region_aspect)
            else:
                # Vùng dọc hơn panel -> scale theo height
                new_h = int(panel_h)
                new_w = int(panel_h * region_aspect)
            
            resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
            return resized
    
    # Fallback: Crop center (method gốc)
    img_aspect = img_w / img_h
    panel_aspect = panel_w / panel_h
    
    if img_aspect > panel_aspect:
        # Ảnh ngang hơn panel
        new_h = img_h
        new_w = int(img_h * panel_aspect)
        crop_x = (img_w - new_w) // 2
        crop_box = (crop_x, 0, crop_x + new_w, img_h)
    else:
        # Ảnh dọc hơn panel
        new_w = img_w
        new_h = int(img_w / panel_aspect)
        crop_y = (img_h - new_h) // 2
        crop_box = (0, crop_y, img_w, crop_y + new_h)
    
    cropped = img.crop(crop_box)
    resized = cropped.resize((int(panel_w), int(panel_h)), Image.Resampling.LANCZOS)
    return resized


if __name__ == "__main__":
    # Test
    print("🧪 Testing Smart Crop...")
    
    # Test với 1 ảnh
    test_image = "images/Screenshot 2026-02-02 073351.png"
    
    if os.path.exists(test_image):
        print(f"\n📸 Testing: {test_image}")
        
        # Test phát hiện text
        print("🔍 Phát hiện text...")
        text_boxes = detect_text_boxes(test_image, use_easyocr=False)
        print(f"   ✓ Tìm thấy {len(text_boxes)} text boxes")
        
        # Test phát hiện người
        print("🔍 Phát hiện người...")
        person_boxes = detect_people(test_image, use_yolo=False)
        print(f"   ✓ Tìm thấy {len(person_boxes)} người")
        
        # Test vùng quan trọng
        print("🔍 Tìm vùng quan trọng...")
        region = get_important_region(test_image)
        if region:
            print(f"   ✓ Vùng quan trọng: {region}")
        else:
            print("   ℹ️  Không tìm thấy vùng đặc biệt")
    else:
        print("❌ Không tìm thấy ảnh test")


def center_crop_to_aspect(img, target_aspect):
    """
    Crop ảnh từ trung tâm về aspect ratio mong muốn.
    
    Args:
        img: PIL Image
        target_aspect: float - Tỷ lệ width/height mong muốn
    
    Returns:
        PIL Image đã được crop
    """
    current_w, current_h = img.size
    current_aspect = current_w / current_h
    
    if abs(current_aspect - target_aspect) < 0.01:
        return img  # Đã đúng aspect rồi
    
    if current_aspect > target_aspect:
        # Ảnh quá ngang, crop 2 bên
        new_w = int(current_h * target_aspect)
        left = (current_w - new_w) // 2
        return img.crop((left, 0, left + new_w, current_h))
    else:
        # Ảnh quá dọc, crop trên/dưới
        new_h = int(current_w / target_aspect)
        top = (current_h - new_h) // 2
        return img.crop((0, top, current_w, top + new_h))


def get_nearest_standard_aspect(aspect):
    """
    Tìm aspect ratio chuẩn gần nhất.
    
    Args:
        aspect: float - Aspect ratio hiện tại (width/height)
    
    Returns:
        tuple: (aspect_name, aspect_value)
    """
    standard_aspects = {
        '1:1': 1.0,
        '4:3': 4/3,
        '3:2': 3/2,
        '16:9': 16/9,
        '21:9': 21/9,
        '2:3': 2/3,
        '3:4': 3/4,
        '9:16': 9/16
    }
    
    closest = min(standard_aspects.items(), key=lambda x: abs(x[1] - aspect))
    return closest[0], closest[1]

