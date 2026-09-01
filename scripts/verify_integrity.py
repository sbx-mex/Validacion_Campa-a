#!/usr/bin/env python3
"""Comprueba que los archivos coincidan con MANIFEST.sha256."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.sha256"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    if not MANIFEST.is_file():
        raise FileNotFoundError("Ejecuta primero scripts/build_release.py.")
    checked = 0
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Falta: {relative}")
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"Integridad inválida: {relative}")
        checked += 1
    print(f"Integridad correcta: {checked} archivos.")


if __name__ == "__main__":
    main()
