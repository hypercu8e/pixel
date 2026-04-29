from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.ai_gemini import plan_gemini_cleanup
from pixel.models import GridSpec, PaletteSpec, SpriteAsset, ValidationReport


class AiGeminiTests(unittest.TestCase):
    def test_plan_requires_api_key_before_optional_dependency(self) -> None:
        asset = SpriteAsset(
            grid=GridSpec(cell_width=1, cell_height=1, rows=1, cols=1),
            palette=PaletteSpec(colors=((0, 0, 0, 255),)),
            pixels=np.zeros((1, 1), dtype=np.uint8),
        )
        report = ValidationReport()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
                plan_gemini_cleanup(
                    "input.png",
                    asset,
                    report,
                    model="gemini-2.5-flash",
                )


if __name__ == "__main__":
    unittest.main()
