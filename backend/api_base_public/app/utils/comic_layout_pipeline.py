"""
Comic Layout Pipeline - Complete Integration
Kết nối tất cả modules: ImageAnalyzer → SceneClassifier → PanelGenerator → LayoutEvaluator
Theo yêu cầu: Automatic Comic Page Layout Generation Based on Image Content Analysis
"""

import os
from typing import List, Dict, Tuple
import json

# Import các modules
from image_analyzer import ImageAnalyzer
from scene_classifier import SceneClassifier
from panel_generator import PanelGenerator
from layout_evaluator import LayoutEvaluator, Panel


class ComicLayoutPipeline:
    """
    Complete pipeline:
    
    Input Images (100+)
        ↓
    [1] ImageAnalyzer → metrics (character_count, motion_score, text_density, ...)
        ↓
    [2] SceneClassifier → scene_type (close_up, group, action, dialogue, normal)
        ↓
    [3] PanelGenerator → panel_spec (shape, aspect, area_ratio)
        ↓
    [4] LayoutEngine → layout (existing comic_book_auto_fill / comic_layout_simple)
        ↓
    [5] LayoutEvaluator → balance_score, rating, violations
        ↓
    Output: Comic pages with evaluation
    """
    
    def __init__(self, use_yolo=False, use_easyocr=False, seed=None):
        """
        Args:
            use_yolo: Dùng YOLO cho character detection (chậm hơn, chính xác hơn)
            use_easyocr: Dùng EasyOCR cho text detection (chậm hơn, chính xác hơn)
            seed: Random seed cho reproducibility
        """
        self.image_analyzer = ImageAnalyzer(use_yolo=use_yolo, use_easyocr=use_easyocr)
        self.scene_classifier = SceneClassifier()
        self.panel_generator = PanelGenerator(seed=seed)
        self.layout_evaluator = LayoutEvaluator()
        
        self.pipeline_history = []
    
    def process_images(self, image_paths: List[str], verbose: bool = True) -> Dict:
        """
        Xử lý pipeline đầy đủ cho danh sách ảnh
        
        Args:
            image_paths: List[str] - Đường dẫn các ảnh
            verbose: bool - In progress logs
        
        Returns:
            Dict với:
                - image_analyses: List[Dict] - Kết quả từ ImageAnalyzer
                - scene_classifications: List[Dict] - Kết quả từ SceneClassifier
                - panel_specs: List[Dict] - Kết quả từ PanelGenerator
                - statistics: Dict - Thống kê tổng hợp
        """
        if verbose:
            print("=" * 80)
            print(f"COMIC LAYOUT PIPELINE - Processing {len(image_paths)} images")
            print("=" * 80)
        
        # ============================================================
        # STEP 1: IMAGE ANALYSIS
        # ============================================================
        if verbose:
            print("\n[1/4] Image Analysis...")
        
        image_analyses = self.image_analyzer.analyze_batch(image_paths)
        
        if verbose:
            stats = self.image_analyzer.get_statistics(image_analyses)
            print(f"  ✓ Analyzed {len(image_analyses)} images")
            print(f"  Metrics:")
            for metric, data in stats.items():
                if isinstance(data, dict) and 'mean' in data:
                    print(f"    {metric}: mean={data['mean']:.3f}, std={data['std']:.3f}")
        
        # ============================================================
        # STEP 2: SCENE CLASSIFICATION
        # ============================================================
        if verbose:
            print("\n[2/4] Scene Classification...")
        
        scene_classifications = self.scene_classifier.classify_batch(image_analyses)
        
        if verbose:
            scene_stats = self.scene_classifier.get_scene_statistics()
            print(f"  ✓ Classified {len(scene_classifications)} scenes")
            print(f"  Scene distribution:")
            for scene, data in scene_stats.items():
                if data['count'] > 0:
                    print(f"    {scene}: {data['count']} ({data['percentage']:.1f}%)")
        
        # ============================================================
        # STEP 3: PANEL GENERATION
        # ============================================================
        if verbose:
            print("\n[3/4] Panel Generation...")
        
        panel_specs = self.panel_generator.generate_panels_batch(scene_classifications)
        
        # Enforce dominant panel rule
        panel_specs = self.panel_generator.enforce_dominant_panel(panel_specs)
        
        # Validate panel count
        validation = self.panel_generator.validate_panel_count(panel_specs)
        
        if verbose:
            print(f"  ✓ Generated {len(panel_specs)} panels")
            print(f"  Validation: {validation['recommendation']}")
            
            gen_stats = self.panel_generator.get_statistics()
            print(f"  Panel types:")
            for shape, count in gen_stats['shape_type_counts'].items():
                print(f"    {shape}: {count}")
        
        # ============================================================
        # STEP 4: STATISTICS & VALIDATION
        # ============================================================
        if verbose:
            print("\n[4/4] Statistics & Validation...")
        
        # Scene distribution validation
        scene_types = [s['scene_type'] for s in scene_classifications]
        scene_validation = self.scene_classifier.validate_scene_distribution(scene_types)
        
        if verbose:
            if scene_validation['warnings']:
                print("  ⚠️  Warnings:")
                for warning in scene_validation['warnings']:
                    print(f"    - {warning}")
            else:
                print("  ✓ Scene distribution valid")
        
        # Compile statistics
        statistics = {
            'total_images': len(image_paths),
            'total_panels': len(panel_specs),
            'image_metrics': self.image_analyzer.get_statistics(image_analyses),
            'scene_distribution': scene_stats,
            'scene_validation': scene_validation,
            'panel_validation': validation,
            'panel_statistics': gen_stats
        }
        
        # Store in history
        pipeline_result = {
            'image_analyses': image_analyses,
            'scene_classifications': scene_classifications,
            'panel_specs': panel_specs,
            'statistics': statistics
        }
        
        self.pipeline_history.append(pipeline_result)
        
        if verbose:
            print("\n" + "=" * 80)
            print("PIPELINE COMPLETED ✓")
            print("=" * 80)
        
        return pipeline_result
    
    def evaluate_layout(self, panel_specs: List[Dict], page_width: float = 100,
                       page_height: float = 140, verbose: bool = True) -> Dict:
        """
        Đánh giá layout quality với LayoutEvaluator
        
        Args:
            panel_specs: List[Dict] - Panel specs từ PanelGenerator
            page_width, page_height: Kích thước trang
            verbose: Print evaluation report
        
        Returns:
            Dict - Evaluation result
        """
        # Convert panel_specs to Panel objects
        panels = []
        
        for spec in panel_specs:
            # Calculate position & size from area_ratio & aspect_ratio
            area_ratio = spec['area_ratio']
            aspect = spec['aspect_ratio']
            
            # Simple placement (can be improved với actual layout algorithm)
            # Assume square page for now
            area = area_ratio * page_width * page_height
            
            # width / height = aspect
            # width * height = area
            # → height = sqrt(area / aspect), width = aspect * height
            import math
            height = math.sqrt(area / aspect)
            width = aspect * height
            
            panel = Panel(
                x=0, y=0,  # Position to be determined by layout engine
                width=width,
                height=height,
                panel_id=spec['panel_id'],
                area_ratio=area_ratio,
                shape_type=spec['shape_type'],
                angle_type=spec['angle_type'],
                scene_type=spec['scene_type']
            )
            
            panels.append(panel)
        
        # Evaluate
        evaluation = self.layout_evaluator.evaluate_page(panels, page_width, page_height)
        
        if verbose:
            report = self.layout_evaluator.export_report(evaluation, format='text')
            print(report)
        
        return evaluation
    
    def export_results(self, pipeline_result: Dict, output_path: str,
                      format: str = 'json'):
        """
        Export pipeline results
        
        Args:
            pipeline_result: Dict từ process_images()
            output_path: Đường dẫn file output
            format: 'json' | 'txt'
        """
        if format == 'json':
            # Convert numpy types to Python native
            import numpy as np
            
            def convert_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_types(item) for item in obj]
                else:
                    return obj
            
            clean_result = convert_types(pipeline_result)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(clean_result, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Exported to {output_path}")
        
        elif format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("COMIC LAYOUT PIPELINE RESULTS\n")
                f.write("=" * 80 + "\n\n")
                
                # Statistics
                stats = pipeline_result['statistics']
                f.write(f"Total images: {stats['total_images']}\n")
                f.write(f"Total panels: {stats['total_panels']}\n\n")
                
                # Scene distribution
                f.write("Scene Distribution:\n")
                for scene, data in stats['scene_distribution'].items():
                    if data['count'] > 0:
                        f.write(f"  {scene}: {data['count']} ({data['percentage']:.1f}%)\n")
                
                f.write("\n")
                
                # Panel details
                f.write("Panel Details:\n")
                for i, panel in enumerate(pipeline_result['panel_specs'], 1):
                    f.write(f"\n{i}. {panel['panel_id']}\n")
                    f.write(f"   Scene: {panel['scene_type']}\n")
                    f.write(f"   Shape: {panel['shape_type']} ({panel['angle_type']})\n")
                    f.write(f"   Aspect: {panel['aspect_ratio']:.2f}\n")
                    f.write(f"   Area: {panel['area_ratio']:.1%}\n")
            
            print(f"✓ Exported to {output_path}")
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_pipeline_summary(self) -> Dict:
        """
        Tổng hợp summary của toàn bộ pipeline runs
        
        Returns:
            Dict với statistics across all runs
        """
        if not self.pipeline_history:
            return {'error': 'No pipeline runs yet'}
        
        total_images = sum(r['statistics']['total_images'] for r in self.pipeline_history)
        total_panels = sum(r['statistics']['total_panels'] for r in self.pipeline_history)
        
        # Aggregate scene types across all runs
        from collections import Counter
        all_scenes = []
        for run in self.pipeline_history:
            for scene in run['scene_classifications']:
                all_scenes.append(scene['scene_type'])
        
        scene_counts = Counter(all_scenes)
        
        summary = {
            'total_runs': len(self.pipeline_history),
            'total_images_processed': total_images,
            'total_panels_generated': total_panels,
            'overall_scene_distribution': dict(scene_counts),
            'avg_panels_per_image': total_panels / total_images if total_images > 0 else 0
        }
        
        return summary


def test_pipeline():
    """Test function for ComicLayoutPipeline"""
    print("=" * 80)
    print("COMIC LAYOUT PIPELINE TEST")
    print("=" * 80)
    
    # Find test images
    test_dirs = ['images', 'uploads', 'outputs']
    test_images = []
    
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            files = [os.path.join(dir_name, f) for f in os.listdir(dir_name) 
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            test_images.extend(files[:5])  # Max 5 images per directory
            
            if len(test_images) >= 5:
                break
    
    if not test_images:
        print("\n❌ No test images found in images/, uploads/, or outputs/")
        print("Creating mock test...")
        
        # Create mock result
        print("\n" + "=" * 80)
        print("MOCK PIPELINE TEST")
        print("=" * 80)
        
        mock_analyses = [
            {
                'image_id': 'test001.jpg',
                'width': 800, 'height': 600,
                'character_count': 2,
                'character_area_ratio': 0.45,
                'motion_score': 0.65,
                'text_density': 0.35,
                'emotion_score': 0.55,
                'shot_type': 'medium'
            },
            {
                'image_id': 'test002.jpg',
                'width': 1000, 'height': 700,
                'character_count': 4,
                'character_area_ratio': 0.55,
                'motion_score': 0.75,
                'text_density': 0.45,
                'emotion_score': 0.70,
                'shot_type': 'wide'
            }
        ]
        
        classifier = SceneClassifier()
        scene_results = classifier.classify_batch(mock_analyses)
        
        generator = PanelGenerator()
        panel_specs = generator.generate_panels_batch(scene_results)
        
        print("\nMock Scene Classifications:")
        for scene in scene_results:
            print(f"  {scene['image_id']}: {scene['scene_type']}")
        
        print("\nMock Panel Specs:")
        for panel in panel_specs:
            print(f"  {panel['panel_id']}: {panel['scene_type']} → "
                  f"{panel['shape_type']} {panel['aspect_ratio']:.2f}")
        
        evaluator = LayoutEvaluator()
        
        # Create mock panels for evaluation
        mock_panels = [
            Panel(0, 0, 50, 60, area_ratio=0.35, angle_type='90', scene_type='group'),
            Panel(50, 0, 50, 30, area_ratio=0.18, angle_type='90', scene_type='dialogue'),
            Panel(50, 30, 50, 30, area_ratio=0.18, angle_type='90', scene_type='close_up'),
            Panel(0, 60, 50, 40, area_ratio=0.15, angle_type='<90', scene_type='action'),
            Panel(50, 60, 50, 40, area_ratio=0.14, angle_type='90', scene_type='normal')
        ]
        
        evaluation = evaluator.evaluate_page(mock_panels)
        report = evaluator.export_report(evaluation, format='text')
        print("\n" + report)
        
        print("\n" + "=" * 80)
        print("MOCK TEST COMPLETED ✓")
        print("=" * 80)
        return
    
    # Real test with images
    print(f"\nFound {len(test_images)} test images")
    print("Test images:")
    for img in test_images:
        print(f"  - {img}")
    
    # Create pipeline
    pipeline = ComicLayoutPipeline(use_yolo=False, use_easyocr=False, seed=42)
    
    try:
        # Process images
        result = pipeline.process_images(test_images, verbose=True)
        
        # Evaluate layout
        print("\n" + "=" * 80)
        print("LAYOUT EVALUATION")
        print("=" * 80)
        
        evaluation = pipeline.evaluate_layout(result['panel_specs'], verbose=True)
        
        # Export results
        output_dir = 'outputs'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        pipeline.export_results(result, os.path.join(output_dir, 'pipeline_result.json'), format='json')
        pipeline.export_results(result, os.path.join(output_dir, 'pipeline_result.txt'), format='txt')
        
        # Summary
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        
        summary = pipeline.get_pipeline_summary()
        print(f"\nTotal runs: {summary['total_runs']}")
        print(f"Total images processed: {summary['total_images_processed']}")
        print(f"Total panels generated: {summary['total_panels_generated']}")
        print(f"Avg panels per image: {summary['avg_panels_per_image']:.2f}")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_pipeline()
