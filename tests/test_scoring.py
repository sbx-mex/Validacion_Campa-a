from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scoring import build_section_summary, calculate_counts, calculate_score, classify_score, validate_answers  # noqa: E402


class ScoringTests(unittest.TestCase):
    def test_na_does_not_affect_score(self):
        answers = [
            {"status": "cumple"}, {"status": "cumple"}, {"status": "cumple"},
            {"status": "no_cumple", "comment": "Corregir"}, {"status": "na"}, {"status": "na"},
        ]
        counts = calculate_counts(answers)
        self.assertEqual(counts, {"cumple": 3, "no_cumple": 1, "na": 2, "respondidas": 6})
        self.assertEqual(calculate_score(counts), 75.0)

    def test_all_na_returns_no_score(self):
        self.assertIsNone(calculate_score(calculate_counts([{"status": "na"}] * 4)))

    def test_no_cumple_requires_comment(self):
        with self.assertRaisesRegex(ValueError, "requiere comentario"):
            validate_answers([{"status": "no_cumple", "comment": ""}])

    def test_sections_keep_independent_scores(self):
        summary = build_section_summary([
            {"sectionId": "a", "sectionTitle": "A", "status": "cumple"},
            {"sectionId": "a", "sectionTitle": "A", "status": "na"},
            {"sectionId": "b", "sectionTitle": "B", "status": "no_cumple", "comment": "Acción"},
        ])
        self.assertEqual(summary[0]["score"], 100.0)
        self.assertEqual(summary[1]["score"], 0.0)

    def test_classification_boundaries(self):
        self.assertEqual(classify_score(90)[0], "Arranque consistente")
        self.assertEqual(classify_score(75)[0], "Requiere seguimiento")
        self.assertEqual(classify_score(74.9)[0], "Atención prioritaria")


if __name__ == "__main__":
    unittest.main()
