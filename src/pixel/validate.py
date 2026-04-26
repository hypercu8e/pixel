from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from pixel.models import SpriteAsset, ValidationReport


def validate_asset(
    asset: SpriteAsset,
    *,
    source_width: int,
    source_height: int,
    warnings: list[str] | None = None,
) -> ValidationReport:
    report_warnings = list(warnings or [])
    errors: list[str] = []
    pixels = asset.pixels
    palette_size = len(asset.palette.colors)

    if pixels.size and int(pixels.max()) >= palette_size:
        errors.append("pixel matrix contains index outside palette")

    isolated = count_isolated_pixels(
        pixels,
        transparent_index=asset.palette.transparent_index,
    )
    if isolated:
        report_warnings.append(
            f"found {isolated} isolated visible pixel(s) in final output"
        )

    used = sorted(int(value) for value in np.unique(pixels))
    transparent_pixels = 0
    if asset.palette.transparent_index is not None:
        transparent_pixels = int(np.sum(pixels == asset.palette.transparent_index))

    metrics: dict[str, Any] = {
        "source_width": source_width,
        "source_height": source_height,
        "rows": asset.grid.rows,
        "cols": asset.grid.cols,
        "palette_colors": palette_size,
        "used_palette_indices": used,
        "used_color_count": len(used),
        "transparent_pixels": transparent_pixels,
        "isolated_visible_pixels": isolated,
    }

    return ValidationReport(metrics=metrics, warnings=report_warnings, errors=errors)


def count_isolated_pixels(
    indexed: NDArray[np.integer],
    *,
    transparent_index: int | None = None,
) -> int:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    height, width = indexed.shape
    count = 0
    for row in range(height):
        for col in range(width):
            value = int(indexed[row, col])
            if transparent_index is not None and value == transparent_index:
                continue
            row0 = max(0, row - 1)
            row1 = min(height, row + 2)
            col0 = max(0, col - 1)
            col1 = min(width, col + 2)
            neighborhood = indexed[row0:row1, col0:col1]
            same = np.sum(neighborhood == value)
            if same == 1:
                count += 1
    return count
