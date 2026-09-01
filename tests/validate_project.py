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
    require(settings.get("schemaVersion") == 2, "La experiencia debe usar settings schemaVersion 2.")
    require(settings["privacy"]["storageMode"] == "local_only", "Los resultados deben guardarse sólo localmente.")
    require(0 < settings["privacy"]["retentionHours"] <= 24, "La retención local no puede superar 24 horas.")
    require(settings["privacy"]["requireAcceptanceEverySession"] is True, "Debe confirmarse la responsabilidad en cada sesión.")
    require(settings["experience"]["theme"]["heroImage"] == "assets/reference/q07.webp", "La portada debe usar la referencia Peanuts ya autorizada.")

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

    html_text = (ROOT / "index.html").read_text(encoding="utf-8")
    app_text = (ROOT / "app.js").read_text(encoding="utf-8")
    web_text = "\n".join((ROOT / relative).read_text(encoding="utf-8") for relative in ["index.html", "styles.css", "app.js", "service-worker.js"])
    require("Información privada" in web_text, "La interfaz debe mostrar el aviso de privacidad.")
    require(not re.search(r"https?://", web_text, re.IGNORECASE), "La aplicación no debe depender de recursos externos.")
    require('id="storeInput"' in web_text and 'id="validatorInput"' in web_text, "Faltan los dos datos de identidad permitidos.")
    for required_id in ["privacyDialog", "responsibilityText", "clearLocalData", "sectionRail", "summaryPrivacyWarning"]:
        require(f'id="{required_id}"' in web_text, f"Falta el control de experiencia/privacidad {required_id}.")
    require("retentionHours" in app_text, "La aplicación debe aplicar retención local.")
    dom_block = re.search(r"const ids = \[(.*?)\];", app_text, re.DOTALL)
    require(dom_block is not None, "No se encontró el contrato de elementos DOM.")
    dom_ids = re.findall(r'"([A-Za-z][A-Za-z0-9]+)"', dom_block.group(1))
    missing_dom = [element_id for element_id in dom_ids if f'id="{element_id}"' not in html_text]
    require(not missing_dom, f"Faltan elementos DOM declarados en app.js: {missing_dom}")
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
