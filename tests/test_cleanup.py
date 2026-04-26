from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.cleanup import cleanup_indexed, remove_isolated_pixels


class CleanupTests(unittest.TestCase):
    def test_cleanup_preserves_pixels_by_default(self) -> None:
        indexed = np.array(
            [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 1],
            ],
            dtype=np.uint8,
        )

        cleaned = cleanup_indexed(indexed)

        np.testing.assert_array_equal(cleaned, indexed)
        self.assertIsNot(cleaned, indexed)

    def test_remove_isolated_replaces_with_clear_neighbor_majority(self) -> None:
        indexed = np.array(
            [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 1],
            ],
            dtype=np.uint8,
        )

        cleaned = cleanup_indexed(indexed, remove_isolated=True)

        np.testing.assert_array_equal(
            cleaned,
            np.array(
                [
                    [1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1],
                ],
                dtype=np.uint8,
            ),
        )

    def test_remove_isolated_leaves_ambiguous_neighbors_unchanged(self) -> None:
        indexed = np.array(
            [
                [1, 1, 3],
                [1, 2, 3],
                [4, 4, 3],
            ],
            dtype=np.uint8,
        )

        cleaned = remove_isolated_pixels(indexed)

        np.testing.assert_array_equal(cleaned, indexed)

    def test_remove_isolated_skips_transparent_source_pixels(self) -> None:
        indexed = np.array(
            [
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1],
            ],
            dtype=np.uint8,
        )

        cleaned = cleanup_indexed(
            indexed,
            transparent_index=0,
            remove_isolated=True,
        )

        np.testing.assert_array_equal(cleaned, indexed)


if __name__ == "__main__":
    unittest.main()
