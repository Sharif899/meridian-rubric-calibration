"""Render docs/RUBRICS.md from the versioned rubric JSON files.

Run: python scripts/build_rubrics_doc.py
The generated document is the human-readable form of the same rubrics
the pipeline loads; the JSON files are the source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render(rubric: dict) -> list[str]:
    version = rubric["version"]
    lines = [f"# Rubric version {version}", ""]
    lines.append("Scale: 0-4 on each of five dimensions. The dimensions are never "
                 "combined into one general impression.")
    lines.append("")
    lines.append("## Verdict rule")
    lines.append("")
    rule = rubric["verdict_rule"]
    lines.append(f"- **Pass:** {rule['pass']}")
    lines.append(f"- **Failure:** {rule['failure']}")
    lines.append(f"- **Partial pass:** {rule['partial']}")
    lines.append("")
    lines.append(rule["note"])
    lines.append("")
    lines.append("## Dimensions and anchors")
    lines.append("")
    for dim in rubric["dimensions"]:
        lines.append(f"### {dim['name']} (`{dim['id']}`)")
        lines.append("")
        lines.append(dim["description"])
        lines.append("")
        for score in ("0", "1", "2", "3", "4"):
            lines.append(f"- **{score}:** {dim['anchors'][score]}")
        lines.append("")
    lines.append("## Grading guidance")
    lines.append("")
    for key, text in rubric["guidance"].items():
        lines.append(f"### {key.replace('_', ' ').title()}")
        lines.append("")
        lines.append(text)
        lines.append("")
    lines.append("## Failure labels")
    lines.append("")
    for label in rubric["failure_labels"]:
        lines.append(f"- **{label['id']}:** {label['definition']}")
    lines.append("")
    for area, entry in rubric["rubrics"].items():
        lines.append(f"## {entry['name']}")
        lines.append("")
        lines.append("### Source evidence a grader must check")
        lines.append("")
        for req in entry["evidence_required"]:
            lines.append(f"- {req}")
        lines.append("")
        lines.append("### Worked examples")
        lines.append("")
        for ex in entry["examples"]:
            lines.append(f"#### Score level {ex['level']}: {ex['title']}")
            lines.append("")
            lines.append(f"> {ex['response']}")
            lines.append("")
            scores = ", ".join(f"{k} {v}" for k, v in ex["scores"].items())
            lines.append(f"Scores: {scores}.")
            lines.append("")
            lines.append(ex["note"])
            lines.append("")
    return lines


def main() -> None:
    out: list[str] = [
        "# Meridian rubrics",
        "",
        "Three rubrics, one per task area, on a consistent 0-4 scale across "
        "five separate dimensions: factual accuracy, evidence use, instruction "
        "following, completeness, and safety.",
        "",
        "Two versions exist. Version 1.0.0 is the original rubric the pilot "
        "ran under. Version 1.1.0 is the revision after the pilot disagreement "
        "analysis; see docs/RUBRIC_CHANGELOG.md for exactly what changed and why. "
        "The machine-readable form is data/rubrics/v1.0.0.json and "
        "data/rubrics/v1.1.0.json; this document is generated from those files.",
        "",
    ]
    for version in ("1.0.0", "1.1.0"):
        rubric = json.loads((ROOT / "data" / "rubrics" / f"v{version}.json").read_text())
        out.extend(render(rubric))
    path = ROOT / "docs" / "RUBRICS.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
