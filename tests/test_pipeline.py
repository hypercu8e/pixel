from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.models import CleanOptions
from pixel.pipeline import clean_image


class PipelineTests(unittest.TestCase):
    def test_clean_image_writes_png_and_report(self) -> None:
        rgba = np.array(
            [
                [[255, 0, 0, 255], [250, 0, 0, 255], [0, 0, 255, 255], [0, 0, 250, 255]],
                [[255, 0, 0, 255], [255, 0, 0, 255], [0, 0, 255, 255], [0, 0, 255, 255]],
                [[0, 255, 0, 255], [0, 250, 0, 255], [0, 0, 0, 0], [0, 0, 0, 0]],
                [[0, 255, 0, 255], [0, 255, 0, 255], [0, 0, 0, 0], [0, 0, 0, 0]],
            ],
            dtype=np.uint8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.png"
            output_path = Path(tmp) / "output.png"
            Image.fromarray(rgba, mode="RGBA").save(input_path)

            result = clean_image(
                input_path,
                output_path,
                CleanOptions(cell_width=2, cell_height=2, colors=4),
            )

            self.assertTrue(output_path.exists())
            self.assertTrue(result.report.ok)
            self.assertEqual(result.asset.pixels.shape, (2, 2))

    def test_auto_background_makes_estimated_border_color_transparent(self) -> None:
        rgba = np.array(
            [
                [[11, 20, 30, 255], [10, 21, 30, 255], [11, 20, 31, 255]],
                [[10, 20, 30, 255], [240, 0, 0, 255], [12, 20, 30, 255]],
                [[11, 19, 30, 255], [10, 20, 31, 255], [11, 20, 30, 255]],
            ],
            dtype=np.uint8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.png"
            output_path = Path(tmp) / "output.png"
            Image.fromarray(rgba, mode="RGBA").save(input_path)

            result = clean_image(
                input_path,
                output_path,
                CleanOptions(
                    cell_width=1,
                    cell_height=1,
                    colors=2,
                    auto_background=True,
                    transparent_tolerance=2,
                ),
            )

            self.assertTrue(result.report.ok)
            self.assertEqual(result.report.metrics["transparent_pixels"], 8)
            self.assertIn("auto-background estimated", result.report.warnings[0])


if __name__ == "__main__":
    unittest.main()
