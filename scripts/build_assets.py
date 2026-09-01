#!/usr/bin/env python3
"""Genera referencias WebP usando exclusivamente las láminas fuente de Fall 26."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class CropSpec:
    source: str
    page: int
    box: tuple[int, int, int, int] | None = None


CROPS: dict[str, CropSpec] = {
    "q01": CropSpec("w36", 3, (485, 220, 650, 338)),
    "q02": CropSpec("w36", 3, (585, 425, 655, 535)),
    "q05": CropSpec("fall", 3, (5, 80, 335, 330)),
    "q06": CropSpec("fall", 3, (5, 270, 335, 535)),
    "q07": CropSpec("fall", 4),
    "q09": CropSpec("fall", 5),
    "q10": CropSpec("fall", 6),
    "q11": CropSpec("fall", 8),
    "q12": CropSpec("fall", 9),
    "q13": CropSpec("fall", 10, (0, 50, 580, 535)),
    "q14": CropSpec("fall", 10, (480, 45, 960, 535)),
    "q16": CropSpec("fall", 14),
    "q17": CropSpec("fall", 12, (0, 60, 510, 535)),
    "q18": CropSpec("fall", 12, (390, 50, 960, 535)),
    "q21": CropSpec("fall", 13, (0, 50, 540, 535)),
    "q22": CropSpec("fall", 13, (420, 50, 960, 535)),
    "q23": CropSpec("fall", 15, (0, 50, 550, 535)),
    "q24": CropSpec("fall", 15, (420, 50, 960, 535)),
    "q25": CropSpec("fall", 16, (0, 60, 550, 535)),
    "q26": CropSpec("fall", 16, (410, 45, 960, 535)),
    "q27": CropSpec("fall", 17),
    "q28": CropSpec("w36", 6, (600, 300, 1280, 720)),
    "q29": CropSpec("fall", 22),
    "q30": CropSpec("fall", 23),
    "q31": CropSpec("fall", 24),
    "q32": CropSpec("fall", 23, (0, 250, 960, 540)),
    "q33": CropSpec("fall", 25),
    "q34": CropSpec("fall", 27),
    "q35": CropSpec("fall", 29),
    "q36": CropSpec("fall", 30),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fall-dir", type=Path, required=True)
    parser.add_argument("--w36-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("assets/reference"))
    return parser.parse_args()


def resolve_source(directory: Path, page: int) -> Path:
    matches = sorted(directory.glob(f"*_{page}.jpg")) + sorted(directory.glob(f"*_{page}.jpeg"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Se esperaba una sola página {page} en {directory}; se encontraron {len(matches)}.")
    return matches[0]


def clamp_box(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    left, top, right, bottom = box
    safe = (max(0, left), max(0, top), min(width, right), min(height, bottom))
    if safe[0] >= safe[2] or safe[1] >= safe[3]:
        raise ValueError(f"Recorte inválido {box} para imagen de tamaño {size}.")
    return safe


def add_private_band(image: Image.Image) -> Image.Image:
    band_height = max(34, round(image.height * 0.055))
    canvas = Image.new("RGB", (image.width, image.height + band_height), "white")
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, image.height, canvas.width, canvas.height), fill="#003b2d")
    font = ImageFont.load_default()
    text = "USO INTERNO - INFORMACION PRIVADA"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = max(12, (canvas.width - (bbox[2] - bbox[0])) // 2)
    y = image.height + (band_height - (bbox[3] - bbox[1])) // 2 - 1
    draw.text((x, y), text, fill="white", font=font)
    return canvas


def render_crop(source_path: Path, spec: CropSpec) -> Image.Image:
    with Image.open(source_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    if spec.box:
        image = image.crop(clamp_box(spec.box, image.size))
    image.thumbnail((1200, 760), Image.Resampling.LANCZOS)
    image = ImageOps.expand(image, border=8, fill="white")
    return add_private_band(image)


def main() -> None:
    args = parse_args()
    roots = {"fall": args.fall_dir, "w36": args.w36_dir}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for item_id, spec in CROPS.items():
        source_path = resolve_source(roots[spec.source], spec.page)
        output_path = args.output_dir / f"{item_id}.webp"
        image = render_crop(source_path, spec)
        image.save(output_path, "WEBP", quality=84, method=6)
        written.append(output_path)
        print(f"{item_id}: {source_path.name} -> {output_path}")
    print(f"Listo: {len(written)} referencias generadas sin imágenes inventadas.")


if __name__ == "__main__":
    main()
