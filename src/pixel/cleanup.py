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


def remove_isolated_pixels_in_region(
    indexed: NDArray[np.integer],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    transparent_index: int | None = None,
) -> NDArray[np.integer]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")
    _validate_region(indexed, x=x, y=y, width=width, height=height)

    cleaned = indexed.copy()
    for row in range(y, y + height):
        for col in range(x, x + width):
            value = int(indexed[row, col])
            if transparent_index is not None and value == transparent_index:
                continue

            replacement = _isolated_pixel_replacement(indexed, row, col)
            if replacement is not None:
                cleaned[row, col] = replacement
    return cleaned


def remove_tiny_components_in_region(
    indexed: NDArray[np.integer],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    transparent_index: int | None = None,
    max_size: int = 3,
) -> NDArray[np.integer]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    _validate_region(indexed, x=x, y=y, width=width, height=height)

    cleaned = indexed.copy()
    visited = np.zeros(indexed.shape, dtype=bool)
    for row in range(y, y + height):
        for col in range(x, x + width):
            if visited[row, col]:
                continue
            value = int(indexed[row, col])
            if transparent_index is not None and value == transparent_index:
                visited[row, col] = True
                continue

            component = _component_from(indexed, row, col, x=x, y=y, width=width, height=height)
            for component_row, component_col in component:
                visited[component_row, component_col] = True

            if len(component) > max_size:
                continue
            replacement = _component_replacement(indexed, component, value)
            if replacement is None:
                continue
            for component_row, component_col in component:
                cleaned[component_row, component_col] = replacement
    return cleaned


def _validate_region(
    indexed: NDArray[np.integer],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("region width and height must be positive")
    if x < 0 or y < 0:
        raise ValueError("region origin must be non-negative")
    if y + height > indexed.shape[0] or x + width > indexed.shape[1]:
        raise ValueError("region exceeds indexed matrix bounds")


def _component_from(
    indexed: NDArray[np.integer],
    row: int,
    col: int,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    value = int(indexed[row, col])
    row_min = y
    row_max = y + height
    col_min = x
    col_max = x + width
    component: list[tuple[int, int]] = []
    stack = [(row, col)]
    seen = set(stack)

    while stack:
        current_row, current_col = stack.pop()
        component.append((current_row, current_col))
        for next_row, next_col in (
            (current_row - 1, current_col),
            (current_row + 1, current_col),
            (current_row, current_col - 1),
            (current_row, current_col + 1),
        ):
            if not (row_min <= next_row < row_max and col_min <= next_col < col_max):
                continue
            if (next_row, next_col) in seen:
                continue
            if int(indexed[next_row, next_col]) != value:
                continue
            seen.add((next_row, next_col))
            stack.append((next_row, next_col))

    return component


def _component_replacement(
    indexed: NDArray[np.integer],
    component: list[tuple[int, int]],
    component_value: int,
) -> int | None:
    component_cells = set(component)
    counts: dict[int, int] = {}
    height, width = indexed.shape

    for row, col in component:
        for neighbor_row in range(max(0, row - 1), min(height, row + 2)):
            for neighbor_col in range(max(0, col - 1), min(width, col + 2)):
                if (neighbor_row, neighbor_col) in component_cells:
                    continue
                neighbor_value = int(indexed[neighbor_row, neighbor_col])
                if neighbor_value == component_value:
                    return None
                counts[neighbor_value] = counts.get(neighbor_value, 0) + 1

    if not counts:
        return None

    top_count = max(counts.values())
    if list(counts.values()).count(top_count) != 1:
        return None
    if top_count < max(2, len(component)):
        return None

    for candidate, count in counts.items():
        if count == top_count:
            return candidate
    return None


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
