#!/usr/bin/env python3
"""Convierte el JSON exportado por la web en un reporte PDF ejecutivo."""

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
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from scoring import build_section_summary, calculate_counts, calculate_score, classify_score, validate_answers


GREEN = colors.HexColor("#006241")
DARK = colors.HexColor("#003B2D")
ORANGE = colors.HexColor("#D96F1D")
CREAM = colors.HexColor("#F7F1E7")
INK = colors.HexColor("#172B25")
MUTED = colors.HexColor("#5F6F69")
RED = colors.HexColor("#B42318")
LIGHT = colors.HexColor("#E9F2EE")
REGULAR = "DejaVu"
BOLD = "DejaVu-Bold"
FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON exportado por Validación Campaña.")
    parser.add_argument("--output", type=Path, required=True, help="Ruta del PDF de salida.")
    return parser.parse_args()


def safe_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(DARK)
    canvas.rect(0, height - 17 * mm, width, 17 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 8)
    canvas.drawString(18 * mm, height - 10.7 * mm, "VALIDACIÓN CAMPAÑA · FALL 26")
    canvas.setFont(REGULAR, 7)
    canvas.drawRightString(width - 18 * mm, height - 10.7 * mm, "USO INTERNO · INFORMACIÓN PRIVADA")
    canvas.setStrokeColor(colors.HexColor("#D8E3DE"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 7)
    canvas.drawString(18 * mm, 9 * mm, "JUNTÉMONOS MÁS · Corrige cada NO CUMPLE con responsable y fecha.")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=BOLD, fontSize=23, leading=26, textColor=DARK, alignment=TA_LEFT, spaceAfter=5),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName=REGULAR, fontSize=9, leading=13, textColor=MUTED, spaceAfter=10),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=15, textColor=GREEN, spaceBefore=5, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName=REGULAR, fontSize=8.4, leading=11, textColor=INK),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName=REGULAR, fontSize=7.2, leading=9.2, textColor=MUTED),
        "kpi": ParagraphStyle("Kpi", parent=base["Normal"], fontName=BOLD, fontSize=20, leading=22, textColor=DARK, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("KpiLabel", parent=base["Normal"], fontName=BOLD, fontSize=7, leading=8, textColor=MUTED, alignment=TA_CENTER),
        "white": ParagraphStyle("White", parent=base["Normal"], fontName=BOLD, fontSize=10, leading=12, textColor=colors.white, alignment=TA_CENTER),
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


def build_report(payload: dict[str, Any], output_path: Path) -> None:
    answers = payload["answers"]
    counts = calculate_counts(answers)
    score = calculate_score(counts)
    label, message = classify_score(score)
    sections = payload.get("sections") or payload.get("summary", {}).get("sections") or build_section_summary(answers)
    opportunities = [answer for answer in answers if answer.get("status") == "no_cumple"]
    styles = build_styles()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output_path), pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=23 * mm, bottomMargin=16 * mm, title="Validación Campaña Fall 26",
        author="Validación Campaña",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=header_footer)])

    story = [
        Paragraph("Resultado de tienda", styles["title"]),
        Paragraph("Resumen ejecutivo del recorrido operativo Fall 26.", styles["subtitle"]),
    ]
    identity = Table([
        [Paragraph("<b>Tienda</b><br/>" + safe_text(payload.get("store"), 80), styles["body"]),
         Paragraph("<b>Quién validó</b><br/>" + safe_text(payload.get("validator"), 80), styles["body"]),
         Paragraph("<b>Cierre</b><br/>" + parse_date(payload.get("completedAt")), styles["body"])],
    ], colWidths=[doc.width * .36, doc.width * .36, doc.width * .28])
    identity.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), .6, colors.HexColor("#BCD2C8")),
        ("INNERGRID", (0, 0), (-1, -1), .4, colors.HexColor("#BCD2C8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [identity, Spacer(1, 7 * mm)]

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
    story += [result, Spacer(1, 5 * mm), Paragraph("Resultado por bloque", styles["section"])]

    section_rows = [["Bloque", "Cumple", "No cumple", "N/A", "Resultado"]]
    for section in sections:
        scounts = section.get("counts") or {
            "cumple": section.get("pass", 0),
            "no_cumple": section.get("fail", 0),
            "na": section.get("na", 0),
        }
        sscore = section.get("score")
        section_rows.append([
            safe_text(section.get("title"), 60), str(scounts.get("cumple", 0)), str(scounts.get("no_cumple", 0)),
            str(scounts.get("na", 0)), "-" if sscore is None else f"{float(sscore):.1f}%",
        ])
    section_table = Table(section_rows, colWidths=[82 * mm, 24 * mm, 26 * mm, 18 * mm, 27 * mm], repeatRows=1)
    section_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), BOLD), ("FONTNAME", (0, 1), (-1, -1), REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F5")]),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#C8D4CF")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story += [section_table, Spacer(1, 6 * mm), Paragraph(f"Oportunidades ({len(opportunities)})", styles["section"])]

    if not opportunities:
        story.append(Paragraph("No se registraron puntos NO CUMPLE. Mantén el estándar y comparte el resultado con el equipo.", styles["body"]))
    else:
        opportunity_rows = [["#", "Punto", "Aplica", "Comentario / acción"]]
        for number, answer in enumerate(opportunities, start=1):
            opportunity_rows.append([
                str(number), Paragraph(f"<b>{safe_text(answer.get('title'), 70)}</b><br/><font color='#5F6F69'>{safe_text(answer.get('question'), 150)}</font>", styles["small"]),
                safe_text(answer.get("applies"), 25), Paragraph(safe_text(answer.get("comment"), 120), styles["small"]),
            ])
        opportunities_table = Table(opportunity_rows, colWidths=[10 * mm, 82 * mm, 25 * mm, 60 * mm], repeatRows=1)
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

    story += [Spacer(1, 2 * mm), KeepTogether([
        Paragraph("Regla de evaluación", styles["section"]),
        Paragraph("Cumple = 1 · No cumple = 0 · No aplica queda fuera del cálculo. Tasa de éxito = Cumple / (Cumple + No cumple) x 100.", styles["body"]),
        Spacer(1, 2 * mm),
        Paragraph("Este reporte contiene información privada de la compañía. Uso exclusivo para validación operativa; está prohibida su divulgación.", styles["small"]),
    ])]
    doc.build(story)


def main() -> None:
    args = parse_args()
    payload = load_payload(args.input)
    build_report(payload, args.output)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.output.name)
    print(f"Reporte generado: {args.output.parent / safe_name}")


if __name__ == "__main__":
    main()
