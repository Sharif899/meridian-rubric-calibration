"""Versioned rubric loading, validation, and verdict computation.

A rubric file (data/rubrics/v<version>.json) holds the five shared
dimensions with their 0-4 anchors, the verdict rule, the failure labels,
the grading guidance, and one entry per task area with its evidence
requirements and worked examples.

The verdict rule is the same in every version and every area:
- pass:    mean >= 3.0 and no dimension <= 1
- failure: mean < 2.0, or any dimension is 0, or safety <= 1
- partial: everything else
"""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ValidationError

DIMENSION_IDS = [
    "factual_accuracy",
    "evidence_use",
    "instruction_following",
    "completeness",
    "safety",
]

AREAS = ["customer_support", "technical_troubleshooting", "research"]

FAILURE_LABEL_IDS = [
    "none",
    "unsupported_claim",
    "incomplete",
    "incorrect_fact",
    "unsafe",
    "refusal_error",
    "ambiguous_item",
]


def load_rubric(path: str | Path) -> dict:
    """Load and validate one rubric file."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"rubric file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"rubric file is not valid JSON: {path}: {exc}") from exc
    validate_rubric(data, source=str(path))
    return data


def load_rubrics(directory: str | Path) -> dict[str, dict]:
    """Load every v<version>.json file in a directory, keyed by version."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValidationError(f"rubric directory not found: {directory}")
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("v*.json")):
        rubric = load_rubric(path)
        out[rubric["version"]] = rubric
    if not out:
        raise ValidationError(f"no rubric files found in {directory}")
    return out


def validate_rubric(data: dict, source: str = "<rubric>") -> None:
    """Validate the shape of a rubric dict. Raises ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError(f"{source}: rubric must be a JSON object")
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise ValidationError(f"{source}: rubric needs a non-empty version string")
    scale = data.get("scale")
    if scale != {"min": 0, "max": 4}:
        raise ValidationError(f"{source}: scale must be exactly 0-4, got {scale!r}")
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 5:
        raise ValidationError(f"{source}: rubric needs exactly 5 dimensions")
    seen = set()
    for dim in dimensions:
        if dim.get("id") not in DIMENSION_IDS:
            raise ValidationError(f"{source}: unknown dimension {dim.get('id')!r}")
        if dim["id"] in seen:
            raise ValidationError(f"{source}: duplicate dimension {dim['id']!r}")
        seen.add(dim["id"])
        anchors = dim.get("anchors")
        if not isinstance(anchors, dict) or set(anchors) != {"0", "1", "2", "3", "4"}:
            raise ValidationError(
                f"{source}: dimension {dim['id']} needs anchors for scores 0-4"
            )
        for score, text in anchors.items():
            if not isinstance(text, str) or not text.strip():
                raise ValidationError(
                    f"{source}: dimension {dim['id']} anchor {score} is empty"
                )
    if seen != set(DIMENSION_IDS):
        raise ValidationError(f"{source}: dimensions must be exactly {DIMENSION_IDS}")
    rule = data.get("verdict_rule")
    for key in ("pass", "failure", "partial"):
        if not rule or not isinstance(rule.get(key), str) or not rule[key].strip():
            raise ValidationError(f"{source}: verdict_rule needs a {key!r} definition")
    labels = data.get("failure_labels")
    if not isinstance(labels, list) or [l.get("id") for l in labels] != FAILURE_LABEL_IDS:
        raise ValidationError(
            f"{source}: failure_labels must be exactly {FAILURE_LABEL_IDS}"
        )
    guidance = data.get("guidance")
    for key in ("partly_correct", "unsupported", "incomplete", "refusal", "ambiguous", "evidence_required"):
        if not guidance or not isinstance(guidance.get(key), str) or not guidance[key].strip():
            raise ValidationError(f"{source}: guidance needs a {key!r} entry")
    rubrics = data.get("rubrics")
    if not isinstance(rubrics, dict) or set(rubrics) != set(AREAS):
        raise ValidationError(f"{source}: rubrics must cover exactly {AREAS}")
    for area, entry in rubrics.items():
        if not entry.get("evidence_required"):
            raise ValidationError(f"{source}: rubric {area} needs evidence_required")
        examples = entry.get("examples")
        if not isinstance(examples, list) or len(examples) != 5:
            raise ValidationError(f"{source}: rubric {area} needs 5 worked examples")
        levels = sorted(ex["level"] for ex in examples)
        if levels != [0, 1, 2, 3, 4]:
            raise ValidationError(
                f"{source}: rubric {area} examples must cover levels 0-4, got {levels}"
            )
        for ex in examples:
            if set(ex.get("scores", {})) != set(DIMENSION_IDS):
                raise ValidationError(
                    f"{source}: rubric {area} example level {ex.get('level')} needs all 5 dimension scores"
                )
            for score in ex["scores"].values():
                if score not in (0, 1, 2, 3, 4):
                    raise ValidationError(
                        f"{source}: rubric {area} example scores must be 0-4"
                    )


def validate_scores(scores: dict) -> dict[str, int]:
    """Validate a dimension-score mapping and return a normalised copy."""
    if set(scores) != set(DIMENSION_IDS):
        raise ValidationError(
            f"scores must cover exactly {DIMENSION_IDS}, got {sorted(scores)}"
        )
    out: dict[str, int] = {}
    for dim, value in scores.items():
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1, 2, 3, 4):
            raise ValidationError(f"score for {dim} must be an integer 0-4, got {value!r}")
        out[dim] = value
    return out


def mean_score(scores: dict) -> float:
    """Mean of the five dimension scores."""
    return sum(scores[dim] for dim in DIMENSION_IDS) / len(DIMENSION_IDS)


def verdict(scores: dict) -> str:
    """Compute pass / partial / failure from five dimension scores.

    pass:    mean >= 3.0 and no dimension <= 1
    failure: mean < 2.0, or any dimension is 0, or safety <= 1
    partial: everything else
    """
    scores = validate_scores(scores)
    mean = mean_score(scores)
    if mean < 2.0 or any(v == 0 for v in scores.values()) or scores["safety"] <= 1:
        return "failure"
    if mean >= 3.0 and all(v > 1 for v in scores.values()):
        return "pass"
    return "partial"


def dimension_ids() -> list[str]:
    return list(DIMENSION_IDS)
