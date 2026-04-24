from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from pixel.models import PaletteSpec, SpriteAsset


def indexed_to_rgba(
    indexed: NDArray[np.integer],
    palette: PaletteSpec,
) -> NDArray[np.uint8]:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    colors = np.array(palette.colors, dtype=np.uint8)
    if indexed.size and int(indexed.max()) >= len(colors):
        raise ValueError("indexed matrix contains palette index outside palette")
    return colors[indexed.astype(np.int64)]


def save_png(path: str | Path, asset: SpriteAsset) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgba = indexed_to_rgba(asset.pixels, asset.palette)
    image = Image.fromarray(rgba, mode="RGBA")
    image.save(output_path)
