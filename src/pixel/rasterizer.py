from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from pixel.models import GridSpec


def rasterize_indexed(
    indexed: NDArray[np.integer],
    grid: GridSpec,
    *,
    palette_size: int | None = None,
) -> NDArray[np.uint8]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    y0 = grid.origin_y
    x0 = grid.origin_x
    y1 = y0 + grid.source_height
    x1 = x0 + grid.source_width
    if y1 > indexed.shape[0] or x1 > indexed.shape[1]:
        raise ValueError("grid exceeds indexed matrix bounds")

    cropped = indexed[y0:y1, x0:x1]
    blocks = cropped.reshape(
        grid.rows,
        grid.cell_height,
        grid.cols,
        grid.cell_width,
    ).transpose(0, 2, 1, 3)

    output = np.zeros((grid.rows, grid.cols), dtype=np.uint8)
    minlength = palette_size or int(indexed.max()) + 1
    for row in range(grid.rows):
        for col in range(grid.cols):
            output[row, col] = majority_index(blocks[row, col], minlength=minlength)
    return output


def majority_index(block: NDArray[np.integer], *, minlength: int) -> int:
    if block.size == 0:
        raise ValueError("cannot vote on empty block")
    counts = np.bincount(block.ravel().astype(np.int64), minlength=minlength)
    return int(np.argmax(counts))
