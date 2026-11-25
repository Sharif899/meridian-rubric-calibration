"""Agreement and calibration analysis.

All metrics are computed from the completed pilot run in the store and
always report their sample size. Nothing here is averaged away: the
report shows exact agreement and kappa per dimension, pass/fail kappa,
failure-label agreement, and the LLM grader's difference from the
adjudicated human score, each with its N.

Cohen's kappa and linear-weighted kappa are implemented from scratch
(no third-party statistics dependency).
"""

from __future__ import annotations

from collections import Counter

from .graders import GRADER_1, GRADER_2, score_human
from .providers import is_refusal_item
from .rubric import DIMENSION_IDS, verdict


def cohens_kappa(a: list, b: list, categories: list) -> float | None:
    """Unweighted Cohen's kappa. Returns None when it is undefined
    (no variation in the ratings)."""
    n = len(a)
    if n == 0:
        return None
    index = {c: i for i, c in enumerate(categories)}
    table = [[0] * len(categories) for _ in categories]
    for x, y in zip(a, b):
        table[index[x]][index[y]] += 1
    po = sum(table[i][i] for i in range(len(categories))) / n
    pe = 0.0
    for i in range(len(categories)):
        pe += (sum(table[i]) / n) * (sum(table[j][i] for j in range(len(categories))) / n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def weighted_kappa(a: list[int], b: list[int], categories: list[int]) -> float | None:
    """Linear-weighted Cohen's kappa for ordered categories."""
    n = len(a)
    if n == 0:
        return None
    k = len(categories)
    index = {c: i for i, c in enumerate(categories)}
    table = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        table[index[x]][index[y]] += 1
    weights = [[1 - abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]
    po = sum(weights[i][j] * table[i][j] for i in range(k) for j in range(k)) / n
    pe = 0.0
    for i in range(k):
        for j in range(k):
            pe += weights[i][j] * (sum(table[i]) / n) * (sum(table[m][j] for m in range(k)) / n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def _exact_agreement(a: list, b: list) -> float:
    return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else 0.0


def item_positions(items: list[dict]) -> dict[str, int]:
    """Global position of each item in the sorted pilot list (0-119)."""
    return {item["id"]: n for n, item in enumerate(sorted(items, key=lambda it: it["id"]))}


def analyze(store, rubric_version: str) -> dict:
    """Compute the full agreement and calibration analysis for one rubric version."""
    g1 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_1, rubric_version=rubric_version)}
    g2 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_2, rubric_version=rubric_version)}
    llm = {s["blinded_id"]: s for s in store.llm_scores(rubric_version=rubric_version)}
    adjudicated = {a["blinded_id"]: a for a in store.adjudications()}
    responses = {r["blinded_id"]: r for r in store.responses()}
    items = {it["id"]: it for it in store.items()}

    double_ids = sorted(set(g1) & set(g2))
    result: dict = {
        "rubric_version": rubric_version,
        "n_double_graded_responses": len(double_ids),
        "n_single_graded_responses": len(set(g1) - set(g2)),
        "n_llm_graded_responses": len(llm),
        "n_adjudicated_responses": len(adjudicated),
    }

    # -- per-dimension agreement on double-graded responses --------------
    per_dimension: dict[str, dict] = {}
    pooled_a: list[int] = []
    pooled_b: list[int] = []
    for dim in DIMENSION_IDS:
        a = [g1[r][ "scores"][dim] for r in double_ids]
        b = [g2[r]["scores"][dim] for r in double_ids]
        pooled_a.extend(a)
        pooled_b.extend(b)
        per_dimension[dim] = {
            "n": len(double_ids),
            "exact_agreement": _exact_agreement(a, b),
            "weighted_kappa": weighted_kappa(a, b, [0, 1, 2, 3, 4]),
        }
    result["per_dimension"] = per_dimension
    result["overall"] = {
        "n_pairs": len(pooled_a),
        "exact_agreement": _exact_agreement(pooled_a, pooled_b),
        "weighted_kappa": weighted_kappa(pooled_a, pooled_b, [0, 1, 2, 3, 4]),
    }

    # -- pass/fail kappa (pass vs not-pass) -------------------------------
    a_pass = [verdict(g1[r]["scores"]) == "pass" for r in double_ids]
    b_pass = [verdict(g2[r]["scores"]) == "pass" for r in double_ids]
    result["pass_fail"] = {
        "n": len(double_ids),
        "exact_agreement": _exact_agreement(a_pass, b_pass),
        "kappa": cohens_kappa(a_pass, b_pass, [True, False]),
        "grader1_pass_count": sum(a_pass),
        "grader2_pass_count": sum(b_pass),
    }

    # -- failure-label agreement ------------------------------------------
    a_labels = [g1[r]["failure_label"] for r in double_ids]
    b_labels = [g2[r]["failure_label"] for r in double_ids]
    label_categories = sorted(set(a_labels) | set(b_labels))
    result["failure_labels"] = {
        "n": len(double_ids),
        "exact_agreement": _exact_agreement(a_labels, b_labels),
        "kappa": cohens_kappa(a_labels, b_labels, label_categories),
        "categories": label_categories,
        "disagreements": [
            {"blinded_id": r, "grader1": g1[r]["failure_label"], "grader2": g2[r]["failure_label"]}
            for r in double_ids
            if g1[r]["failure_label"] != g2[r]["failure_label"]
        ],
    }

    # -- disagreement examples --------------------------------------------
    examples = []
    for r in double_ids:
        differing = [d for d in DIMENSION_IDS if g1[r]["scores"][d] != g2[r]["scores"][d]]
        if differing:
            examples.append({
                "blinded_id": r,
                "item_id": responses[r]["item_id"],
                "area": items[responses[r]["item_id"]]["area"],
                "ambiguous": items[responses[r]["item_id"]]["ambiguous"],
                "differing_dimensions": differing,
                "grader1_scores": g1[r]["scores"],
                "grader2_scores": g2[r]["scores"],
                "grader1_label": g1[r]["failure_label"],
                "grader2_label": g2[r]["failure_label"],
                "adjudicated_scores": adjudicated[r]["adjudicated_scores"] if r in adjudicated else None,
            })
    result["disagreement_examples"] = examples
    result["n_disagreements"] = len(examples)

    # -- LLM grader vs adjudicated human score ----------------------------
    common = sorted(set(llm) & set(adjudicated))
    llm_rows: dict[str, dict] = {"n_responses": len(common), "n_pairs": 0, "diff_gt_1": 0,
                                  "mean_abs_diff": 0.0, "per_dimension": {}}
    total_abs = 0
    total_pairs = 0
    for dim in DIMENSION_IDS:
        diffs = [abs(llm[r]["scores"][dim] - adjudicated[r]["adjudicated_scores"][dim]) for r in common]
        gt1 = sum(1 for d in diffs if d > 1)
        llm_rows["per_dimension"][dim] = {
            "n": len(diffs),
            "mean_abs_diff": sum(diffs) / len(diffs) if diffs else 0.0,
            "diff_gt_1": gt1,
            "diff_gt_1_rate": gt1 / len(diffs) if diffs else 0.0,
        }
        total_abs += sum(diffs)
        total_pairs += len(diffs)
        llm_rows["diff_gt_1"] += gt1
    llm_rows["n_pairs"] = total_pairs
    llm_rows["diff_gt_1_rate"] = llm_rows["diff_gt_1"] / total_pairs if total_pairs else 0.0
    llm_rows["mean_abs_diff"] = total_abs / total_pairs if total_pairs else 0.0
    result["llm_vs_adjudicated"] = llm_rows

    # -- distributions and pass rates (adjudicated) -----------------------
    by_area: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    for area in ("customer_support", "technical_troubleshooting", "research"):
        rows = [a for a in adjudicated.values()
                if items[responses[a["blinded_id"]]["item_id"]]["area"] == area]
        by_area[area] = _summarise(rows)
    for model in ("model-a", "model-b"):
        rows = [a for a in adjudicated.values() if responses[a["blinded_id"]]["model"] == model]
        by_model[model] = _summarise(rows)
    result["by_area"] = by_area
    result["by_model"] = by_model
    result["overall_adjudicated"] = _summarise(list(adjudicated.values()))

    # -- score distributions per dimension (adjudicated) ------------------
    distributions: dict[str, dict] = {}
    for dim in DIMENSION_IDS:
        counts = Counter(a["adjudicated_scores"][dim] for a in adjudicated.values())
        distributions[dim] = {str(s): counts.get(s, 0) for s in (0, 1, 2, 3, 4)}
    result["score_distributions"] = distributions

    # -- failure counts by adjudicated label ------------------------------
    result["failure_counts"] = dict(Counter(a["failure_label"] for a in adjudicated.values()))
    return result


def _summarise(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "pass_rate": 0.0, "partial_rate": 0.0, "failure_rate": 0.0,
                "mean_score": 0.0, "verdicts": {}}
    verdicts = Counter(verdict(r["adjudicated_scores"]) for r in rows)
    means = [sum(r["adjudicated_scores"].values()) / 5 for r in rows]
    return {
        "n": n,
        "pass_rate": verdicts.get("pass", 0) / n,
        "partial_rate": verdicts.get("partial", 0) / n,
        "failure_rate": verdicts.get("failure", 0) / n,
        "mean_score": sum(means) / n,
        "verdicts": dict(verdicts),
    }


def revision_impact(store, from_version: str = "1.0.0", to_version: str = "1.1.0") -> dict:
    """What the rubric revision changes, measured by re-scoring.

    The same double-graded responses are re-scored under both versions
    with both graders' rules, and every response is re-scored under both
    versions with grader-1's rules to count verdict flips. This is a
    re-score of the completed pilot, not a second pilot, and the report
    says so.
    """
    items = {it["id"]: it for it in store.items()}
    responses = store.responses()
    g1 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_1, rubric_version=from_version)}
    g2 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_2, rubric_version=from_version)}
    double_ids = sorted(set(g1) & set(g2))
    responses_by_id = {r["blinded_id"]: r for r in responses}

    def agreement(version: str) -> dict:
        per_dim = {}
        pooled_a: list[int] = []
        pooled_b: list[int] = []
        for dim in DIMENSION_IDS:
            a = [score_human(responses_by_id[r]["defect_profile"], items[responses_by_id[r]["item_id"]], version, GRADER_1)[dim] for r in double_ids]
            b = [score_human(responses_by_id[r]["defect_profile"], items[responses_by_id[r]["item_id"]], version, GRADER_2)[dim] for r in double_ids]
            pooled_a.extend(a)
            pooled_b.extend(b)
            per_dim[dim] = {
                "exact_agreement": _exact_agreement(a, b),
                "weighted_kappa": weighted_kappa(a, b, [0, 1, 2, 3, 4]),
            }
        return {
            "n": len(double_ids),
            "per_dimension": per_dim,
            "overall_exact_agreement": _exact_agreement(pooled_a, pooled_b),
            "overall_weighted_kappa": weighted_kappa(pooled_a, pooled_b, [0, 1, 2, 3, 4]),
        }

    before = agreement(from_version)
    after = agreement(to_version)

    # Verdict flips across all responses, grader-1 scoring.
    flips: list[dict] = []
    refusal_flips = 0
    for r in responses:
        item = items[r["item_id"]]
        s_from = score_human(r["defect_profile"], item, from_version, GRADER_1)
        s_to = score_human(r["defect_profile"], item, to_version, GRADER_1)
        v_from, v_to = verdict(s_from), verdict(s_to)
        if v_from != v_to:
            flips.append({
                "blinded_id": r["blinded_id"],
                "item_id": r["item_id"],
                "area": item["area"],
                "from": v_from,
                "to": v_to,
                "refusal": bool(r["defect_profile"]["refusal"] and r["defect_profile"]["refusal_correct"]),
            })
            if r["defect_profile"]["refusal"] and r["defect_profile"]["refusal_correct"]:
                refusal_flips += 1
    return {
        "from_version": from_version,
        "to_version": to_version,
        "before": before,
        "after": after,
        "n_verdict_flips": len(flips),
        "n_refusal_flips": refusal_flips,
        "flips": flips,
    }
