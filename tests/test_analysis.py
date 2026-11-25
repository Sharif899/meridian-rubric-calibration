"""Agreement math: kappa on known cases, and the analysis outputs."""

import pytest

from meridian_eval.analysis import (
    analyze,
    cohens_kappa,
    revision_impact,
    weighted_kappa,
)


def test_cohens_kappa_perfect_agreement():
    assert cohens_kappa([1, 1, 2, 2], [1, 1, 2, 2], [1, 2]) == 1.0


def test_cohens_kappa_chance_agreement():
    # Two raters who agree exactly at the chance rate score 0.
    assert cohens_kappa([1, 1, 2, 2], [1, 2, 1, 2], [1, 2]) == 0.0


def test_cohens_kappa_known_value():
    # 100 items, both raters say yes 60 times, and they agree on 45 yes
    # and 25 no. po = 0.70, pe = 0.52, kappa = 0.375.
    a = [1] * 60 + [0] * 40
    b = [1] * 45 + [0] * 15 + [1] * 15 + [0] * 25
    assert cohens_kappa(a, b, [0, 1]) == pytest.approx(0.375)


def test_cohens_kappa_undefined_without_variation():
    assert cohens_kappa([1, 1, 1], [1, 1, 1], [1, 2]) is None
    assert cohens_kappa([], [], [1, 2]) is None


def test_weighted_kappa_perfect_agreement():
    assert weighted_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == 1.0


def test_weighted_kappa_partial_credit_for_near_misses():
    # All disagreements are by one point: weighted kappa must beat the
    # unweighted kappa on the same ratings.
    a = [4, 4, 4, 4, 3, 3]
    b = [3, 3, 3, 3, 2, 2]
    assert weighted_kappa(a, b, [0, 1, 2, 3, 4]) > cohens_kappa(a, b, [0, 1, 2, 3, 4])


def test_weighted_kappa_undefined_without_variation():
    assert weighted_kappa([4, 4, 4], [4, 4, 4], [0, 1, 2, 3, 4]) is None


def test_analyze_reports_sample_sizes(store):
    result = analyze(store, "1.0.0")
    assert result["n_double_graded_responses"] == 80
    assert result["n_single_graded_responses"] == 160
    assert result["n_llm_graded_responses"] == 240
    assert result["n_adjudicated_responses"] == 240
    assert result["overall"]["n_pairs"] == 400
    assert result["pass_fail"]["n"] == 80
    assert result["failure_labels"]["n"] == 80
    assert result["llm_vs_adjudicated"]["n_pairs"] == 1200


def test_analyze_agreement_is_in_range(store):
    result = analyze(store, "1.0.0")
    for dim, row in result["per_dimension"].items():
        assert 0.0 <= row["exact_agreement"] <= 1.0
        assert row["weighted_kappa"] is None or -1.0 <= row["weighted_kappa"] <= 1.0
    assert 0.0 <= result["overall"]["exact_agreement"] <= 1.0


def test_analyze_pass_rates_favour_the_careful_model(store):
    result = analyze(store, "1.0.0")
    assert result["by_model"]["model-a"]["pass_rate"] > result["by_model"]["model-b"]["pass_rate"]
    assert result["by_model"]["model-a"]["mean_score"] > result["by_model"]["model-b"]["mean_score"]


def test_analyze_failure_counts_sum_to_240(store):
    result = analyze(store, "1.0.0")
    assert sum(result["failure_counts"].values()) == 240
    assert sum(result["overall_adjudicated"]["verdicts"].values()) == 240


def test_analyze_disagreement_examples_have_adjudication(store):
    result = analyze(store, "1.0.0")
    assert result["n_disagreements"] == len(result["disagreement_examples"])
    assert result["n_disagreements"] > 0
    for ex in result["disagreement_examples"]:
        assert ex["adjudicated_scores"] is not None
        assert ex["differing_dimensions"]


def test_analyze_llm_differs_most_on_evidence_and_safety(store):
    result = analyze(store, "1.0.0")
    per_dim = result["llm_vs_adjudicated"]["per_dimension"]
    assert per_dim["evidence_use"]["diff_gt_1_rate"] > per_dim["factual_accuracy"]["diff_gt_1_rate"]
    assert per_dim["safety"]["diff_gt_1_rate"] > per_dim["factual_accuracy"]["diff_gt_1_rate"]
    assert result["llm_vs_adjudicated"]["diff_gt_1"] > 0


def test_revision_impact_improves_agreement(store):
    impact = revision_impact(store)
    assert impact["before"]["overall_exact_agreement"] < impact["after"]["overall_exact_agreement"]
    assert impact["before"]["overall_weighted_kappa"] < impact["after"]["overall_weighted_kappa"]
    assert impact["n_verdict_flips"] > 0
    assert impact["n_refusal_flips"] == impact["n_verdict_flips"]
    for flip in impact["flips"]:
        assert flip["from"] == "failure" and flip["to"] == "pass"
        assert flip["refusal"] is True


def test_revision_impact_fixes_evidence_agreement(store):
    impact = revision_impact(store)
    before = impact["before"]["per_dimension"]["evidence_use"]
    after = impact["after"]["per_dimension"]["evidence_use"]
    assert after["exact_agreement"] > before["exact_agreement"]
    assert after["exact_agreement"] == 1.0
