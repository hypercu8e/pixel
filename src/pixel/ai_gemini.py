from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

from PIL import Image

from pixel.ai_cleanup import AiCleanupAdvice, parse_ai_cleanup_advice
from pixel.export import indexed_to_rgba
from pixel.models import SpriteAsset, ValidationReport


AI_CLEANUP_PROMPT = """You are reviewing a pixel-art cleanup pipeline output.

Return only JSON with this shape:
{"regions":[{"x":0,"y":0,"width":1,"height":1,"issue":"background_noise","action":"remove_isolated_pixels","confidence":0.75}]}

Coordinates are in output grid cells, not source pixels. Use x/y as top-left.
Allowed actions:
- remove_isolated_pixels: single-cell visible noise with a clear neighbor majority
- remove_tiny_components: tiny visible clusters that look like background or cleanup noise

Only mark small regions that need deterministic cleanup. Do not suggest redrawing,
new colors, pose changes, or full-image edits.
"""


def plan_gemini_cleanup(
    input_path: str | Path,
    provisional_asset: SpriteAsset,
    report: ValidationReport,
    *,
    model: str,
) -> AiCleanupAdvice:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required for --ai-cleanup gemini")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ValueError(
            "google-genai is required for --ai-cleanup gemini; "
            "install with `python -m pip install -e .[ai]`"
        ) from exc

    input_bytes = _path_png_bytes(input_path)
    output_bytes = _asset_png_bytes(provisional_asset)
    prompt = _build_prompt(provisional_asset, report)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            "Source image before cleanup:",
            types.Part.from_bytes(data=input_bytes, mime_type="image/png"),
            "Provisional deterministic cleanup output:",
            types.Part.from_bytes(data=output_bytes, mime_type="image/png"),
            prompt,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return parse_ai_cleanup_advice(response.text or "", model=model)


def _asset_png_bytes(asset: SpriteAsset) -> bytes:
    rgba = indexed_to_rgba(asset.pixels, asset.palette)
    image = Image.fromarray(rgba, mode="RGBA")
    return _image_png_bytes(image)


def _path_png_bytes(path: str | Path) -> bytes:
    image = Image.open(path).convert("RGBA")
    return _image_png_bytes(image)


def _image_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_prompt(asset: SpriteAsset, report: ValidationReport) -> str:
    return "\n".join(
        [
            AI_CLEANUP_PROMPT,
            f"Grid: {asset.grid.cols} columns x {asset.grid.rows} rows.",
            f"Palette colors: {len(asset.palette.colors)}.",
            f"Validator metrics: {report.metrics}.",
            f"Validator warnings: {report.warnings}.",
        ]
    )
