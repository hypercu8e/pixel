from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image


def load_rgba(path: str | Path) -> NDArray[np.uint8]:
    image = Image.open(path).convert("RGBA")
    return np.asarray(image, dtype=np.uint8).copy()
