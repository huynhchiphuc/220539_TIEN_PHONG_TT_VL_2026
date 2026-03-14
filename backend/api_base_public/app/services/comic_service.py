import os
import shutil
from pathlib import Path
from datetime import datetime

try:
    from app.services.comic.comic_book_auto_fill import create_comic_book_from_images
    from app.services.comic.comic_layout_simple import process_comic_layout
    COMIC_ENGINE_AVAILABLE = True
except ImportError:
    COMIC_ENGINE_AVAILABLE = False

try:
    from app.db.db_manager import MySQLDatabase
    from app.db.mysql_connection import get_mysql_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class ComicService:
    @staticmethod
    def generate_comic_pipeline(
        input_folder: str,
        output_folder: str,
        file_json_data: dict,
        user_id: int = None,
        session_id: str = None
    ):
        """
        Core logic to generate comic book pages from input images.
        Moved from router to here to follow MVC/Service architecture.
        """
        if not COMIC_ENGINE_AVAILABLE:
            raise Exception('Comic engine not available')
            
        # 1. Clear physical output folder
        if os.path.exists(output_folder):
            try:
                shutil.rmtree(output_folder)
            except Exception as e:
                print(f'Cannot remove old output: {e}')
                for f in Path(output_folder).glob('*'):
                    try: f.unlink()
                    except: pass
        os.makedirs(output_folder, exist_ok=True)

        # 2. Extract configuration from file_json_data
        layout_mode = file_json_data.get('layout_mode', 'advanced')
        single_page_mode = file_json_data.get('single_page_mode', False)
        panels_per_page = file_json_data.get('panels_per_page', 5)
        
        generated_pages = []

        # 3. Generate Logic
        if layout_mode == 'simple':
            print(f'🎨 Using SIMPLE layout mode')
            resolution_map = {"1K": 1000, "2K": 2000, "4K": 4000}
            aspect_ratio_map = {
                "1:1": (1, 1), "2:3": (2, 3), "3:2": (3, 2),
                "3:4": (3, 4), "4:3": (4, 3), "4:5": (4, 5),
                "5:4": (5, 4), "9:16": (9, 16), "16:9": (16, 9), "21:9": (21, 9)
            }
            aspect_ratio_key = file_json_data.get('aspect_ratio', '16:9')
            if str(aspect_ratio_key).lower() == 'auto':
                aspect_ratio_key = '16:9' # fallback for service param
            
            base_resolution = resolution_map.get(file_json_data.get('resolution', '2K'), 2000)
            aspect_w, aspect_h = aspect_ratio_map.get(aspect_ratio_key, (16, 9))
            page_width = base_resolution

            if single_page_mode:
                page_height = base_resolution * 20
                img_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                simple_panels_per_page = len(img_files)
            else:
                page_height = int(base_resolution * aspect_h / aspect_w)
                simple_panels_per_page = panels_per_page if panels_per_page else 8

            base_output = os.path.join(output_folder, 'page')
            generated_pages = process_comic_layout(
                input_folder=input_folder,
                output_filename=base_output + '.jpg',
                page_width=page_width,
                margin=file_json_data.get('margin', 20),
                gap=file_json_data.get('gap', 10),
                page_height=page_height,
                panels_per_page=simple_panels_per_page,
                use_smart_crop=file_json_data.get('use_smart_crop', False),
                adaptive_layout=file_json_data.get('adaptive_layout', True),
                analyze_shot_type=file_json_data.get('analyze_shot_type', False),
                classify_characters=file_json_data.get('classify_characters', False),
                reading_direction=file_json_data.get('reading_direction', 'ltr')
            )
        else:
            print(f'🧠 Using ADVANCED layout mode')
            panels = panels_per_page
            if single_page_mode:
                img_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                panels = len(img_files)
                
            generated_pages = create_comic_book_from_images(
                image_folder=input_folder,
                output_folder=output_folder,
                panels_per_page=panels,
                diagonal_prob=file_json_data.get('diagonal_prob', 0.3),
                adaptive_layout=file_json_data.get('adaptive_layout', True),
                use_smart_crop=file_json_data.get('use_smart_crop', False),
                reading_direction=file_json_data.get('reading_direction', 'ltr'),
                analyze_shot_type=file_json_data.get('analyze_shot_type', False),
                auto_page_size=file_json_data.get('auto_page_size', True),
                target_dpi=file_json_data.get('target_dpi', 150),
                classify_characters=file_json_data.get('classify_characters', False)
            )

        pages = [str(Path(p)) for p in generated_pages]
        
        return {
            'success': True,
            'session_id': session_id,
            'pages': pages,
            'count': len(pages),
            'output_folder': output_folder,
            'message': 'Generated successfully pipeline'
        }