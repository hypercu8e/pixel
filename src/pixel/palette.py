from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from pixel.colors import RgbaColor
from pixel.models import PaletteSpec


TRANSPARENT: RgbaColor = (0, 0, 0, 0)


def build_palette(
    rgba: NDArray[np.uint8],
    *,
    colors: int,
    explicit_palette: list[RgbaColor] | None = None,
) -> PaletteSpec:
    if colors <= 0 or colors > 256:
        raise ValueError("colors must be between 1 and 256")

    has_transparency = bool(np.any(rgba[:, :, 3] == 0))
    if explicit_palette is not None:
        return _explicit_palette(explicit_palette, has_transparency)

    visible = rgba[rgba[:, :, 3] > 0][:, :3]
    palette_colors: list[RgbaColor] = []
    transparent_index = None

    if has_transparency:
        palette_colors.append(TRANSPARENT)
        transparent_index = 0

    visible_slots = colors - len(palette_colors)
    if visible_slots <= 0:
        return PaletteSpec(tuple(palette_colors), transparent_index=transparent_index)
    if visible.size == 0:
        return PaletteSpec(tuple(palette_colors or [TRANSPARENT]), transparent_index=0)

    selected = _quantize_visible_colors(visible, visible_slots)
    for rgb in selected:
        palette_colors.append((int(rgb[0]), int(rgb[1]), int(rgb[2]), 255))

    return PaletteSpec(tuple(palette_colors), transparent_index=transparent_index)


def snap_to_palette(
    rgba: NDArray[np.uint8],
    palette: PaletteSpec,
) -> NDArray[np.uint8]:
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("rgba must have shape H x W x 4")

    indexed = np.zeros(rgba.shape[:2], dtype=np.uint8)
    visible_mask = rgba[:, :, 3] > 0

    if palette.transparent_index is not None:
        indexed[~visible_mask] = palette.transparent_index

    visible_palette_indices = [
        index for index, color in enumerate(palette.colors) if color[3] > 0
    ]
    if np.any(visible_mask) and not visible_palette_indices:
        raise ValueError("palette has no visible colors")

    if np.any(visible_mask):
        palette_rgb = np.array(
            [palette.colors[index][:3] for index in visible_palette_indices],
            dtype=np.int32,
        )
        pixels = rgba[:, :, :3].astype(np.int32)
        distances = np.sum((pixels[:, :, None, :] - palette_rgb[None, None, :, :]) ** 2, axis=3)
        nearest = np.argmin(distances, axis=2)
        index_lookup = np.array(visible_palette_indices, dtype=np.uint8)
        indexed[visible_mask] = index_lookup[nearest[visible_mask]]

    return indexed


def _explicit_palette(
    colors: list[RgbaColor],
    has_transparency: bool,
) -> PaletteSpec:
    if not colors:
        raise ValueError("explicit palette cannot be empty")

    palette = list(colors)
    transparent_index = next(
        (index for index, color in enumerate(palette) if color[3] == 0),
        None,
    )

    if has_transparency and transparent_index is None:
        palette.insert(0, TRANSPARENT)
        transparent_index = 0

    return PaletteSpec(tuple(palette), transparent_index=transparent_index)


def _quantize_visible_colors(
    visible_rgb: NDArray[np.uint8],
    max_colors: int,
) -> NDArray[np.uint8]:
    if max_colors <= 0:
        return np.empty((0, 3), dtype=np.uint8)

    unique, counts = np.unique(visible_rgb, axis=0, return_counts=True)
    if len(unique) <= max_colors:
        order = _frequency_order(unique, counts)
        return unique[order]

    # Pillow's adaptive palette gives a real quantization step without adding a
    # dependency. Dithering stays off so the palette solver does not inject noise.
    strip = Image.fromarray(visible_rgb.reshape(1, -1, 3), mode="RGB")
    quantized = strip.quantize(
        colors=max_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    quantized_rgb = np.asarray(quantized.convert("RGB"), dtype=np.uint8).reshape(-1, 3)
    palette_unique, palette_counts = np.unique(
        quantized_rgb,
        axis=0,
        return_counts=True,
    )
    order = _frequency_order(palette_unique, palette_counts)
    return palette_unique[order[:max_colors]]


def _frequency_order(colors: NDArray[np.uint8], counts: NDArray[np.integer]) -> NDArray[np.int64]:
    return np.lexsort((colors[:, 2], colors[:, 1], colors[:, 0], -counts))
