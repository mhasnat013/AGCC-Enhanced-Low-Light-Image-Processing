"""Automated checks for the reusable AGCC core functions."""

import importlib.util
from pathlib import Path
import unittest
import warnings

import numpy as np


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "Code" / "AGCC Core Implementation.py"
)
SPEC = importlib.util.spec_from_file_location("agcc_core", MODULE_PATH)
agcc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agcc)


class TestAGCCCore(unittest.TestCase):
    def setUp(self):
        gradient = np.linspace(0.02, 0.35, 64, dtype=np.float32)
        gray = np.tile(gradient, (64, 1))
        self.low_light_rgb = np.stack(
            (gray * 0.9, gray, gray * 1.1),
            axis=2,
        )

    def test_to_float_rgb_normalizes_uint8(self):
        image = np.full((8, 8, 3), 128, dtype=np.uint8)
        output = agcc.to_float_rgb(image)

        self.assertEqual(output.dtype, np.float32)
        self.assertTrue(np.all(output >= 0.0))
        self.assertTrue(np.all(output <= 1.0))

    def test_adaptive_gamma_is_positive(self):
        gamma = agcc.adaptive_gamma_value(self.low_light_rgb)
        self.assertGreaterEqual(gamma, 0.1)

    def test_original_agcc_preserves_shape_and_range(self):
        result = agcc.original_agcc(self.low_light_rgb)

        self.assertEqual(result["final"].shape, self.low_light_rgb.shape)
        self.assertTrue(np.all(result["final"] >= 0.0))
        self.assertTrue(np.all(result["final"] <= 1.0))
        self.assertGreaterEqual(result["runtime"], 0.0)

    def test_hybrid_agcc_preserves_shape_and_range(self):
        result = agcc.improved_hybrid_agcc(self.low_light_rgb)

        self.assertEqual(result["final"].shape, self.low_light_rgb.shape)
        self.assertTrue(np.all(result["final"] >= 0.0))
        self.assertTrue(np.all(result["final"] <= 1.0))

    def test_identical_images_have_perfect_ssim(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            metrics = agcc.evaluate_with_reference(
                self.low_light_rgb,
                self.low_light_rgb,
            )

        self.assertAlmostEqual(metrics["ssim"], 1.0, places=6)
        self.assertTrue(np.isinf(metrics["psnr"]))


if __name__ == "__main__":
    unittest.main()
