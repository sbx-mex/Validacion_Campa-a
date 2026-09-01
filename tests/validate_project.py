#!/usr/bin/env python3
"""Valida el contrato operativo, los recursos y la privacidad del sitio."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str):
    with (ROOT / relative).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    checklist = load_json("data/fall26_checklist.json")
    settings = load_json("config/settings.json")
    manifest = load_json("manifest.webmanifest")
    sections = checklist["sections"]
    items = [item for section in sections for item in section["items"]]

    require(len(sections) == 9, "El recorrido debe contener 9 secciones.")
    require(len(items) == 36, "El recorrido debe contener exactamente 36 controles.")
    require([item["id"] for item in items] == [f"q{index:02d}" for index in range(1, 37)], "Los IDs deben ser secuenciales q01-q36.")
    require(len({item["id"] for item in items}) == 36, "Los IDs no pueden repetirse.")
    require(settings["statuses"]["cumple"]["value"] == 1, "Cumple debe valer 1.")
    require(settings["statuses"]["no_cumple"]["value"] == 0, "No cumple debe valer 0.")
    require(settings["statuses"]["na"]["value"] is None, "No aplica no pondera.")
    require("25" in settings["expectedMinutes"] and "30" in settings["expectedMinutes"], "Duración esperada inválida.")

    referenced = []
    for item in items:
        require(item.get("question") and item.get("criterion") and item.get("applies"), f"Contenido incompleto en {item['id']}.")
        image = item.get("image")
        if image:
            require(image.endswith(".webp"), f"La referencia {item['id']} debe ser WebP.")
            path = ROOT / image
            require(path.is_file() and path.stat().st_size > 1000, f"Falta la referencia {image}.")
            with Image.open(path) as opened:
                require(opened.format == "WEBP", f"Formato inválido en {image}.")
                require(opened.width >= 50 and opened.height >= 100 and opened.width * opened.height >= 10000, f"Referencia demasiado pequeña: {image}.")
            referenced.append(image)
    require(len(referenced) == 30, "Deben existir exactamente 30 referencias visuales útiles.")

    required_files = [
        "index.html", "styles.css", "app.js", "service-worker.js", "manifest.webmanifest",
        "assets/icons/icon.svg", "scripts/generate_store_report.py", "scripts/scoring.py", "PRIVACIDAD.md",
    ]
    for relative in required_files:
        require((ROOT / relative).is_file(), f"Falta {relative}.")
    require(manifest["start_url"] == "./", "El manifest debe funcionar en una subruta de GitHub.")

    web_text = "\n".join((ROOT / relative).read_text(encoding="utf-8") for relative in ["index.html", "styles.css", "app.js", "service-worker.js"])
    require("Información privada" in web_text, "La interfaz debe mostrar el aviso de privacidad.")
    require(not re.search(r"https?://", web_text, re.IGNORECASE), "La aplicación no debe depender de recursos externos.")
    require('id="storeInput"' in web_text and 'id="validatorInput"' in web_text, "Faltan los dos datos de identidad permitidos.")
    service_worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    for image in referenced:
        require(f'"{Path(image).stem}"' in service_worker, f"La referencia offline no está declarada: {image}.")
    forbidden_sources = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in {".zip", ".jpg", ".jpeg"}]
    require(not forbidden_sources, "No deben incluirse fuentes privadas crudas dentro del proyecto.")

    sample = ROOT / "sample/ejemplo_resultado.json"
    require(sample.is_file(), "Falta el JSON de ejemplo.")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "reporte.pdf"
        subprocess.run([sys.executable, str(ROOT / "scripts/generate_store_report.py"), "--input", str(sample), "--output", str(output)], check=True, cwd=ROOT)
        require(output.read_bytes().startswith(b"%PDF"), "El reporte generado no es un PDF válido.")
        require(output.stat().st_size > 4000, "El reporte PDF parece incompleto.")

    print(f"Proyecto válido: {len(sections)} secciones, {len(items)} controles, {len(referenced)} referencias WebP.")


if __name__ == "__main__":
    main()
