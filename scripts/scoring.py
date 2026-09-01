"""Reglas únicas de evaluación para web, pruebas y reporte PDF."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


VALID_STATUSES = {"cumple", "no_cumple", "na"}


def calculate_counts(answers: Iterable[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(answer.get("status") for answer in answers)
    return {
        "cumple": counter["cumple"],
        "no_cumple": counter["no_cumple"],
        "na": counter["na"],
        "respondidas": sum(counter[status] for status in VALID_STATUSES),
    }


def calculate_score(counts: dict[str, int]) -> float | None:
    ponderadas = counts.get("cumple", 0) + counts.get("no_cumple", 0)
    if ponderadas == 0:
        return None
    return round(counts.get("cumple", 0) / ponderadas * 100, 1)


def classify_score(score: float | None) -> tuple[str, str]:
    if score is None:
        return "Sin calificación", "Completa al menos un punto ponderable."
    if score >= 90:
        return "Arranque consistente", "Mantén el estándar y cierra los hallazgos puntuales."
    if score >= 75:
        return "Requiere seguimiento", "Corrige las oportunidades prioritarias antes del siguiente turno."
    return "Atención prioritaria", "Define responsables y corrige de inmediato los puntos no cumplidos."


def build_section_summary(answers: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    titles: dict[str, str] = {}
    for answer in answers:
        section_id = str(answer.get("sectionId") or "sin_seccion")
        grouped.setdefault(section_id, []).append(answer)
        titles[section_id] = str(answer.get("sectionTitle") or section_id)
    result = []
    for section_id, section_answers in grouped.items():
        counts = calculate_counts(section_answers)
        result.append({
            "id": section_id,
            "title": titles[section_id],
            "score": calculate_score(counts),
            "counts": counts,
        })
    return result


def validate_answers(answers: Iterable[dict[str, Any]]) -> None:
    for index, answer in enumerate(answers, start=1):
        status = answer.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"Respuesta {index}: estado no válido: {status!r}.")
        if status == "no_cumple" and not str(answer.get("comment") or "").strip():
            raise ValueError(f"Respuesta {index}: No cumple requiere comentario.")
