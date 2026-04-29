from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.ai_cleanup import (
    AiCleanupAdvice,
    AiCleanupRegion,
    apply_ai_cleanup_advice,
    parse_ai_cleanup_advice,
)


class AiCleanupTests(unittest.TestCase):
    def test_parse_advice_keeps_valid_regions_and_records_invalid_ones(self) -> None:
        advice = parse_ai_cleanup_advice(
            """
            {
              "regions": [
                {
                  "x": 1,
                  "y": 2,
                  "width": 3,
                  "height": 4,
                  "issue": "background_noise",
                  "action": "remove_tiny_components",
                  "confidence": 0.8
                },
                {"x": "bad"}
              ]
            }
            """,
            model="gemini-2.5-flash",
        )

        self.assertEqual(len(advice.regions), 1)
        self.assertEqual(advice.regions[0].action, "remove_tiny_components")
        self.assertEqual(len(advice.ignored_regions), 1)

    def test_parse_advice_rejects_non_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_ai_cleanup_advice("not json", model="gemini-2.5-flash")

    def test_apply_advice_clips_region_and_ignores_unknown_action(self) -> None:
        indexed = np.array(
            [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 1],
            ],
            dtype=np.uint8,
        )
        advice = AiCleanupAdvice(
            model="gemini-2.5-flash",
            regions=(
                AiCleanupRegion(
                    x=-1,
                    y=-1,
                    width=3,
                    height=3,
                    issue="noise",
                    action="remove_isolated_pixels",
                    confidence=0.9,
                ),
                AiCleanupRegion(
                    x=0,
                    y=0,
                    width=1,
                    height=1,
                    issue="noise",
                    action="redraw",
                    confidence=0.9,
                ),
            ),
        )

        result = apply_ai_cleanup_advice(indexed, advice)

        np.testing.assert_array_equal(
            result.pixels,
            np.array(
                [
                    [1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1],
                ],
                dtype=np.uint8,
            ),
        )
        self.assertEqual(len(result.accepted_regions), 1)
        self.assertEqual(len(result.ignored_regions), 1)
        self.assertIn("ignored 1 AI cleanup region", result.warnings[0])


if __name__ == "__main__":
    unittest.main()
