import unittest
import sys
import os

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.renderer.camera import Camera

class TestCamera(unittest.TestCase):
    def setUp(self):
        self.world_size = 5000.0
        self.win_w = 800
        self.win_h = 500
        self.camera = Camera(self.world_size, self.win_w, self.win_h)
        # Center camera
        self.camera.x = 2500.0
        self.camera.y = 2500.0
        self.camera.zoom = 2.5

    def test_visible_area_at_2_5x(self):
        # visible_h = 5000 / 2.5 = 2000
        # visible_w = (5000 * 0.75) / 2.5 = 1500
        w, h = self.camera.get_visible_area()
        self.assertEqual(h, 2000.0)
        self.assertEqual(w, 1500.0)

    def test_culling_bounds_at_2_5x_margin_250(self):
        # Margin 250.
        # min_x = 2500 - (1500/2) - 250 = 2500 - 750 - 250 = 1500
        # max_x = 2500 + (1500/2) + 250 = 2500 + 750 + 250 = 3500
        margin = 250.0
        bounds = self.camera.get_culling_bounds(margin)
        
        print(f"\nDEBUG TEST BOUNDS: {bounds}")
        
        self.assertEqual(bounds[0], 1500.0) # min_x
        self.assertEqual(bounds[2], 3500.0) # max_x
        self.assertEqual(bounds[1], 1250.0) # min_y (2500 - 1000 - 250)
        self.assertEqual(bounds[3], 3750.0) # max_y (2500 + 1000 + 250)
        
    def test_projection_logic(self):
        # Test if x=sim_max_x maps to normalized > 0.75
        margin = 250.0
        bounds = self.camera.get_culling_bounds(margin)
        max_x = bounds[2] # 3500
        
        # Projection logic from main.py / shader
        # rel_x = (pos - cx) * z
        # norm = rel_x / W + 0.375
        
        cx = self.camera.x
        z = self.camera.zoom
        W = self.world_size
        
        rel_x = (max_x - cx) * z # (3500 - 2500) * 2.5 = 1000 * 2.5 = 2500
        norm = rel_x / W + 0.375 # 2500/5000 + 0.375 = 0.5 + 0.375 = 0.875
        
        print(f"\nDEBUG PROJECTED MAX_X: {norm}")
        self.assertTrue(norm > 0.75)

if __name__ == '__main__':
    unittest.main()
