#!/usr/bin/env python3
"""Genera el reporte PDF ejecutivo de una validación Fall 26."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from scoring import (
    build_execution_insights,
    build_journey_summary,
    calculate_counts,
    calculate_score,
    classify_score,
    validate_answers,
)


GREEN = colors.HexColor("#006241")
DARK = colors.HexColor("#003B2D")
ORANGE = colors.HexColor("#D94F1D")
CREAM = colors.HexColor("#FFF8ED")
INK = colors.HexColor("#2C2430")
MUTED = colors.HexColor("#5F6F69")
RED = colors.HexColor("#B42318")
LIGHT = colors.HexColor("#E9F2EE")
PLUM = colors.HexColor("#2C2430")
REGULAR = "DejaVu"
BOLD = "DejaVu-Bold"
ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"

pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Archivo de resultados de Validación Campaña.")
    parser.add_argument("--output", type=Path, required=True, help="Ruta del PDF de salida.")
    return parser.parse_args()


def safe_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return text.replace("\u2011", "-").replace("\u2013", "-").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    answers = payload.get("answers")
    if not isinstance(answers, list):
        raise ValueError("El JSON no contiene una lista answers válida.")
    validate_answers(answers)
    return payload


def parse_date(value: Any) -> str:
    if not value:
        return "Sin fecha"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return safe_text(value, 40)


def load_catalog() -> tuple[dict[str, str], dict[str, dict[str, str]], list[dict[str, str]]]:
    with (ROOT / "data" / "fall26_checklist.json").open("r", encoding="utf-8") as stream:
        checklist = json.load(stream)
    actions = checklist.get("guidance", {}).get("correctiveActions", {})
    if not isinstance(actions, dict):
        raise ValueError("El catálogo no contiene correcciones inmediatas válidas.")
    stages = checklist.get("journeyStages", [])
    stage_map = {str(stage["id"]): stage for stage in stages}
    item_map: dict[str, dict[str, str]] = {}
    for section in checklist.get("sections", []):
        stage = stage_map.get(str(section.get("journeyStageId")), {})
        for item in section.get("items", []):
            item_map[str(item["id"])] = {
                "sectionId": str(section.get("id") or ""),
                "sectionTitle": str(section.get("title") or ""),
                "journeyStageId": str(stage.get("id") or ""),
                "journeyStageTitle": str(stage.get("title") or ""),
                "journeyStageSubtitle": str(stage.get("subtitle") or ""),
                "title": str(item.get("title") or ""),
                "question": str(item.get("question") or ""),
                "criterion": str(item.get("criterion") or ""),
                "applies": str(item.get("applies") or ""),
            }
    return (
        {str(key): str(value) for key, value in actions.items()},
        item_map,
        [{str(key): str(value) for key, value in stage.items()} for stage in stages],
    )


def enrich_answers(answers: list[dict[str, Any]], catalog: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    enriched = []
    for answer in answers:
        normalized = dict(catalog.get(str(answer.get("id") or ""), {}))
        normalized.update(answer)
        enriched.append(normalized)
    return enriched


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(DARK)
    canvas.rect(0, height - 17 * mm, width, 17 * mm, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.rect(0, height - 18.2 * mm, width, 1.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 8)
    canvas.drawString(18 * mm, height - 10.7 * mm, "VALIDACIÓN CAMPAÑA · FALL 26")
    canvas.setFont(REGULAR, 7)
    canvas.drawRightString(width - 18 * mm, height - 10.7 * mm, "JUNTÉMONOS MÁS · USO INTERNO")
    canvas.setFillColor(colors.HexColor("#F79435"))
    canvas.circle(width - 14 * mm, height - 8.5 * mm, 1.4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#F7AA63"))
    canvas.setLineWidth(1.1)
    canvas.arc(width - 18 * mm, height - 13 * mm, width - 12 * mm, height - 7 * mm, 10, 115)
    canvas.setStrokeColor(colors.HexColor("#D8E3DE"))
    canvas.line(18 * mm, 15.5 * mm, width - 18 * mm, 15.5 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 5.8)
    canvas.drawString(18 * mm, 10.5 * mm, "La información publicada es propiedad de la marca y está prohibida su divulgación.")
    canvas.drawString(18 * mm, 7.2 * mm, "Copyright 2026 © Starbucks México")
    canvas.drawRightString(width - 18 * mm, 7.2 * mm, f"JUNTÉMONOS MÁS · Página {doc.page}")
    canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=BOLD, fontSize=23, leading=26, textColor=DARK, alignment=TA_LEFT, spaceAfter=5),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName=REGULAR, fontSize=9, leading=13, textColor=MUTED, spaceAfter=10),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=15, textColor=GREEN, spaceBefore=5, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName=REGULAR, fontSize=8.4, leading=11, textColor=INK),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName=REGULAR, fontSize=7.2, leading=9.2, textColor=MUTED),
        "privacy": ParagraphStyle("Privacy", parent=base["BodyText"], fontName=REGULAR, fontSize=7.1, leading=9, textColor=colors.white),
        "kpi": ParagraphStyle("Kpi", parent=base["Normal"], fontName=BOLD, fontSize=20, leading=22, textColor=DARK, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("KpiLabel", parent=base["Normal"], fontName=BOLD, fontSize=7, leading=8, textColor=MUTED, alignment=TA_CENTER),
        "white": ParagraphStyle("White", parent=base["Normal"], fontName=BOLD, fontSize=10, leading=12, textColor=colors.white, alignment=TA_CENTER),
        "eyebrow": ParagraphStyle("Eyebrow", parent=base["Normal"], fontName=BOLD, fontSize=7.5, leading=9, textColor=ORANGE, spaceAfter=3),
        "warm": ParagraphStyle("Warm", parent=base["BodyText"], fontName=REGULAR, fontSize=8, leading=10.5, textColor=colors.HexColor("#654836")),
    }


def kpi_card(value: str, label: str, styles: dict[str, ParagraphStyle], color=CREAM) -> Table:
    table = Table([[Paragraph(value, styles["kpi"])], [Paragraph(label, styles["kpi_label"]) ]], colWidths=[34 * mm], rowHeights=[12 * mm, 8 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D8CBB8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def journey_card(stage: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    counts = stage.get("counts") or {}
    score = stage.get("score")
    score_text = "-" if score is None else f"{float(score):.0f}%"
    detail = f"{counts.get('cumple', 0)} C · {counts.get('no_cumple', 0)} NC · {counts.get('na', 0)} N/A"
    accent = GREEN if score is not None and score >= 90 else ORANGE if score is not None and score >= 75 else RED if score is not None else MUTED
    card = Table([
        [Paragraph(safe_text(stage.get("title"), 22), styles["kpi_label"])],
        [Paragraph(score_text, styles["kpi"])],
        [Paragraph(detail, styles["kpi_label"])],
    ], colWidths=[34.8 * mm], rowHeights=[6 * mm, 10 * mm, 6 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFDF8")),
        ("BOX", (0, 0), (-1, -1), .75, colors.HexColor("#D8CBB8")),
        ("LINEABOVE", (0, 0), (-1, 0), 2.2, accent),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return card


def build_report(payload: dict[str, Any], output_path: Path) -> None:
    corrective_actions, catalog, stage_definitions = load_catalog()
    answers = enrich_answers(payload["answers"], catalog)
    counts = calculate_counts(answers)
    score = calculate_score(counts)
    label, message = classify_score(score)
    stages = build_journey_summary(answers)
    stage_result_map = {stage["id"]: stage for stage in stages}
    stages = [stage_result_map.get(stage["id"], {
        "id": stage["id"], "title": stage["title"], "subtitle": stage["subtitle"],
        "score": None, "counts": {"cumple": 0, "no_cumple": 0, "na": 0, "respondidas": 0},
    }) for stage in stage_definitions]
    insights = build_execution_insights(answers, corrective_actions)
    strengths = insights["strengths"]
    opportunities = insights["opportunities"]
    styles = build_styles()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output_path), pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=23 * mm, bottomMargin=19 * mm, title="Validación Campaña Fall 26",
        author="Validación Campaña",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=header_footer)])

    story = [
        Paragraph("RECORRIDO COMPLETADO", styles["eyebrow"]),
        Paragraph("Resultado Fall 26", styles["title"]),
        Paragraph("Gracias por validar. Celebremos lo que está listo y resolvamos juntos cada oportunidad.", styles["subtitle"]),
    ]
    responsibility = payload.get("responsibility") or {}
    acceptance = "Aceptación registrada" if responsibility.get("accepted") else "Aceptación no incluida en el archivo"
    retention = safe_text(responsibility.get("retentionHours") or 24, 4)
    privacy_line = (
        f"<b>USO RESPONSABLE</b> · {acceptance} · Revisión de campaña · "
        f"Guardado local hasta {retention} horas · No divulgar."
    )
    identity = Table([
        [Paragraph("<b>Tienda</b><br/>" + safe_text(payload.get("store"), 80), styles["body"]),
         Paragraph("<b>Quién validó</b><br/>" + safe_text(payload.get("validator"), 80), styles["body"]),
         Paragraph("<b>Cierre</b><br/>" + parse_date(payload.get("completedAt")), styles["body"])],
        [Paragraph(privacy_line, styles["privacy"]), "", ""],
    ], colWidths=[doc.width * .36, doc.width * .36, doc.width * .28])
    identity.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), .6, colors.HexColor("#BCD2C8")),
        ("INNERGRID", (0, 0), (-1, -1), .4, colors.HexColor("#BCD2C8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("SPAN", (0, 1), (-1, 1)), ("BACKGROUND", (0, 1), (-1, 1), PLUM),
        ("LEFTPADDING", (0, 1), (-1, 1), 8), ("RIGHTPADDING", (0, 1), (-1, 1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    story += [identity, Spacer(1, 4 * mm)]

    score_text = "-" if score is None else f"{score:.1f}%"
    cards = Table([[
        kpi_card(score_text, "TASA DE EXITO", styles, colors.HexColor("#DDECE5")),
        kpi_card(str(counts["cumple"]), "CUMPLE", styles),
        kpi_card(str(counts["no_cumple"]), "NO CUMPLE", styles, colors.HexColor("#FCE8E6")),
        kpi_card(str(counts["na"]), "NO APLICA", styles),
    ]], colWidths=[doc.width / 4] * 4)
    cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story += [cards, Spacer(1, 5 * mm)]

    state_color = GREEN if score is not None and score >= 90 else ORANGE if score is not None and score >= 75 else RED
    result = Table([[Paragraph(safe_text(label, 80), styles["white"]), Paragraph(safe_text(message, 180), styles["body"]) ]], colWidths=[48 * mm, doc.width - 48 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), state_color), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8F6F1")),
        ("BOX", (0, 0), (-1, -1), .7, state_color), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    strength_names = " · ".join(safe_text(answer.get("title"), 45) for answer in strengths[:6])
    if len(strengths) > 6:
        strength_names += f" · y {len(strengths) - 6} más"
    if not strength_names:
        strength_names = "Los puntos corregidos aparecerán aquí en la siguiente validación."
    recognition = Table([[
        Paragraph(f"{len(strengths)}<br/><font size='7'>PUNTOS A FAVOR</font>", styles["white"]),
        Paragraph(f"<b>Reconozcamos al equipo</b><br/>{strength_names}", styles["warm"]),
    ]], colWidths=[39 * mm, doc.width - 39 * mm])
    recognition.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), GREEN),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EEF8F3")),
        ("BOX", (0, 0), (-1, -1), .7, colors.HexColor("#8DB9A6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [result, Spacer(1, 3 * mm), recognition, Spacer(1, 5 * mm), Paragraph("Customer Journey", styles["section"])]

    journey = Table(
        [[journey_card(stage, styles) for stage in stages]],
        colWidths=[doc.width / 5] * 5,
    )
    journey.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [journey, Spacer(1, 5 * mm), Paragraph(f"Ruta de mejora ({len(opportunities)})", styles["section"])]
    story.append(Paragraph("Cada oportunidad conserva el acuerdo registrado para corregir, asignar y volver a validar.", styles["warm"]))
    story.append(Spacer(1, 2 * mm))

    if not opportunities:
        story.append(Paragraph("No se registraron puntos NO CUMPLE. Celebra el resultado, mantén el estándar y reconoce al equipo.", styles["body"]))
    else:
        opportunity_rows = [["#", "Momento y punto", "Corrige ahora", "Acuerdo y cierre"]]
        for number, answer in enumerate(opportunities, start=1):
            stage_label = safe_text(answer.get("journeyStageTitle") or answer.get("sectionTitle"), 30)
            agreement = safe_text(answer.get("comment"), 120)
            opportunity_rows.append([
                str(number),
                Paragraph(f"<font color='#006241'><b>{stage_label}</b></font><br/><b>{safe_text(answer.get('title'), 70)}</b><br/><font color='#D94F1D'>{safe_text(answer.get('applies'), 25)}</font>", styles["small"]),
                Paragraph(safe_text(answer.get("suggestedAction"), 190), styles["small"]),
                Paragraph(f"<b>Acuerdo:</b> {agreement}<br/><br/><font color='#5F6F69'>Responsable: __________<br/>Fecha: ____ / ____</font>", styles["small"]),
            ])
        opportunities_table = Table(opportunity_rows, colWidths=[9 * mm, 43 * mm, 70 * mm, 55 * mm], repeatRows=1)
        opportunities_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ORANGE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), BOLD), ("FONTSIZE", (0, 0), (-1, -1), 7.3),
            ("ALIGN", (0, 0), (0, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF8F1")]),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D8CBB8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(opportunities_table)

    doc.build(story)


def main() -> None:
    args = parse_args()
    payload = load_payload(args.input)
    build_report(payload, args.output)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.output.name)
    print(f"Reporte generado: {args.output.parent / safe_name}")


if __name__ == "__main__":
    main()
