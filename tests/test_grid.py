from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.grid import derive_grid_spec


class GridTests(unittest.TestCase):
    def test_derives_rows_cols_and_warns_about_remainder(self) -> None:
        grid, warnings = derive_grid_spec(
            510,
            512,
            cell_width=8,
            cell_height=8,
        )

        self.assertEqual(grid.cols, 63)
        self.assertEqual(grid.rows, 64)
        self.assertEqual(len(warnings), 1)
        self.assertIn("right edge", warnings[0])

    def test_ignores_one_bottom_pixel_for_512_by_513(self) -> None:
        grid, warnings = derive_grid_spec(
            512,
            513,
            cell_width=8,
            cell_height=8,
        )

        self.assertEqual(grid.cols, 64)
        self.assertEqual(grid.rows, 64)
        self.assertEqual(len(warnings), 1)
        self.assertIn("bottom edge", warnings[0])

    def test_manual_rows_cols_must_fit_bounds(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds image bounds"):
            derive_grid_spec(
                32,
                32,
                cell_width=8,
                cell_height=8,
                rows=5,
                cols=4,
            )


if __name__ == "__main__":
    unittest.main()
