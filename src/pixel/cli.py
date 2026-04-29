from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pixel.colors import parse_hex_color
from pixel.grid import detect_grid_spec
from pixel.models import CleanOptions
from pixel.pipeline import clean_image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pixel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean = subparsers.add_parser(
        "clean",
        help="Convert fake pixel art into a clean indexed raster and export PNG.",
    )
    clean.add_argument("input", type=Path)
    clean.add_argument("output", type=Path)
    clean.add_argument("--cell-width", type=int)
    clean.add_argument("--cell-height", type=int)
    clean.add_argument("--rows", type=int)
    clean.add_argument("--cols", type=int)
    clean.add_argument("--origin-x", type=int, default=0)
    clean.add_argument("--origin-y", type=int, default=0)
    clean.add_argument("--auto-grid", action="store_true")
    clean.add_argument("--colors", type=int, default=16)
    clean.add_argument(
        "--palette",
        nargs="+",
        help="Explicit palette as hex colors, for example #00000000 #1a1c2c.",
    )
    clean.add_argument(
        "--auto-background",
        action="store_true",
        help="Estimate background color from image borders and make it transparent.",
    )
    clean.add_argument("--transparent-color", help="Chroma key color, for example #ff00ff.")
    clean.add_argument(
        "--transparent-tolerance",
        type=int,
        default=0,
        help="Per-channel tolerance for --transparent-color. Default: exact match.",
    )
    clean.add_argument("--alpha-threshold", type=int, default=1)
    clean.add_argument(
        "--remove-isolated",
        action="store_true",
        help="Remove unambiguous isolated visible pixels after rasterization.",
    )
    clean.add_argument(
        "--ai-cleanup",
        choices=["gemini"],
        help="Ask a vision model for targeted cleanup regions before final export.",
    )
    clean.add_argument(
        "--ai-model",
        default="gemini-2.5-flash",
        help="Model used by --ai-cleanup. Default: gemini-2.5-flash.",
    )
    clean.add_argument(
        "--ai-advice-report",
        type=Path,
        help="Optional JSON report with AI cleanup advice and applied regions.",
    )
    clean.add_argument("--report", type=Path, help="Optional JSON validation report path.")
    clean.add_argument("--quiet", action="store_true")
    clean.set_defaults(func=run_clean)
    return parser


def run_clean(args: argparse.Namespace) -> int:
    if args.ai_advice_report and not args.ai_cleanup:
        print("error: --ai-advice-report requires --ai-cleanup", file=sys.stderr)
        return 2

    transparent_color = (
        parse_hex_color(args.transparent_color) if args.transparent_color else None
    )
    palette = [parse_hex_color(value) for value in args.palette] if args.palette else None

    options = CleanOptions(
        cell_width=args.cell_width,
        cell_height=args.cell_height,
        rows=args.rows,
        cols=args.cols,
        origin_x=args.origin_x,
        origin_y=args.origin_y,
        auto_grid=args.auto_grid,
        colors=args.colors,
        palette=palette,
        auto_background=args.auto_background,
        transparent_color=transparent_color,
        transparent_tolerance=args.transparent_tolerance,
        alpha_threshold=args.alpha_threshold,
        remove_isolated=args.remove_isolated,
        ai_cleanup=args.ai_cleanup,
        ai_model=args.ai_model,
    )

    try:
        result = clean_image(args.input, args.output, options)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if args.auto_grid or args.cell_width is None:
            print(
                "hint: pass --cell-width and --cell-height for the reliable MVP path.",
                file=sys.stderr,
            )
        return 2

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(result.report.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if args.ai_advice_report:
        args.ai_advice_report.parent.mkdir(parents=True, exist_ok=True)
        args.ai_advice_report.write_text(
            json.dumps(result.ai_advice, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if not args.quiet:
        _print_result(result, args.output)
    return 0 if result.report.ok else 1


def _print_result(result, output: Path) -> None:
    grid = result.asset.grid
    palette = result.asset.palette
    metrics = result.report.metrics
    print(f"Input: {metrics['source_width']}x{metrics['source_height']}")
    print(
        "Grid: "
        f"{grid.cols}x{grid.rows} cells from "
        f"{grid.cell_width}x{grid.cell_height} source cells"
    )
    print(f"Palette: {len(palette.colors)} colors")
    print(f"Output: {output}")
    if result.ai_advice:
        accepted = len(result.ai_advice["accepted_regions"])
        ignored = len(result.ai_advice["ignored_regions"])
        print(f"AI cleanup: {accepted} accepted region(s), {ignored} ignored")

    for warning in result.report.warnings:
        print(f"warning: {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
