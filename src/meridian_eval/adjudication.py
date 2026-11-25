"""Adjudication of human-grader disagreements.

Every double-graded response gets an adjudication record. Where the two
graders agreed, the adjudicated score is that score. Where they
disagreed, the adjudicator applies the clarified rubric (v1.1.0) to the
points the pilot showed were unclear, and the stricter reading
elsewhere, and records the decision and the rubric clause applied.
Single-graded responses carry the single human score as the adjudicated
score; there is nothing to adjudicate.

Adjudicated human scores are the reference for calibration. The LLM
grader's scores are never used as ground truth.
"""

from __future__ import annotations

from .graders import GRADER_1, GRADER_2, failure_label
from .rubric import DIMENSION_IDS, verdict

_LABEL_SEVERITY = {
    "unsafe": 0,
    "incorrect_fact": 1,
    "unsupported_claim": 2,
    "incomplete": 3,
    "refusal_error": 4,
    "ambiguous_item": 5,
    "none": 6,
}


def _stricter_mean(a: int, b: int) -> int:
    """Mean of two scores rounded down (toward the stricter grader)."""
    return (a + b) // 2


def adjudicate_pair(g1_scores: dict | None, g1_label: str | None,
                    g2_scores: dict | None, g2_label: str | None,
                    profile: dict, item: dict) -> dict:
    """Adjudicate one response. Returns the adjudication record fields."""
    if g1_scores is None and g2_scores is None:
        raise ValueError("cannot adjudicate a response with no human scores")
    if g2_scores is None:
        return {
            "adjudicated_scores": dict(g1_scores),
            "failure_label": g1_label,
            "decision": "single",
            "rationale": "Single-graded by grader-1; no second grader to adjudicate against.",
        }
    if g1_scores == g2_scores and g1_label == g2_label:
        return {
            "adjudicated_scores": dict(g1_scores),
            "failure_label": g1_label,
            "decision": "agreed",
            "rationale": "Graders agreed on all five dimensions and on the failure label.",
        }
    adjudicated: dict[str, int] = {}
    clauses: list[str] = []
    for dim in DIMENSION_IDS:
        a, b = g1_scores[dim], g2_scores[dim]
        if a == b:
            adjudicated[dim] = a
            continue
        if dim == "factual_accuracy" and profile["wrong_core_fact"]:
            adjudicated[dim] = 1
            clauses.append(
                "factual accuracy: v1.1.0 partly-correct guidance — an error in the "
                "core claim caps the score at 1"
            )
        elif dim == "evidence_use" and profile["cites_related_not_governing"]:
            adjudicated[dim] = 2
            clauses.append(
                "evidence use: v1.1.0 anchor 2 — citing a related source instead of "
                "the governing source scores 2"
            )
        else:
            adjudicated[dim] = _stricter_mean(a, b)
            clauses.append(
                f"{dim}: graders split {a} vs {b}; no clarified rule resolves it, "
                "so the adjudicator took the stricter reading (mean rounded down)"
            )
    if g1_label == g2_label:
        label = g1_label
    elif item["ambiguous"] and {"ambiguous_item", "none"} == {g1_label, g2_label}:
        label = "ambiguous_item"
        clauses.append(
            "failure label: the item is flagged ambiguous in the pilot data, "
            "so the label records the item, not the response"
        )
    else:
        label = min((g1_label, g2_label), key=lambda l: _LABEL_SEVERITY[l])
        clauses.append(f"failure label: took the more severe label ({label})")
    return {
        "adjudicated_scores": adjudicated,
        "failure_label": label,
        "decision": "adjudicated",
        "rationale": " ".join(clauses),
    }


def adjudication_summary(adjudications: list[dict]) -> dict:
    """Counts of agreed / adjudicated / single records."""
    counts = {"agreed": 0, "adjudicated": 0, "single": 0}
    for adj in adjudications:
        counts[adj["decision"]] += 1
    return counts


__all__ = ["adjudicate_pair", "adjudication_summary", "GRADER_1", "GRADER_2", "verdict", "failure_label"]
