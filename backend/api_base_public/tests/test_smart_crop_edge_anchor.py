import unittest

from app.services.ai.smart_crop import _compute_edge_aware_crop_box


class SmartCropEdgeAnchorTests(unittest.TestCase):
    def test_left_edge_dialogue_stays_inside_crop(self):
        crop = _compute_edge_aware_crop_box(
            img_w=1000,
            img_h=1200,
            panel_aspect=1.4,
            critical_box=(20, 180, 320, 420),
        )
        x1, y1, x2, y2 = crop
        self.assertLessEqual(x1, 20)
        self.assertGreaterEqual(x2, 320)
        self.assertGreaterEqual(y2, 420)

    def test_right_edge_dialogue_stays_inside_crop(self):
        crop = _compute_edge_aware_crop_box(
            img_w=1000,
            img_h=1200,
            panel_aspect=1.4,
            critical_box=(700, 200, 980, 430),
        )
        x1, y1, x2, y2 = crop
        self.assertLessEqual(x1, 700)
        self.assertGreaterEqual(x2, 980)
        self.assertGreaterEqual(y2, 430)

    def test_top_dialogue_biases_crop_upward(self):
        crop = _compute_edge_aware_crop_box(
            img_w=1000,
            img_h=1400,
            panel_aspect=1.2,
            critical_box=(300, 30, 720, 220),
        )
        x1, y1, x2, y2 = crop
        self.assertLessEqual(y1, 30)
        self.assertGreaterEqual(y2, 220)


if __name__ == "__main__":
    unittest.main()
