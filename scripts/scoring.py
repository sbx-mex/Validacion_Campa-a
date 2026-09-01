"""Reglas únicas de evaluación para web, pruebas y reporte PDF."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


VALID_STATUSES = {"cumple", "no_cumple", "na"}
EXPECTED_VALUES = {"cumple": 1, "no_cumple": 0, "na": None}


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
        return "Arranque consistente", "¡Gran trabajo! Reconoce al equipo y cierra las oportunidades puntuales."
    if score >= 75:
        return "Vamos bien", "Celebra los puntos a favor y completa las correcciones antes del siguiente turno."
    return "Enfoque inmediato", "Atiende primero las correcciones sugeridas y vuelve a validar los puntos prioritarios."


def build_execution_insights(
    answers: Iterable[dict[str, Any]], corrective_actions: dict[str, str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Separa fortalezas y oportunidades, agregando una acción concreta a cada No cumple."""
    action_map = corrective_actions or {}
    strengths: list[dict[str, Any]] = []
    opportunities: list[dict[str, Any]] = []
    for answer in answers:
        if answer.get("status") == "cumple":
            strengths.append(answer)
        elif answer.get("status") == "no_cumple":
            enriched = dict(answer)
            enriched["suggestedAction"] = str(
                answer.get("suggestedAction")
                or action_map.get(str(answer.get("id") or ""))
                or answer.get("criterion")
                or "Corrige el estándar y vuelve a validar."
            )
            opportunities.append(enriched)
    return {"strengths": strengths, "opportunities": opportunities}


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
    seen_ids: set[str] = set()
    for index, answer in enumerate(answers, start=1):
        status = answer.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"Respuesta {index}: estado no válido: {status!r}.")
        answer_id = str(answer.get("id") or "")
        if answer_id:
            if answer_id in seen_ids:
                raise ValueError(f"Respuesta {index}: ID duplicado: {answer_id}.")
            seen_ids.add(answer_id)
        if "value" in answer and answer.get("value") != EXPECTED_VALUES[status]:
            raise ValueError(f"Respuesta {index}: valor incompatible con {status}.")
        if status == "no_cumple" and not str(answer.get("comment") or "").strip():
            raise ValueError(f"Respuesta {index}: No cumple requiere comentario.")
        if len(str(answer.get("comment") or "")) > 120:
            raise ValueError(f"Respuesta {index}: comentario mayor a 120 caracteres.")
