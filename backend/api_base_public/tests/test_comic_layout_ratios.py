import random
import unittest

from app.services.comic.comic_book_auto_fill import create_dynamic_grid_layout


class ComicLayoutRatioTests(unittest.TestCase):
    def _panel_aspect(self, panel):
        _, _, w, h = panel.get_bounds()
        return (w / h) if h else 0

    def test_dynamic_grid_avoids_ultra_thin_panels_for_three_portrait_images(self):
        random.seed(123)
        image_aspects = [
            {"aspect": 0.7, "orientation": "portrait"},
            {"aspect": 0.65, "orientation": "portrait"},
            {"aspect": 0.75, "orientation": "portrait"},
        ]

        panels = create_dynamic_grid_layout(image_aspects, width=100, height=160, jitter_factor=8.0, margin=4)

        self.assertEqual(len(panels), 3)
        min_aspect = min(self._panel_aspect(panel) for panel in panels)
        self.assertGreaterEqual(min_aspect, 0.55)

    def test_dynamic_grid_balances_five_portrait_images(self):
        random.seed(456)
        image_aspects = [
            {"aspect": 0.7, "orientation": "portrait"},
            {"aspect": 0.65, "orientation": "portrait"},
            {"aspect": 0.8, "orientation": "portrait"},
            {"aspect": 0.75, "orientation": "portrait"},
            {"aspect": 0.68, "orientation": "portrait"},
        ]

        panels = create_dynamic_grid_layout(image_aspects, width=100, height=160, jitter_factor=8.0, margin=4)

        self.assertEqual(len(panels), 5)
        min_aspect = min(self._panel_aspect(panel) for panel in panels)
        self.assertGreaterEqual(min_aspect, 0.5)


if __name__ == "__main__":
    unittest.main()
