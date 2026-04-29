from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixel.cli import main


class CliTests(unittest.TestCase):
    def test_ai_advice_report_requires_ai_cleanup(self) -> None:
        with patch("sys.stderr"):
            result = main(
                [
                    "clean",
                    "input.png",
                    "output.png",
                    "--cell-width",
                    "1",
                    "--ai-advice-report",
                    "advice.json",
                ]
            )

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
