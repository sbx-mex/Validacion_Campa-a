#!/usr/bin/env python3
"""Construye un ZIP limpio y un manifiesto SHA-256 para GitHub."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.sha256"
EXCLUDED_DIRS = {".git", "__pycache__", ".idea", ".vscode", "tmp"}
EXCLUDED_NAMES = {".DS_Store", "MANIFEST.sha256"}
FORBIDDEN_SUFFIXES = {".zip", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--root-name",
        default="Validacion_Campana",
        help="Nombre de la carpeta raíz dentro del ZIP.",
    )
    return parser.parse_args()


def project_files(output: Path) -> list[Path]:
    output = output.resolve()
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() == output:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts) or path.name in EXCLUDED_NAMES:
            continue
        if relative.parts[0] == "exports" and path.name != ".gitkeep":
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f"Fuente cruda o paquete anidado no permitido: {relative}")
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_manifest(files: list[Path]) -> None:
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_root_name(root_name: str) -> str:
    candidate = Path(root_name)
    if not root_name.strip() or candidate.name != root_name or root_name in {".", ".."}:
        raise ValueError("--root-name debe ser un nombre de carpeta simple y seguro")
    return root_name


def write_zip(files: list[Path], output: Path, root_name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*files, MANIFEST]:
            relative = path.relative_to(ROOT)
            archive.write(path, Path(root_name) / relative)


def main() -> None:
    args = parse_args()
    files = project_files(args.output)
    write_manifest(files)
    write_zip(files, args.output, validate_root_name(args.root_name))
    print(f"Release listo: {args.output} ({len(files) + 1} archivos)")


if __name__ == "__main__":
    main()
