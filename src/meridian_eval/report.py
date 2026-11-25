"""Report rendering: Markdown + JSON exports of the analysis.

The Markdown report is the analysis report. Every number in it comes
from the completed pilot run in the store; the human judgments, the
LLM-grader scores, and the adjudicated labels are kept in separate
sections, and every metric reports its sample size.
"""

from __future__ import annotations

import json

from .rubric import DIMENSION_IDS


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _kappa(value: float | None) -> str:
    if value is None:
        return "undefined (no variation in the ratings)"
    return f"{value:.3f}"


def render_markdown(analysis: dict, revision: dict, meta: dict) -> str:
    a = analysis
    lines: list[str] = []
    lines.append("# Meridian pilot analysis report")
    lines.append("")
    lines.append(
        f"Rubric version graded under: {a['rubric_version']}. "
        f"Pilot: {meta.get('n_items', 120)} items "
        f"({meta.get('items_per_area', 40)} per task area). "
        f"Responses: {meta.get('n_responses', 240)} blinded responses "
        f"(2 models x 120 items). "
        f"Double-graded responses: {a['n_double_graded_responses']} "
        f"(both human graders, blinded). "
        f"Single-graded responses: {a['n_single_graded_responses']}. "
        f"LLM-grader responses: {a['n_llm_graded_responses']}."
    )
    lines.append("")
    lines.append(
        "Human judgments, LLM-grader scores, and adjudicated labels are "
        "reported separately throughout. Adjudicated human scores are the "
        "reference for calibration; the LLM grader's scores are never "
        "treated as ground truth."
    )
    lines.append("")
    lines.append("## 1. Human-grader agreement (double-graded responses)")
    lines.append("")
    lines.append(
        f"Sample: N = {a['n_double_graded_responses']} double-graded responses, "
        f"each scored on 5 dimensions, so N = {a['overall']['n_pairs']} dimension pairs."
    )
    lines.append("")
    lines.append("| Dimension | N | Exact agreement | Weighted kappa |")
    lines.append("| --- | ---: | ---: | ---: |")
    for dim in DIMENSION_IDS:
        row = a["per_dimension"][dim]
        lines.append(
            f"| {dim} | {row['n']} | {_pct(row['exact_agreement'])} | {_kappa(row['weighted_kappa'])} |"
        )
    lines.append(
        f"| **Overall (pooled)** | {a['overall']['n_pairs']} | "
        f"**{_pct(a['overall']['exact_agreement'])}** | **{_kappa(a['overall']['weighted_kappa'])}** |"
    )
    lines.append("")
    lines.append("## 2. Pass/fail agreement")
    lines.append("")
    pf = a["pass_fail"]
    lines.append(
        f"Pass means the verdict is pass; not-pass means partial or failure. "
        f"N = {pf['n']} double-graded responses. Exact agreement "
        f"{_pct(pf['exact_agreement'])}, Cohen's kappa {_kappa(pf['kappa'])}. "
        f"Grader-1 passed {pf['grader1_pass_count']} responses; "
        f"grader-2 passed {pf['grader2_pass_count']}."
    )
    lines.append("")
    lines.append("## 3. Failure-label agreement")
    lines.append("")
    fl = a["failure_labels"]
    lines.append(
        f"N = {fl['n']} double-graded responses. Exact agreement "
        f"{_pct(fl['exact_agreement'])}, Cohen's kappa {_kappa(fl['kappa'])}. "
        f"Labels seen: {', '.join(fl['categories'])}."
    )
    if fl["disagreements"]:
        lines.append("")
        lines.append("Label disagreements:")
        lines.append("")
        for d in fl["disagreements"]:
            lines.append(
                f"- {d['blinded_id']}: grader-1 {d['grader1']}, grader-2 {d['grader2']}"
            )
    lines.append("")
    lines.append("## 4. LLM grader vs adjudicated human score")
    lines.append("")
    llm = a["llm_vs_adjudicated"]
    lines.append(
        f"N = {llm['n_responses']} responses x 5 dimensions = {llm['n_pairs']} pairs. "
        f"Mean absolute difference {llm['mean_abs_diff']:.2f} points. "
        f"Pairs differing by more than 1 point: {llm['diff_gt_1']} "
        f"({_pct(llm['diff_gt_1_rate'])})."
    )
    lines.append("")
    lines.append("| Dimension | N | Mean abs. diff | Diff > 1 pt |")
    lines.append("| --- | ---: | ---: | ---: |")
    for dim in DIMENSION_IDS:
        row = llm["per_dimension"][dim]
        lines.append(
            f"| {dim} | {row['n']} | {row['mean_abs_diff']:.2f} | "
            f"{row['diff_gt_1']} ({_pct(row['diff_gt_1_rate'])}) |"
        )
    lines.append("")
    lines.append("## 5. Pass rates and mean scores (adjudicated)")
    lines.append("")
    lines.append("| Slice | N | Mean score | Pass | Partial | Failure |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    overall = a["overall_adjudicated"]
    lines.append(
        f"| Overall | {overall['n']} | {overall['mean_score']:.2f} | "
        f"{_pct(overall['pass_rate'])} | {_pct(overall['partial_rate'])} | {_pct(overall['failure_rate'])} |"
    )
    for area, row in a["by_area"].items():
        lines.append(
            f"| {area} | {row['n']} | {row['mean_score']:.2f} | "
            f"{_pct(row['pass_rate'])} | {_pct(row['partial_rate'])} | {_pct(row['failure_rate'])} |"
        )
    for model, row in a["by_model"].items():
        lines.append(
            f"| {model} | {row['n']} | {row['mean_score']:.2f} | "
            f"{_pct(row['pass_rate'])} | {_pct(row['partial_rate'])} | {_pct(row['failure_rate'])} |"
        )
    lines.append("")
    lines.append("## 6. Score distributions (adjudicated, counts of 0-4)")
    lines.append("")
    lines.append("| Dimension | 0 | 1 | 2 | 3 | 4 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for dim in DIMENSION_IDS:
        dist = a["score_distributions"][dim]
        lines.append(
            f"| {dim} | {dist['0']} | {dist['1']} | {dist['2']} | {dist['3']} | {dist['4']} |"
        )
    lines.append("")
    lines.append("## 7. Failure counts by adjudicated label")
    lines.append("")
    for label, count in sorted(a["failure_counts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- {label}: {count}")
    lines.append("")
    lines.append("## 8. Disagreements between the human graders")
    lines.append("")
    lines.append(
        f"{a['n_disagreements']} of {a['n_double_graded_responses']} double-graded "
        "responses had a disagreement on at least one dimension or on the failure label."
    )
    lines.append("")
    for ex in a["disagreement_examples"]:
        lines.append(
            f"- {ex['blinded_id']} (item {ex['item_id']}, {ex['area']}, "
            f"{'ambiguous' if ex['ambiguous'] else 'not flagged ambiguous'}): "
            f"differing dimensions {', '.join(ex['differing_dimensions'])}; "
            f"grader-1 {ex['grader1_scores']}, grader-2 {ex['grader2_scores']}, "
            f"adjudicated {ex['adjudicated_scores']}; "
            f"labels {ex['grader1_label']} vs {ex['grader2_label']}."
        )
    lines.append("")
    lines.append("## 9. What the rubric revision changes")
    lines.append("")
    lines.append(
        f"This section re-scores the completed pilot under rubric "
        f"{revision['from_version']} and rubric {revision['to_version']} with "
        "both graders' rules. It is a re-score of the same pilot, not a "
        "second pilot."
    )
    lines.append("")
    before, after = revision["before"], revision["after"]
    lines.append(
        f"Overall exact agreement: {_pct(before['overall_exact_agreement'])} "
        f"(v{revision['from_version']}) -> {_pct(after['overall_exact_agreement'])} "
        f"(v{revision['to_version']}), N = {before['n']} double-graded responses. "
        f"Overall weighted kappa: {_kappa(before['overall_weighted_kappa'])} -> "
        f"{_kappa(after['overall_weighted_kappa'])}."
    )
    lines.append("")
    lines.append("| Dimension | Exact agreement v1.0.0 | Exact agreement v1.1.0 | Weighted kappa v1.0.0 | Weighted kappa v1.1.0 |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for dim in DIMENSION_IDS:
        b, f = before["per_dimension"][dim], after["per_dimension"][dim]
        lines.append(
            f"| {dim} | {_pct(b['exact_agreement'])} | {_pct(f['exact_agreement'])} | "
            f"{_kappa(b['weighted_kappa'])} | {_kappa(f['weighted_kappa'])} |"
        )
    lines.append("")
    lines.append(
        f"Verdict flips across all {meta.get('n_responses', 240)} responses "
        f"(grader-1 scoring): {revision['n_verdict_flips']}. "
        f"Of those, {revision['n_refusal_flips']} are correct refusals that "
        f"failed under v{revision['from_version']} and pass under "
        f"v{revision['to_version']}."
    )
    for flip in revision["flips"]:
        lines.append(
            f"- {flip['blinded_id']} (item {flip['item_id']}, {flip['area']}): "
            f"{flip['from']} -> {flip['to']}"
            + (" (correct refusal)" if flip["refusal"] else "")
        )
    lines.append("")
    return "\n".join(lines)


def render_json(analysis: dict, revision: dict, meta: dict) -> dict:
    return {
        "meta": meta,
        "analysis": analysis,
        "revision_impact": revision,
    }


def dumps_json(payload: dict) -> str:
    return json.dumps(payload, indent=2) + "\n"
