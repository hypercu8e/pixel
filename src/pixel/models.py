from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from pixel.colors import RgbaColor, rgba_to_hex


@dataclass(frozen=True)
class GridSpec:
    cell_width: int
    cell_height: int
    rows: int
    cols: int
    origin_x: int = 0
    origin_y: int = 0

    def __post_init__(self) -> None:
        if self.cell_width <= 0 or self.cell_height <= 0:
            raise ValueError("cell size must be positive")
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("rows and cols must be positive")
        if self.origin_x < 0 or self.origin_y < 0:
            raise ValueError("origin must be non-negative")

    @property
    def source_width(self) -> int:
        return self.cols * self.cell_width

    @property
    def source_height(self) -> int:
        return self.rows * self.cell_height

    def to_dict(self) -> dict[str, int]:
        return {
            "cell_width": self.cell_width,
            "cell_height": self.cell_height,
            "rows": self.rows,
            "cols": self.cols,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y,
        }


@dataclass(frozen=True)
class PaletteSpec:
    colors: tuple[RgbaColor, ...]
    transparent_index: int | None = None

    def __post_init__(self) -> None:
        if not self.colors:
            raise ValueError("palette must contain at least one color")
        if len(self.colors) > 256:
            raise ValueError("palette cannot contain more than 256 colors")
        for color in self.colors:
            if len(color) != 4 or any(channel < 0 or channel > 255 for channel in color):
                raise ValueError("palette colors must be RGBA values in 0..255")
        if self.transparent_index is not None:
            if not 0 <= self.transparent_index < len(self.colors):
                raise ValueError("transparent index outside palette")

    def to_dict(self) -> dict[str, Any]:
        return {
            "colors": [rgba_to_hex(color) for color in self.colors],
            "transparent_index": self.transparent_index,
        }


@dataclass
class SpriteAsset:
    grid: GridSpec
    palette: PaletteSpec
    pixels: NDArray[np.integer]
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pixels.ndim != 2:
            raise ValueError("pixels must have shape H x W")
        if self.pixels.shape != (self.grid.rows, self.grid.cols):
            raise ValueError("pixel matrix shape must match grid rows and cols")


@dataclass(frozen=True)
class ValidationReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "metrics": self.metrics,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class CleanOptions:
    cell_width: int | None = None
    cell_height: int | None = None
    rows: int | None = None
    cols: int | None = None
    origin_x: int = 0
    origin_y: int = 0
    auto_grid: bool = False
    colors: int = 16
    palette: list[RgbaColor] | None = None
    auto_background: bool = False
    transparent_color: RgbaColor | None = None
    transparent_tolerance: int = 0
    alpha_threshold: int | None = 1


@dataclass(frozen=True)
class CleanResult:
    asset: SpriteAsset
    report: ValidationReport
