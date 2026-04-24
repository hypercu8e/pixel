from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.models import GridSpec
from pixel.rasterizer import majority_index, rasterize_indexed


class RasterizerTests(unittest.TestCase):
    def test_majority_voting_rasterizes_blocks(self) -> None:
        indexed = np.array(
            [
                [1, 1, 2, 2],
                [1, 3, 2, 0],
                [4, 4, 5, 5],
                [4, 0, 5, 5],
            ],
            dtype=np.uint8,
        )
        grid = GridSpec(cell_width=2, cell_height=2, rows=2, cols=2)

        output = rasterize_indexed(indexed, grid, palette_size=6)

        np.testing.assert_array_equal(
            output,
            np.array(
                [
                    [1, 2],
                    [4, 5],
                ],
                dtype=np.uint8,
            ),
        )

    def test_majority_tie_chooses_lowest_index(self) -> None:
        block = np.array([[2, 3], [3, 2]], dtype=np.uint8)

        self.assertEqual(majority_index(block, minlength=4), 2)


if __name__ == "__main__":
    unittest.main()
