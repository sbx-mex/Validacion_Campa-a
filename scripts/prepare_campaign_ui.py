#!/usr/bin/env python3
"""Prepara recortes WebP de la referencia oficial Fall 26 para la experiencia de exportación."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Imagen oficial Fall 26 proporcionada.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets" / "ui")
    return parser.parse_args()


def improve(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(1.025)
    return image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=118, threshold=3))


def crop_box(image: Image.Image, relative_box: tuple[float, float, float, float]) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = relative_box
    return image.crop((int(width * left), int(height * top), int(width * right), int(height * bottom)))


def save_webp(image: Image.Image, path: Path, size: tuple[int, int], *, fit: bool = True) -> None:
    prepared = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS) if fit else ImageOps.contain(
        image, size, method=Image.Resampling.LANCZOS,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    prepared.save(path, "WEBP", quality=90, method=6, exact=True)
    print(f"Generado: {path} · {prepared.width}x{prepared.height}")


def main() -> None:
    args = parse_args()
    if not args.source.is_file():
        raise FileNotFoundError(f"No existe la referencia oficial: {args.source}")

    with Image.open(args.source) as opened:
        source = improve(opened)

    save_webp(source, args.output_dir / "fall26-campaign-reference.webp", (1200, 1200))

    # Snoopy y Woodstock acompañan el momento de preparación del reporte.
    working = crop_box(source, (0.27, 0.35, 0.78, 0.77))
    save_webp(working, args.output_dir / "export-working.webp", (960, 600))

    # El grupo completo cierra el recorrido con reconocimiento y sentido de equipo.
    complete = crop_box(source, (0.00, 0.33, 1.00, 0.79))
    save_webp(complete, args.output_dir / "export-complete.webp", (960, 540))


if __name__ == "__main__":
    main()
