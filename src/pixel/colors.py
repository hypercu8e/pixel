from __future__ import annotations

RgbaColor = tuple[int, int, int, int]


def parse_hex_color(value: str) -> RgbaColor:
    raw = value.strip()
    if raw.startswith("#"):
        raw = raw[1:]

    if len(raw) == 6:
        raw += "ff"
    if len(raw) != 8:
        raise ValueError("hex colors must be #RRGGBB or #RRGGBBAA")

    try:
        parts = tuple(int(raw[index : index + 2], 16) for index in range(0, 8, 2))
    except ValueError as exc:
        raise ValueError(f"invalid hex color: {value}") from exc

    return parts  # type: ignore[return-value]


def rgba_to_hex(color: RgbaColor) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in color)
