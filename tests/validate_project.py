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
    export_experience = load_json("data/export_experience.json")
    sections = checklist["sections"]
    journey_stages = checklist["journeyStages"]
    items = [item for section in sections for item in section["items"]]

    require(len(sections) == 9, "El recorrido debe contener 9 secciones.")
    require(len(journey_stages) == 5, "El Customer Journey debe contener cinco momentos.")
    stage_ids = {stage["id"] for stage in journey_stages}
    require(len(stage_ids) == 5, "Los momentos del Customer Journey no pueden repetirse.")
    require(all(section.get("journeyStageId") in stage_ids for section in sections), "Cada sección debe pertenecer a un momento válido.")
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
    require(settings["experience"]["theme"]["heroImage"] == "assets/ui/fall26-campaign-reference.webp", "La portada debe usar la referencia oficial Fall optimizada.")
    require(settings["experience"]["navigation"].get("showImmediateGuidance") is True, "La guía inmediata debe permanecer activa.")
    require(settings["experience"]["navigation"].get("style") == "customer_journey", "La navegación debe usar Customer Journey.")
    require(settings["experience"].get("ios", {}).get("minimumTouchTarget") == 48, "Los controles táctiles deben medir al menos 48 px.")
    require(settings["experience"]["navigation"].get("autoAdvanceStatuses") == ["cumple", "na"], "Cumple y No aplica deben avanzar automáticamente.")
    require(350 <= settings["experience"]["navigation"].get("autoAdvanceDelayMs", 0) <= 1500, "El avance automático debe permitir leer la confirmación.")

    corrective_actions = checklist.get("guidance", {}).get("correctiveActions", {})
    require(set(corrective_actions) == {item["id"] for item in items}, "Cada control debe tener una corrección inmediata única.")
    require(all(len(str(action).strip()) >= 25 for action in corrective_actions.values()), "Las correcciones inmediatas deben ser claras y accionables.")
    require(export_experience.get("schemaVersion") == 1, "La experiencia de exportación debe usar schemaVersion 1.")
    require(export_experience["before"]["title"] == "Estamos trabajando para ti", "Falta el mensaje cálido previo a la exportación.")
    require("DM" in export_experience["after"]["opportunityMessage"], "El cierre debe orientar el seguimiento con el DM.")

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
    require(len(referenced) == 34, "Deben existir exactamente 34 referencias visuales útiles.")

    required_files = [
        "index.html", "styles.css", "app.js", "service-worker.js", "manifest.webmanifest",
        "assets/icons/icon.svg", "assets/icons/apple-touch-icon.png", "assets/icons/icon-192.png", "assets/icons/icon-512.png",
        "assets/ui/fall26-campaign-reference.webp", "assets/ui/export-working.webp", "assets/ui/export-complete.webp",
        "data/export_experience.json", "scripts/build_ios_assets.py", "scripts/prepare_campaign_ui.py",
        "scripts/generate_store_report.py", "scripts/optimize_validation_images.py", "scripts/scoring.py", "PRIVACIDAD.md",
    ]
    for relative in required_files:
        require((ROOT / relative).is_file(), f"Falta {relative}.")
    require(manifest["start_url"] == "./", "El manifest debe funcionar en una subruta de GitHub.")
    icon_sizes = {icon["sizes"] for icon in manifest["icons"]}
    require({"180x180", "192x192", "512x512"}.issubset(icon_sizes), "El manifest debe incluir iconos iOS/PWA nítidos.")
    for relative, expected_size in [
        ("assets/icons/apple-touch-icon.png", (180, 180)),
        ("assets/icons/icon-192.png", (192, 192)),
        ("assets/icons/icon-512.png", (512, 512)),
    ]:
        with Image.open(ROOT / relative) as opened:
            require(opened.size == expected_size, f"Tamaño inválido en {relative}.")
    for relative, expected_size in [
        ("assets/ui/fall26-campaign-reference.webp", (1200, 1200)),
        ("assets/ui/export-working.webp", (960, 600)),
        ("assets/ui/export-complete.webp", (960, 540)),
    ]:
        with Image.open(ROOT / relative) as opened:
            require(opened.format == "WEBP" and opened.size == expected_size, f"Recurso de campaña inválido: {relative}.")

    html_text = (ROOT / "index.html").read_text(encoding="utf-8")
    app_text = (ROOT / "app.js").read_text(encoding="utf-8")
    web_text = "\n".join((ROOT / relative).read_text(encoding="utf-8") for relative in ["index.html", "styles.css", "app.js", "service-worker.js"])
    require("La información publicada es propiedad de la marca" in web_text, "La interfaz debe mostrar el aviso de propiedad y no divulgación.")
    require("Copyright 2026 © Starbucks México" in web_text, "La interfaz debe mostrar el copyright solicitado.")
    require("Atajos:" not in html_text, "Los atajos no deben mostrarse en la interfaz.")
    require("hero-metrics" not in html_text, "La portada no debe mostrar métricas operativas.")
    require(not re.search(r"https?://", web_text, re.IGNORECASE), "La aplicación no debe depender de recursos externos.")
    require('id="storeInput"' in web_text and 'id="validatorInput"' in web_text, "Faltan los dos datos de identidad permitidos.")
    for required_id in [
        "privacyDialog", "responsibilityText", "clearLocalData", "sectionRail", "summaryPrivacyWarning",
        "responseGuidance", "applyCorrection", "strengthCount", "strengthsList", "exportDialog",
        "exportConfirm", "exportPrimary", "exportSecondary", "exportOpportunityNote",
    ]:
        require(f'id="{required_id}"' in web_text, f"Falta el control de experiencia/privacidad {required_id}.")
    require("Descargar JSON" not in html_text and "El JSON descargado" not in html_text, "La interfaz no debe mostrar descarga o instrucción JSON.")
    require("downloadResultJson" not in app_text, "El motor web no debe conservar la descarga JSON visible.")
    require("retentionHours" in app_text, "La aplicación debe aplicar retención local.")
    require("scheduleAutoAdvance" in app_text and "cancelAutoAdvance" in app_text, "Falta navegación automática segura.")
    require("renderJourneyStages" in app_text and "data-edit-question" in app_text, "Falta resumen por Customer Journey o edición de acuerdos.")
    require("openExportConfirmation" in app_text and "renderExportStage" in app_text, "Falta confirmación antes y después de exportar.")
    require("buildPdfFilename" in app_text and "_Fall" in app_text, "Falta nombre dinámico Tienda_Fall.")
    require('apple-mobile-web-app-capable' in html_text and 'apple-touch-icon' in html_text, "Falta compatibilidad iOS instalada.")
    dom_block = re.search(r"const ids = \[(.*?)\];", app_text, re.DOTALL)
    require(dom_block is not None, "No se encontró el contrato de elementos DOM.")
    dom_ids = re.findall(r'"([A-Za-z][A-Za-z0-9]+)"', dom_block.group(1))
    missing_dom = [element_id for element_id in dom_ids if f'id="{element_id}"' not in html_text]
    require(not missing_dom, f"Faltan elementos DOM declarados en app.js: {missing_dom}")
    service_worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    require("validacion-fall26-v6" in service_worker, "La caché offline debe apuntar a la versión 6.")
    for icon in ["apple-touch-icon.png", "icon-192.png", "icon-512.png"]:
        require(icon in service_worker, f"El icono iOS/PWA no está disponible offline: {icon}.")
    for asset in ["data/export_experience.json", "fall26-campaign-reference.webp", "export-working.webp", "export-complete.webp"]:
        require(asset in service_worker, f"La experiencia de exportación no está disponible offline: {asset}.")
    require("Damos_Seguimiento.webp" not in web_text and "Un_placer_haber_Ayudado.webp" not in web_text, "No deben usarse recursos ajenos a la campaña oficial.")
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

    print(f"Proyecto válido: {len(journey_stages)} momentos, {len(sections)} secciones, {len(items)} controles, {len(referenced)} referencias WebP.")


if __name__ == "__main__":
    main()
