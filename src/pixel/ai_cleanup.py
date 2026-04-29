from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from pixel.cleanup import (
    remove_isolated_pixels_in_region,
    remove_tiny_components_in_region,
)


SUPPORTED_AI_CLEANUP_ACTIONS = {
    "remove_isolated_pixels",
    "remove_tiny_components",
}


@dataclass(frozen=True)
class AiCleanupRegion:
    x: int
    y: int
    width: int
    height: int
    issue: str
    action: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "issue": self.issue,
            "action": self.action,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class AiCleanupAdvice:
    model: str
    regions: tuple[AiCleanupRegion, ...]
    raw_text: str = ""
    warnings: tuple[str, ...] = ()
    ignored_regions: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "regions": [region.to_dict() for region in self.regions],
            "warnings": list(self.warnings),
            "ignored_regions": list(self.ignored_regions),
        }


@dataclass(frozen=True)
class AiCleanupApplication:
    pixels: NDArray[np.integer]
    accepted_regions: list[dict[str, Any]] = field(default_factory=list)
    ignored_regions: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_ai_cleanup_advice(text: str, *, model: str) -> AiCleanupAdvice:
    payload = _load_json_object(text)
    regions_raw = payload.get("regions", [])
    if not isinstance(regions_raw, list):
        raise ValueError("AI cleanup advice must contain a regions list")

    regions: list[AiCleanupRegion] = []
    ignored: list[dict[str, Any]] = []
    for index, value in enumerate(regions_raw):
        if not isinstance(value, dict):
            ignored.append({"index": index, "reason": "region is not an object"})
            continue
        try:
            region = AiCleanupRegion(
                x=int(value["x"]),
                y=int(value["y"]),
                width=int(value["width"]),
                height=int(value["height"]),
                issue=str(value.get("issue", "")),
                action=str(value["action"]),
                confidence=float(value.get("confidence", 1.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            ignored.append(
                {
                    "index": index,
                    "reason": f"invalid region: {exc}",
                    "region": value,
                }
            )
            continue
        regions.append(region)

    return AiCleanupAdvice(
        model=model,
        regions=tuple(regions),
        raw_text=text,
        ignored_regions=tuple(ignored),
    )


def apply_ai_cleanup_advice(
    indexed: NDArray[np.integer],
    advice: AiCleanupAdvice,
    *,
    transparent_index: int | None = None,
) -> AiCleanupApplication:
    if indexed.ndim != 2:
        raise ValueError("indexed must have shape H x W")

    cleaned = indexed.copy()
    accepted: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = list(advice.ignored_regions)
    warnings = list(advice.warnings)

    for region in advice.regions:
        clipped = _clip_region(region, indexed.shape)
        if clipped is None:
            ignored.append(
                {
                    "region": region.to_dict(),
                    "reason": "region is outside the output grid",
                }
            )
            continue
        if region.action not in SUPPORTED_AI_CLEANUP_ACTIONS:
            ignored.append(
                {
                    "region": region.to_dict(),
                    "reason": f"unsupported action: {region.action}",
                }
            )
            continue

        before = cleaned.copy()
        if region.action == "remove_isolated_pixels":
            cleaned = remove_isolated_pixels_in_region(
                cleaned,
                x=clipped.x,
                y=clipped.y,
                width=clipped.width,
                height=clipped.height,
                transparent_index=transparent_index,
            )
        elif region.action == "remove_tiny_components":
            cleaned = remove_tiny_components_in_region(
                cleaned,
                x=clipped.x,
                y=clipped.y,
                width=clipped.width,
                height=clipped.height,
                transparent_index=transparent_index,
            )

        changed_pixels = int(np.sum(before != cleaned))
        accepted.append(
            {
                "region": region.to_dict(),
                "clipped_region": clipped.to_dict(),
                "changed_pixels": changed_pixels,
            }
        )

    if ignored:
        warnings.append(f"ignored {len(ignored)} AI cleanup region(s)")
    return AiCleanupApplication(
        pixels=cleaned,
        accepted_regions=accepted,
        ignored_regions=ignored,
        warnings=warnings,
    )


def _load_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("AI cleanup advice is not valid JSON") from None
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("AI cleanup advice is not valid JSON") from exc

    if not isinstance(value, dict):
        raise ValueError("AI cleanup advice must be a JSON object")
    return value


def _clip_region(
    region: AiCleanupRegion,
    shape: tuple[int, int],
) -> AiCleanupRegion | None:
    rows, cols = shape
    x0 = max(0, region.x)
    y0 = max(0, region.y)
    x1 = min(cols, region.x + region.width)
    y1 = min(rows, region.y + region.height)
    if x1 <= x0 or y1 <= y0:
        return None
    return AiCleanupRegion(
        x=x0,
        y=y0,
        width=x1 - x0,
        height=y1 - y0,
        issue=region.issue,
        action=region.action,
        confidence=region.confidence,
    )
