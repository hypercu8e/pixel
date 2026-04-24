from __future__ import annotations

from pixel.models import GridSpec


def derive_grid_spec(
    image_width: int,
    image_height: int,
    *,
    cell_width: int,
    cell_height: int | None = None,
    rows: int | None = None,
    cols: int | None = None,
    origin_x: int = 0,
    origin_y: int = 0,
) -> tuple[GridSpec, list[str]]:
    if cell_height is None:
        cell_height = cell_width
    if cell_width <= 0 or cell_height <= 0:
        raise ValueError("cell width and height must be positive")
    if origin_x < 0 or origin_y < 0:
        raise ValueError("grid origin must be non-negative")
    if origin_x >= image_width or origin_y >= image_height:
        raise ValueError("grid origin must be inside the image")

    available_width = image_width - origin_x
    available_height = image_height - origin_y
    warnings: list[str] = []

    if cols is None:
        cols = available_width // cell_width
        unused_x = available_width % cell_width
        if unused_x:
            warnings.append(f"ignored {unused_x}px on the right edge outside the grid")
    if rows is None:
        rows = available_height // cell_height
        unused_y = available_height % cell_height
        if unused_y:
            warnings.append(f"ignored {unused_y}px on the bottom edge outside the grid")

    if rows <= 0 or cols <= 0:
        raise ValueError("derived grid has no cells")

    grid = GridSpec(
        cell_width=cell_width,
        cell_height=cell_height,
        rows=rows,
        cols=cols,
        origin_x=origin_x,
        origin_y=origin_y,
    )
    if origin_x + grid.source_width > image_width:
        raise ValueError("grid width exceeds image bounds")
    if origin_y + grid.source_height > image_height:
        raise ValueError("grid height exceeds image bounds")

    return grid, warnings


def detect_grid_spec(
    image_width: int,
    image_height: int,
    *,
    origin_x: int = 0,
    origin_y: int = 0,
) -> tuple[GridSpec, list[str]]:
    """Conservative placeholder detection for the MVP.

    It only handles the obvious case where a common pixel scale divides both
    dimensions. Manual override remains the reliable path.
    """

    available_width = image_width - origin_x
    available_height = image_height - origin_y
    for cell_size in (8, 6, 5, 4, 3, 2, 1):
        if available_width % cell_size == 0 and available_height % cell_size == 0:
            grid, warnings = derive_grid_spec(
                image_width,
                image_height,
                cell_width=cell_size,
                cell_height=cell_size,
                origin_x=origin_x,
                origin_y=origin_y,
            )
            warnings.append(
                "auto-grid is an MVP heuristic; use manual cell size for reliable output"
            )
            return grid, warnings

    raise ValueError("cannot infer grid automatically")
