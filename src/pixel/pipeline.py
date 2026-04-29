from __future__ import annotations

from pathlib import Path

from pixel.ai_cleanup import apply_ai_cleanup_advice
from pixel.ai_gemini import plan_gemini_cleanup
from pixel.alpha import estimate_background_color, resolve_alpha
from pixel.cleanup import cleanup_indexed
from pixel.export import save_png
from pixel.grid import derive_grid_spec, detect_grid_spec
from pixel.ingest import load_rgba
from pixel.models import CleanOptions, CleanResult, SpriteAsset
from pixel.palette import build_palette, snap_to_palette
from pixel.rasterizer import rasterize_indexed
from pixel.validate import validate_asset
from pixel.colors import rgba_to_hex


def clean_image(input_path: str | Path, output_path: str | Path, options: CleanOptions) -> CleanResult:
    rgba = load_rgba(input_path)
    source_height, source_width = rgba.shape[:2]
    warnings: list[str] = []

    transparent_color = options.transparent_color
    if options.auto_background:
        if transparent_color is not None:
            raise ValueError("--auto-background cannot be combined with --transparent-color")
        transparent_color = estimate_background_color(rgba)
        warnings.append(
            "auto-background estimated "
            f"{rgba_to_hex(transparent_color)} with tolerance {options.transparent_tolerance}"
        )

    resolved = resolve_alpha(
        rgba,
        alpha_threshold=options.alpha_threshold,
        transparent_color=transparent_color,
        transparent_tolerance=options.transparent_tolerance,
    )

    if options.auto_grid and options.cell_width is None:
        grid, grid_warnings = detect_grid_spec(
            source_width,
            source_height,
            origin_x=options.origin_x,
            origin_y=options.origin_y,
        )
    else:
        if options.cell_width is None:
            raise ValueError("manual grid requires --cell-width")
        grid, grid_warnings = derive_grid_spec(
            source_width,
            source_height,
            cell_width=options.cell_width,
            cell_height=options.cell_height,
            rows=options.rows,
            cols=options.cols,
            origin_x=options.origin_x,
            origin_y=options.origin_y,
        )

    palette = build_palette(
        resolved,
        colors=options.colors,
        explicit_palette=options.palette,
    )
    snapped = snap_to_palette(resolved, palette)
    rasterized = rasterize_indexed(snapped, grid, palette_size=len(palette.colors))
    cleaned = cleanup_indexed(
        rasterized,
        transparent_index=palette.transparent_index,
        remove_isolated=options.remove_isolated,
    )
    asset = SpriteAsset(grid=grid, palette=palette, pixels=cleaned)
    report = validate_asset(
        asset,
        source_width=source_width,
        source_height=source_height,
        warnings=warnings + grid_warnings,
    )

    ai_advice_report = None
    if options.ai_cleanup is not None:
        if options.ai_cleanup != "gemini":
            raise ValueError(f"unsupported AI cleanup provider: {options.ai_cleanup}")
        advice = plan_gemini_cleanup(
            input_path,
            asset,
            report,
            model=options.ai_model,
        )
        before_metrics = dict(report.metrics)
        application = apply_ai_cleanup_advice(
            asset.pixels,
            advice,
            transparent_index=palette.transparent_index,
        )
        asset = SpriteAsset(grid=grid, palette=palette, pixels=application.pixels)
        report = validate_asset(
            asset,
            source_width=source_width,
            source_height=source_height,
            warnings=warnings + grid_warnings + application.warnings,
        )
        ai_advice_report = {
            "model": options.ai_model,
            "advice": advice.to_dict(),
            "accepted_regions": application.accepted_regions,
            "ignored_regions": application.ignored_regions,
            "warnings": application.warnings,
            "metrics_before": before_metrics,
            "metrics_after": report.metrics,
        }

    save_png(output_path, asset)
    return CleanResult(asset=asset, report=report, ai_advice=ai_advice_report)
