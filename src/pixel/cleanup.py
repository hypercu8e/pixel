from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def cleanup_indexed(
    indexed: NDArray[np.integer],
    *,
    transparent_index: int | None = None,
    remove_isolated: bool = False,
) -> NDArray[np.integer]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    cleaned = indexed.copy()
    if remove_isolated:
        cleaned = remove_isolated_pixels(
            cleaned,
            transparent_index=transparent_index,
        )
    return cleaned


def remove_isolated_pixels(
    indexed: NDArray[np.integer],
    *,
    transparent_index: int | None = None,
) -> NDArray[np.integer]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    height, width = indexed.shape
    cleaned = indexed.copy()

    for row in range(height):
        for col in range(width):
            value = int(indexed[row, col])
            if transparent_index is not None and value == transparent_index:
                continue

            replacement = _isolated_pixel_replacement(indexed, row, col)
            if replacement is not None:
                cleaned[row, col] = replacement

    return cleaned


def _isolated_pixel_replacement(
    indexed: NDArray[np.integer],
    row: int,
    col: int,
) -> int | None:
    height, width = indexed.shape
    value = int(indexed[row, col])
    counts: dict[int, int] = {}
    same_neighbor_count = 0
    neighbor_count = 0

    for neighbor_row in range(max(0, row - 1), min(height, row + 2)):
        for neighbor_col in range(max(0, col - 1), min(width, col + 2)):
            if neighbor_row == row and neighbor_col == col:
                continue
            neighbor_value = int(indexed[neighbor_row, neighbor_col])
            neighbor_count += 1
            if neighbor_value == value:
                same_neighbor_count += 1
            counts[neighbor_value] = counts.get(neighbor_value, 0) + 1

    if same_neighbor_count or not counts:
        return None

    top_count = max(counts.values())
    if list(counts.values()).count(top_count) != 1:
        return None

    majority_threshold = neighbor_count // 2 + 1
    if top_count < majority_threshold:
        return None

    for candidate, count in counts.items():
        if count == top_count:
            return candidate
    return None
