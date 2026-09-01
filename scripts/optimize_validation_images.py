#!/usr/bin/env python3
"""Normaliza las referencias operativas y genera lotes listos para sustituir."""

from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


IMAGE_MAP = [
    ("Zona Hand Off.jpeg", "q25"),
    ("Vaso verde México 2026.jpeg", "q02"),
    ("Tabla nueva de madera.jpeg", "q01"),
    ("Second choice Blonde.jpeg", "q19"),
    ("Rewards y cenefas.jpeg", "q15"),
    ("Promoplanner y Delivery.jpeg", "q04"),
    ("Mueble Merch.jpeg", "q22"),
    ("Mastrena.jpeg", "q18"),
    ("Condiment · CDMX.jpeg", "q24"),
    ("Community Board.jpeg", "q23"),
    ("Colombia Nariño.jpeg", "q03"),
    ("Canastas.jpeg", "q21"),
    ("BUNN.jpeg", "q17"),
    ("BNTK con objetivos.jpeg", "q26"),
    ("Aboards · segunda vigencia.jpeg", "q06"),
    ("Aboards · primera vigencia.jpeg", "q05"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="ZIP o carpeta con las 16 imágenes fuente.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package-dir", type=Path, required=True, help="Carpeta para los tres ZIP de sustitución.")
    return parser.parse_args()


def safe_extract(source: Path, destination: Path) -> Path:
    if source.is_dir():
        return source
    if not zipfile.is_zipfile(source):
        raise ValueError(f"La fuente no es una carpeta ni un ZIP válido: {source}")
    with zipfile.ZipFile(source) as archive:
        root = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Ruta insegura dentro del ZIP: {member.filename}")
        archive.extractall(destination)
    return destination


def optimize_image(source: Path, destination: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_size = image.size

        longest = max(image.size)
        if longest < 900:
            scale = min(4.0, 1200 / longest)
        elif longest < 1400:
            scale = 1400 / longest
        else:
            scale = 1.0
        if scale > 1:
            target = (round(image.width * scale), round(image.height * scale))
            image = image.resize(target, Image.Resampling.LANCZOS)

        image = ImageEnhance.Contrast(image).enhance(1.035)
        image = ImageEnhance.Color(image).enhance(1.015)
        image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=3))

        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "WEBP", quality=92, method=6, exact=True)
        return original_size, image.size


def write_package(path: Path, ids: list[str], reference_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for image_id in ids:
            source = reference_dir / f"{image_id}.webp"
            archive.write(source, f"assets/reference/{source.name}")


def main() -> None:
    args = parse_args()
    reference_dir = args.project_root / "assets/reference"
    with tempfile.TemporaryDirectory(prefix="fall26-images-") as temporary:
        source_dir = safe_extract(args.source, Path(temporary))
        available = {path.name: path for path in source_dir.rglob("*") if path.is_file()}
        expected = {name for name, _ in IMAGE_MAP}
        missing = sorted(expected - available.keys())
        if missing:
            raise ValueError("Faltan imágenes requeridas: " + ", ".join(missing))

        for filename, image_id in IMAGE_MAP:
            before, after = optimize_image(available[filename], reference_dir / f"{image_id}.webp")
            print(f"{image_id}: {filename} · {before[0]}x{before[1]} → {after[0]}x{after[1]}")

    first_lot = [image_id for _, image_id in IMAGE_MAP[:10]]
    second_lot = [image_id for _, image_id in IMAGE_MAP[10:]]
    all_ids = first_lot + second_lot
    if args.package_dir.exists():
        for archive in args.package_dir.glob("Imagenes_Validacion_*.zip"):
            archive.unlink()
    else:
        args.package_dir.mkdir(parents=True)
    write_package(args.package_dir / "Imagenes_Validacion_Lote_1_de_10.zip", first_lot, reference_dir)
    write_package(args.package_dir / "Imagenes_Validacion_Lote_2_de_6.zip", second_lot, reference_dir)
    write_package(args.package_dir / "Imagenes_Validacion_16_Archivos.zip", all_ids, reference_dir)
    print(f"Paquetes listos en: {args.package_dir}")


if __name__ == "__main__":
    main()
