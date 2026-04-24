from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.alpha import estimate_background_color, resolve_alpha
from pixel.colors import parse_hex_color
from pixel.palette import build_palette, snap_to_palette


class AlphaPaletteTests(unittest.TestCase):
    def test_transparent_color_sets_alpha_zero(self) -> None:
        rgba = np.array(
            [
                [[255, 0, 255, 255], [10, 20, 30, 255]],
            ],
            dtype=np.uint8,
        )

        resolved = resolve_alpha(rgba, transparent_color=(255, 0, 255, 255))

        self.assertEqual(int(resolved[0, 0, 3]), 0)
        self.assertEqual(int(resolved[0, 1, 3]), 255)

    def test_transparent_color_tolerance_catches_near_background(self) -> None:
        rgba = np.array(
            [
                [[252, 2, 253, 255], [240, 0, 240, 255]],
            ],
            dtype=np.uint8,
        )

        resolved = resolve_alpha(
            rgba,
            transparent_color=(255, 0, 255, 255),
            transparent_tolerance=5,
        )

        self.assertEqual(int(resolved[0, 0, 3]), 0)
        self.assertEqual(int(resolved[0, 1, 3]), 255)

    def test_estimate_background_color_uses_opaque_border_median(self) -> None:
        rgba = np.array(
            [
                [[10, 20, 30, 255], [12, 20, 31, 255], [10, 19, 30, 255]],
                [[11, 20, 30, 255], [250, 0, 0, 255], [10, 21, 30, 255]],
                [[10, 20, 29, 255], [12, 19, 31, 255], [10, 20, 30, 255]],
            ],
            dtype=np.uint8,
        )

        background = estimate_background_color(rgba)

        self.assertEqual(background, (10, 20, 30, 255))

    def test_explicit_palette_snap_preserves_transparency_index(self) -> None:
        rgba = np.array(
            [
                [[0, 0, 0, 0], [250, 0, 0, 255], [0, 10, 240, 255]],
            ],
            dtype=np.uint8,
        )
        palette = build_palette(
            rgba,
            colors=3,
            explicit_palette=[
                parse_hex_color("#00000000"),
                parse_hex_color("#ff0000"),
                parse_hex_color("#0000ff"),
            ],
        )

        indexed = snap_to_palette(rgba, palette)

        np.testing.assert_array_equal(indexed, np.array([[0, 1, 2]], dtype=np.uint8))

    def test_auto_palette_quantizes_clusters_instead_of_top_unique_only(self) -> None:
        reds = np.array(
            [[[240 + offset, 0, 0, 255] for offset in range(8)]],
            dtype=np.uint8,
        )
        blues = np.array(
            [[[0, 0, 240 + offset, 255] for offset in range(8)]],
            dtype=np.uint8,
        )
        rgba = np.concatenate([reds, blues], axis=1)

        palette = build_palette(rgba, colors=2)
        indexed = snap_to_palette(rgba, palette)

        self.assertEqual(len(palette.colors), 2)
        self.assertEqual(len(set(int(value) for value in indexed.ravel())), 2)


if __name__ == "__main__":
    unittest.main()
