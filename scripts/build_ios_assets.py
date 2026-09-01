#!/usr/bin/env python3
"""Genera iconos PWA/iOS nítidos con una identidad Fall original y sin recursos externos."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "icons"
GREEN = "#006241"
DARK = "#003B2D"
CREAM = "#FFF8ED"
ORANGE = "#F79435"
INK = "#2C2430"


def draw_icon(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGB", (canvas_size, canvas_size), GREEN)
    draw = ImageDraw.Draw(image)

    margin = int(canvas_size * 0.10)
    radius = int(canvas_size * 0.21)
    draw.rounded_rectangle(
        (margin, margin, canvas_size - margin, canvas_size - margin),
        radius=radius,
        fill=CREAM,
    )

    pumpkin_box = (
        int(canvas_size * 0.25), int(canvas_size * 0.28),
        int(canvas_size * 0.75), int(canvas_size * 0.72),
    )
    draw.ellipse(pumpkin_box, fill=ORANGE)
    draw.ellipse(
        (int(canvas_size * 0.34), pumpkin_box[1], int(canvas_size * 0.66), pumpkin_box[3]),
        outline="#D94F1D", width=max(2, int(canvas_size * 0.018)),
    )
    draw.rounded_rectangle(
        (int(canvas_size * 0.47), int(canvas_size * 0.20), int(canvas_size * 0.53), int(canvas_size * 0.34)),
        radius=max(2, int(canvas_size * 0.02)), fill=DARK,
    )

    check_width = max(3, int(canvas_size * 0.043))
    draw.line(
        [
            (int(canvas_size * 0.34), int(canvas_size * 0.51)),
            (int(canvas_size * 0.46), int(canvas_size * 0.62)),
            (int(canvas_size * 0.68), int(canvas_size * 0.39)),
        ],
        fill=CREAM,
        width=check_width,
        joint="curve",
    )

    draw.arc(
        (int(canvas_size * 0.69), int(canvas_size * 0.67), int(canvas_size * 0.84), int(canvas_size * 0.82)),
        start=195,
        end=340,
        fill=INK,
        width=max(2, int(canvas_size * 0.012)),
    )
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, size in (
        ("apple-touch-icon.png", 180),
        ("icon-192.png", 192),
        ("icon-512.png", 512),
    ):
        draw_icon(size).save(OUTPUT / filename, format="PNG", optimize=True)
        print(f"Generado: {OUTPUT / filename}")


if __name__ == "__main__":
    main()
