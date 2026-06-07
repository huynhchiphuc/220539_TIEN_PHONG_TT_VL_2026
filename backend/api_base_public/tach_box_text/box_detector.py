"""
Utilities for text boxes and YOLO person boxes.
"""
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import numpy as np


def _find_contours_compat(image, mode, method):
    """Compatible wrapper for cv2.findContours across OpenCV 3/4."""
    result = cv2.findContours(image, mode, method)
    if len(result) == 2:
        return result[0], result[1]
    if len(result) == 3:
        return result[1], result[2]
    return [], None


def box_iou(box1, box2):
    """Compute IoU for two boxes."""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    if x2_i < x1_i or y2_i < y1_i:
        return 0.0

    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def merge_overlapping_boxes(detections, iou_threshold=0.5):
    """Merge overlapping boxes by confidence."""
    if not detections:
        return []

    sorted_dets = sorted(detections, key=lambda x: x.get("confidence", 0), reverse=True)
    merged = []

    while sorted_dets:
        current = sorted_dets.pop(0)
        current_box = current["box"]

        to_remove = []
        for i, det in enumerate(sorted_dets):
            if box_iou(current_box, det["box"]) > iou_threshold:
                to_remove.append(i)

        for i in reversed(to_remove):
            sorted_dets.pop(i)

        merged.append(current)

    return merged


def detect_text_boxes(image_path, use_easyocr=True, min_confidence=0.3):
    """
    Detect text-like regions using EasyOCR or fallback methods.

    Returns a list of dicts with keys: box, confidence, text, method.
    """
    all_detections: List[Dict] = []

    if use_easyocr:
        try:
            import easyocr
            if not hasattr(detect_text_boxes, "reader"):
                print("Loading EasyOCR model...")
                detect_text_boxes.reader = easyocr.Reader(["vi", "en"], gpu=False)

            results = detect_text_boxes.reader.readtext(str(image_path))
            for (bbox, text, prob) in results:
                if prob >= min_confidence:
                    pts = np.array(bbox)
                    x1, y1 = pts.min(axis=0)
                    x2, y2 = pts.max(axis=0)
                    all_detections.append(
                        {
                            "box": (int(x1), int(y1), int(x2), int(y2)),
                            "confidence": float(prob),
                            "text": text,
                            "method": "easyocr",
                        }
                    )
            return all_detections
        except ImportError:
            print("EasyOCR not installed, using fallback methods")

    img = cv2.imread(str(image_path))
    if img is None:
        return []

    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        for region in regions:
            x, y, w, h = cv2.boundingRect(region)
            aspect = w / h if h > 0 else 0
            if 0.1 < aspect < 10 and w * h > 200:
                all_detections.append(
                    {
                        "box": (x, y, x + w, y + h),
                        "confidence": 0.7,
                        "text": "",
                        "method": "mser",
                    }
                )
    except Exception as exc:
        print(f"MSER detection failed: {exc}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = _find_contours_compat(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / h if h > 0 else 0
            if 0.2 < aspect < 8:
                all_detections.append(
                    {
                        "box": (x, y, x + w, y + h),
                        "confidence": 0.5,
                        "text": "",
                        "method": "contour",
                    }
                )

    merged = merge_overlapping_boxes(all_detections, iou_threshold=0.5)
    return merged


def detect_people(image_path, use_yolo=True, min_confidence=0.3):
    """
    Detect people with YOLO (preferred) and fallback methods.

    Returns a list of dicts with keys: box, confidence, method.
    """
    all_detections: List[Dict] = []

    if use_yolo:
        try:
            from ultralytics import YOLO

            if not hasattr(detect_people, "model"):
                print("Loading YOLO model...")
                model_path = Path(__file__).resolve().parents[1] / "app" / "services" / "ai" / "yolov8n.pt"
                detect_people.model = YOLO(str(model_path))

            results = detect_people.model(str(image_path), verbose=False)
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == 0:
                        conf = float(box.conf[0])
                        if conf >= min_confidence:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            all_detections.append(
                                {
                                    "box": (int(x1), int(y1), int(x2), int(y2)),
                                    "confidence": conf,
                                    "method": "yolo",
                                }
                            )
            return all_detections
        except ImportError:
            print("YOLO unavailable, using fallback methods")
        except Exception as exc:
            print(f"YOLO error: {exc}")

    img = cv2.imread(str(image_path))
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        upper_body_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_upperbody.xml"
        )

        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        for (x, y, w, h) in faces:
            all_detections.append(
                {
                    "box": (x, y, x + w, y + h),
                    "confidence": 0.7,
                    "method": "haar_face",
                }
            )

        bodies = upper_body_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))
        for (x, y, w, h) in bodies:
            all_detections.append(
                {
                    "box": (x, y, x + w, y + h),
                    "confidence": 0.6,
                    "method": "haar_body",
                }
            )
    except Exception as exc:
        print(f"Haar detection error: {exc}")

    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = _find_contours_compat(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = img.shape[:2]
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (h * w * 0.02):
                x, y, bbox_w, bbox_h = cv2.boundingRect(cnt)
                all_detections.append(
                    {
                        "box": (x, y, x + bbox_w, y + bbox_h),
                        "confidence": 0.4,
                        "method": "skin_color",
                    }
                )
    except Exception as exc:
        print(f"Skin detection error: {exc}")

    merged = merge_overlapping_boxes(all_detections, iou_threshold=0.5)
    return merged
