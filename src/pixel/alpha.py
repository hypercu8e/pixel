from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from pixel.colors import RgbaColor


def estimate_background_color(
    rgba: NDArray[np.uint8],
    *,
    border_width: int = 1,
) -> RgbaColor:
    """Estimate a flat-ish background color from opaque image border pixels."""

    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("rgba must have shape H x W x 4")
    if border_width <= 0:
        raise ValueError("border_width must be positive")

    height, width = rgba.shape[:2]
    if height == 0 or width == 0:
        raise ValueError("cannot estimate background from empty image")

    border = min(border_width, height, width)
    samples = [
        rgba[:border, :, :],
        rgba[-border:, :, :],
        rgba[:, :border, :],
        rgba[:, -border:, :],
    ]
    border_pixels = np.concatenate([sample.reshape(-1, 4) for sample in samples], axis=0)
    opaque = border_pixels[border_pixels[:, 3] > 0]
    if opaque.size == 0:
        raise ValueError("cannot estimate background from fully transparent border")

    median_rgb = np.median(opaque[:, :3].astype(np.float32), axis=0)
    rgb = tuple(int(round(channel)) for channel in median_rgb)
    return (rgb[0], rgb[1], rgb[2], 255)


def resolve_alpha(
    rgba: NDArray[np.uint8],
    *,
    alpha_threshold: int | None = None,
    transparent_color: RgbaColor | None = None,
    transparent_tolerance: int = 0,
) -> NDArray[np.uint8]:
    """Return RGBA pixels with explicit transparent pixels normalized to alpha 0."""

    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("rgba must have shape H x W x 4")
    if not 0 <= transparent_tolerance <= 255:
        raise ValueError("transparent_tolerance must be between 0 and 255")

    resolved = rgba.copy()
    mask = np.zeros(rgba.shape[:2], dtype=bool)

    if alpha_threshold is not None:
        if not 0 <= alpha_threshold <= 255:
            raise ValueError("alpha_threshold must be between 0 and 255")
        mask |= resolved[:, :, 3] < alpha_threshold

    if transparent_color is not None:
        rgb = np.array(transparent_color[:3], dtype=np.int16)
        pixels = resolved[:, :, :3].astype(np.int16)
        delta = np.abs(pixels - rgb)
        mask |= np.all(delta <= transparent_tolerance, axis=2)

    resolved[mask, 3] = 0
    return resolved
