"""
Layout Evaluator Module - Module 5
Đánh giá chất lượng layout dựa trên balance score
Theo yêu cầu: Automatic Comic Page Layout Generation Based on Image Content Analysis
"""

import numpy as np
from typing import Dict, List, Tuple, Any


class Panel:
    """
    Panel data structure cho evaluation
    
    Attributes:
        panel_id: Unique identifier
        x, y, width, height: Position và size (normalized 0-1 hoặc pixels)
        area_ratio: Tỷ lệ diện tích panel / diện tích trang (0-1)
        aspect_ratio: width / height
        shape_type: 'rectangular' | 'diagonal'
        angle_type: '90' | '<90'
        scene_type: 'close_up' | 'group' | 'action' | 'dialogue' | 'normal'
    """
    
    def __init__(self, x=0, y=0, width=100, height=100, **kwargs):
        self.panel_id = kwargs.get('panel_id', None)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # Calculate derived properties
        self.area = width * height
        self.area_ratio = kwargs.get('area_ratio', None)
        self.aspect_ratio = width / height if height > 0 else 1.0
        
        # Shape properties
        self.shape_type = kwargs.get('shape_type', 'rectangular')
        self.angle_type = kwargs.get('angle_type', '90')
        self.scene_type = kwargs.get('scene_type', 'normal')
    
    def __repr__(self):
        return (f"Panel(id={self.panel_id}, pos=({self.x:.0f},{self.y:.0f}), "
                f"size=({self.width:.0f}x{self.height:.0f}), "
                f"area_ratio={self.area_ratio:.2f if self.area_ratio else 0:.2f})")


class LayoutEvaluator:
    """
    Đánh giá chất lượng layout theo công thức:
    
    balance_score = dominant_area_ratio * 0.4 +
                    rectangular_ratio * 0.3 +
                    size_variance * 0.3
    
    Rating thresholds:
    > 0.75: Tốt
    0.6-0.75: Ổn
    < 0.6: Cần tối ưu
    """
    
    # Thresholds theo yêu cầu đề bài
    RATING_THRESHOLDS = {
        'excellent': 0.75,
        'good': 0.60
    }
    
    # Ideal values cho mỗi component
    IDEAL_VALUES = {
        'dominant_area': (0.30, 0.45),      # 30-45% là dominant
        'rectangular_ratio': 0.70,          # 70-100% rectangular
        'cv': (0.3, 0.6)                    # Coefficient of variation 0.3-0.6
    }
    
    def __init__(self):
        self.evaluation_history = []
    
    def calculate_balance_score(self, panels: List[Panel], page_width: float = 100, 
                                page_height: float = 140) -> Dict:
        """
        Tính balance_score theo công thức yêu cầu
        
        Args:
            panels: List[Panel] - Các panels trong layout
            page_width, page_height: Kích thước trang (để tính area_ratio nếu chưa có)
        
        Returns:
            Dict với:
                - balance_score: float (0-1)
                - rating: str ('Tốt' | 'Ổn' | 'Cần tối ưu')
                - color: str ('green' | 'yellow' | 'red')
                - components: Dict chi tiết các thành phần
        """
        if not panels:
            return {
                'balance_score': 0.0,
                'rating': 'Invalid',
                'color': 'red',
                'error': 'No panels provided'
            }
        
        page_area = page_width * page_height
        
        # Calculate area_ratio cho mỗi panel nếu chưa có
        for panel in panels:
            if panel.area_ratio is None:
                panel.area_ratio = panel.area / page_area
        
        areas = [p.area_ratio for p in panels]
        
        # ============================================================
        # COMPONENT 1: Dominant Area Ratio (0.4 weight)
        # ============================================================
        dominant_area = max(areas)
        
        ideal_min, ideal_max = self.IDEAL_VALUES['dominant_area']
        
        if ideal_min <= dominant_area <= ideal_max:
            dominant_score = 1.0
        else:
            # Penalize deviation from 37.5% (center of 30-45%)
            ideal_center = (ideal_min + ideal_max) / 2
            deviation = abs(dominant_area - ideal_center) / ideal_center
            dominant_score = max(0.0, 1.0 - deviation)
        
        # ============================================================
        # COMPONENT 2: Rectangular Ratio (0.3 weight)
        # ============================================================
        rectangular_count = sum(1 for p in panels if p.angle_type == '90')
        rectangular_ratio = rectangular_count / len(panels)
        
        ideal_rect = self.IDEAL_VALUES['rectangular_ratio']
        
        if rectangular_ratio >= ideal_rect:
            rect_score = 1.0
        else:
            # Penalize low rectangular ratio
            rect_score = rectangular_ratio / ideal_rect
        
        # ============================================================
        # COMPONENT 3: Size Variance (0.3 weight)
        # ============================================================
        mean_area = np.mean(areas)
        variance = np.var(areas)
        std_dev = np.sqrt(variance)
        
        # Coefficient of variation (CV) - normalized std dev
        cv = std_dev / mean_area if mean_area > 0 else 0
        
        # Ideal CV: 0.3-0.6 (good variety, not extreme)
        cv_min, cv_max = self.IDEAL_VALUES['cv']
        
        if cv_min <= cv <= cv_max:
            variance_score = 1.0
        elif cv < cv_min:
            # Too uniform
            variance_score = cv / cv_min
        else:
            # Too chaotic (cv > cv_max)
            variance_score = max(0.0, 1.0 - (cv - cv_max) / 0.4)
        
        # ============================================================
        # FINAL BALANCE SCORE (Weighted Sum)
        # ============================================================
        balance_score = (
            dominant_score * 0.4 +
            rect_score * 0.3 +
            variance_score * 0.3
        )
        
        # ============================================================
        # RATING CLASSIFICATION
        # ============================================================
        if balance_score > self.RATING_THRESHOLDS['excellent']:
            rating = "Tốt"
            color = "green"
        elif balance_score >= self.RATING_THRESHOLDS['good']:
            rating = "Ổn"
            color = "yellow"
        else:
            rating = "Cần tối ưu"
            color = "red"
        
        result = {
            'balance_score': round(balance_score, 3),
            'rating': rating,
            'color': color,
            'components': {
                'dominant_area_ratio': round(dominant_area, 3),
                'dominant_score': round(dominant_score, 3),
                'rectangular_ratio': round(rectangular_ratio, 3),
                'rect_score': round(rect_score, 3),
                'size_variance': round(variance, 4),
                'cv': round(cv, 3),
                'variance_score': round(variance_score, 3)
            },
            'weights': {
                'dominant': 0.4,
                'rectangular': 0.3,
                'variance': 0.3
            }
        }
        
        return result
    
    def evaluate_page(self, page_layout: List[Panel], page_width: float = 100,
                     page_height: float = 140) -> Dict:
        """
        Đánh giá 1 trang với balance score + constraint validation
        
        Returns:
            Dict với balance_score, rating, violations, panel statistics
        """
        if not page_layout:
            return {
                'error': 'Empty page layout',
                'balance_score': 0.0,
                'rating': 'Invalid'
            }
        
        # Calculate balance score
        balance = self.calculate_balance_score(page_layout, page_width, page_height)
        
        # Panel statistics
        panel_count = len(page_layout)
        diagonal_count = sum(1 for p in page_layout if p.angle_type == '<90')
        diagonal_ratio = diagonal_count / panel_count if panel_count > 0 else 0
        
        areas = [p.area_ratio for p in page_layout]
        dominant_area = max(areas)
        
        # ============================================================
        # CONSTRAINT VALIDATION
        # ============================================================
        violations = []
        
        # Constraint 1: 4-7 panels per page
        if not (4 <= panel_count <= 7):
            violations.append({
                'type': 'panel_count',
                'message': f"Panel count {panel_count} ngoài range 4-7",
                'severity': 'high'
            })
        
        # Constraint 2: Dominant panel 30-45%
        if not (0.30 <= dominant_area <= 0.45):
            violations.append({
                'type': 'dominant_area',
                'message': f"Dominant panel {dominant_area:.1%} ngoài range 30-45%",
                'severity': 'medium'
            })
        
        # Constraint 3: Dynamic panels ≤ 30%
        if diagonal_ratio > 0.30:
            violations.append({
                'type': 'diagonal_ratio',
                'message': f"Dynamic panels {diagonal_ratio:.1%} vượt 30%",
                'severity': 'low'
            })
        
        # Constraint 4: Check 3 consecutive same size
        consecutive_same = self._check_consecutive_same_size(page_layout)
        if consecutive_same:
            violations.append({
                'type': 'consecutive_same',
                'message': f"Có {consecutive_same} panels cùng size liên tiếp",
                'severity': 'medium'
            })
        
        result = {
            'balance_score': balance['balance_score'],
            'rating': balance['rating'],
            'color': balance['color'],
            'panel_count': panel_count,
            'diagonal_count': diagonal_count,
            'diagonal_ratio': round(diagonal_ratio, 3),
            'dominant_area': round(dominant_area, 3),
            'violations': violations,
            'violation_count': len(violations),
            'is_valid': len(violations) == 0,
            'details': balance
        }
        
        return result
    
    def _check_consecutive_same_size(self, panels: List[Panel], 
                                    tolerance: float = 0.05) -> int:
        """
        Kiểm tra có 3+ panels liên tiếp cùng size không
        
        Returns:
            Max number of consecutive same-size panels (0 nếu không có vi phạm)
        """
        if len(panels) < 3:
            return 0
        
        areas = [p.area_ratio for p in panels]
        
        max_consecutive = 0
        current_consecutive = 1
        
        for i in range(1, len(areas)):
            # Check if current area ≈ previous area (within tolerance)
            if abs(areas[i] - areas[i-1]) <= tolerance:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        
        # Return violation count (3+ consecutive = violation)
        return max_consecutive if max_consecutive >= 3 else 0
    
    def evaluate_comic(self, pages: List[List[Panel]], page_width: float = 100,
                      page_height: float = 140) -> Dict:
        """
        Đánh giá toàn bộ comic (multiple pages)
        
        Returns:
            Dict với overall statistics, page-by-page scores, violations
        """
        if not pages:
            return {
                'error': 'No pages provided',
                'overall_balance': 0.0
            }
        
        page_scores = []
        
        for i, page in enumerate(pages):
            score = self.evaluate_page(page, page_width, page_height)
            score['page_number'] = i + 1
            page_scores.append(score)
            
            # Store in history
            self.evaluation_history.append({
                'page_number': i + 1,
                'score': score
            })
        
        # Overall statistics
        valid_scores = [p['balance_score'] for p in page_scores]
        avg_balance = np.mean(valid_scores) if valid_scores else 0.0
        min_balance = np.min(valid_scores) if valid_scores else 0.0
        max_balance = np.max(valid_scores) if valid_scores else 0.0
        
        total_violations = sum(p['violation_count'] for p in page_scores)
        total_panels = sum(p['panel_count'] for p in page_scores)
        
        # Rating distribution
        rating_counts = {}
        for p in page_scores:
            rating = p['rating']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        # Overall rating based on average
        if avg_balance > self.RATING_THRESHOLDS['excellent']:
            overall_rating = "Tốt"
        elif avg_balance >= self.RATING_THRESHOLDS['good']:
            overall_rating = "Ổn"
        else:
            overall_rating = "Cần tối ưu"
        
        result = {
            'overall_balance': round(avg_balance, 3),
            'overall_rating': overall_rating,
            'min_balance': round(min_balance, 3),
            'max_balance': round(max_balance, 3),
            'total_pages': len(pages),
            'total_panels': total_panels,
            'total_violations': total_violations,
            'rating_distribution': rating_counts,
            'page_scores': page_scores
        }
        
        return result
    
    def get_improvement_suggestions(self, evaluation: Dict) -> List[str]:
        """
        Đề xuất cải thiện dựa trên evaluation result
        
        Args:
            evaluation: Result từ evaluate_page() hoặc evaluate_comic()
        
        Returns:
            List[str] - Các đề xuất cải thiện
        """
        suggestions = []
        
        if 'details' in evaluation:
            components = evaluation['details']['components']
            
            # Suggestion 1: Dominant area
            if components['dominant_score'] < 0.8:
                dom_area = components['dominant_area_ratio']
                if dom_area < 0.30:
                    suggestions.append(
                        f"Tăng kích thước panel chính lên 30-45% "
                        f"(hiện tại {dom_area:.1%})"
                    )
                elif dom_area > 0.45:
                    suggestions.append(
                        f"Giảm kích thước panel chính xuống 30-45% "
                        f"(hiện tại {dom_area:.1%})"
                    )
            
            # Suggestion 2: Rectangular ratio
            if components['rect_score'] < 0.8:
                rect_ratio = components['rectangular_ratio']
                suggestions.append(
                    f"Tăng tỷ lệ panels vuông góc lên ≥70% "
                    f"(hiện tại {rect_ratio:.1%})"
                )
            
            # Suggestion 3: Size variance
            if components['variance_score'] < 0.8:
                cv = components['cv']
                if cv < 0.3:
                    suggestions.append(
                        "Tăng đa dạng kích thước panels (hiện tại quá đồng nhất)"
                    )
                elif cv > 0.6:
                    suggestions.append(
                        "Giảm sự chênh lệch kích thước panels (hiện tại quá hỗn loạn)"
                    )
        
        # Suggestions from violations
        if 'violations' in evaluation:
            for violation in evaluation['violations']:
                if violation['type'] == 'panel_count':
                    panel_count = evaluation.get('panel_count', 0)
                    if panel_count < 4:
                        suggestions.append("Thêm panels để đạt 4-7 panels/trang")
                    elif panel_count > 7:
                        suggestions.append("Giảm số panels xuống 4-7 panels/trang")
                
                elif violation['type'] == 'diagonal_ratio':
                    suggestions.append("Giảm số panels dynamic angle xuống ≤30%")
                
                elif violation['type'] == 'consecutive_same':
                    suggestions.append(
                        "Tránh 3+ panels cùng kích thước liên tiếp - "
                        "thêm nhịp điệu (lớn → nhỏ → trung bình)"
                    )
        
        return suggestions
    
    def export_report(self, evaluation: Dict, format: str = 'text') -> str:
        """
        Export evaluation report
        
        Args:
            evaluation: Result từ evaluate_page() hoặc evaluate_comic()
            format: 'text' | 'json' | 'html'
        
        Returns:
            str - Formatted report
        """
        if format == 'text':
            return self._format_text_report(evaluation)
        elif format == 'json':
            import json
            return json.dumps(evaluation, indent=2, ensure_ascii=False)
        elif format == 'html':
            return self._format_html_report(evaluation)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_text_report(self, evaluation: Dict) -> str:
        """Format evaluation as text report"""
        lines = []
        lines.append("=" * 60)
        lines.append("LAYOUT EVALUATION REPORT")
        lines.append("=" * 60)
        
        # Overall score
        score = evaluation.get('balance_score', evaluation.get('overall_balance', 0))
        rating = evaluation.get('rating', evaluation.get('overall_rating', 'N/A'))
        
        lines.append(f"\nBalance Score: {score:.3f}")
        lines.append(f"Rating: {rating}")
        
        # Details
        if 'details' in evaluation:
            lines.append("\n" + "-" * 60)
            lines.append("COMPONENTS")
            lines.append("-" * 60)
            
            comp = evaluation['details']['components']
            lines.append(f"Dominant Area: {comp['dominant_area_ratio']:.1%} "
                        f"(score: {comp['dominant_score']:.2f})")
            lines.append(f"Rectangular Ratio: {comp['rectangular_ratio']:.1%} "
                        f"(score: {comp['rect_score']:.2f})")
            lines.append(f"Size Variance CV: {comp['cv']:.2f} "
                        f"(score: {comp['variance_score']:.2f})")
        
        # Violations
        if 'violations' in evaluation and evaluation['violations']:
            lines.append("\n" + "-" * 60)
            lines.append("VIOLATIONS")
            lines.append("-" * 60)
            
            for v in evaluation['violations']:
                lines.append(f"[{v['severity'].upper()}] {v['message']}")
        
        # Suggestions
        suggestions = self.get_improvement_suggestions(evaluation)
        if suggestions:
            lines.append("\n" + "-" * 60)
            lines.append("SUGGESTIONS")
            lines.append("-" * 60)
            
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{i}. {s}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def _format_html_report(self, evaluation: Dict) -> str:
        """Format evaluation as HTML report"""
        # Simplified HTML generation
        score = evaluation.get('balance_score', evaluation.get('overall_balance', 0))
        rating = evaluation.get('rating', evaluation.get('overall_rating', 'N/A'))
        color = evaluation.get('color', 'gray')
        
        html = f"""
        <div class="layout-evaluation" style="border: 2px solid {color}; padding: 20px;">
            <h2>Layout Evaluation</h2>
            <div class="score" style="font-size: 24px; color: {color};">
                Balance Score: {score:.3f} - {rating}
            </div>
        </div>
        """
        
        return html


def test_layout_evaluator():
    """Test function for LayoutEvaluator"""
    print("=" * 80)
    print("LAYOUT EVALUATOR TEST")
    print("=" * 80)
    
    evaluator = LayoutEvaluator()
    
    # Test case 1: Good layout
    print("\n" + "=" * 80)
    print("TEST 1: GOOD LAYOUT (Expected: Tốt)")
    print("=" * 80)
    
    good_panels = [
        Panel(0, 0, 50, 60, area_ratio=0.35, angle_type='90'),     # Dominant
        Panel(50, 0, 50, 30, area_ratio=0.18, angle_type='90'),
        Panel(50, 30, 50, 30, area_ratio=0.18, angle_type='90'),
        Panel(0, 60, 33, 40, area_ratio=0.15, angle_type='90'),
        Panel(33, 60, 33, 40, area_ratio=0.14, angle_type='<90')    # 1 diagonal
    ]
    
    result1 = evaluator.evaluate_page(good_panels)
    print(evaluator.export_report(result1, format='text'))
    
    # Test case 2: Poor layout
    print("\n" + "=" * 80)
    print("TEST 2: POOR LAYOUT (Expected: Cần tối ưu)")
    print("=" * 80)
    
    poor_panels = [
        Panel(0, 0, 100, 35, area_ratio=0.25, angle_type='<90'),   # No dominant
        Panel(0, 35, 100, 35, area_ratio=0.25, angle_type='<90'),  # Too many diagonal
        Panel(0, 70, 100, 35, area_ratio=0.25, angle_type='<90'),
        Panel(0, 105, 100, 35, area_ratio=0.25, angle_type='<90')  # All same size
    ]
    
    result2 = evaluator.evaluate_page(poor_panels)
    print(evaluator.export_report(result2, format='text'))
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == '__main__':
    test_layout_evaluator()
