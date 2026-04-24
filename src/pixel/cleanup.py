from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def cleanup_indexed(indexed: NDArray[np.integer]) -> NDArray[np.integer]:
    """Conservative MVP cleanup: preserve pixels and return an owned array."""

    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")
    return indexed.copy()
