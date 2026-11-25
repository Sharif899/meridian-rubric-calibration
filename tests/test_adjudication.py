"""Adjudication: agreed, single-graded, and adjudicated paths."""

from meridian_eval.adjudication import adjudicate_pair
from meridian_eval.graders import GRADER_1
from meridian_eval.providers import empty_profile
from meridian_eval.rubric import verdict


def _scores(**overrides):
    base = {"factual_accuracy": 4, "evidence_use": 4, "instruction_following": 4,
            "completeness": 4, "safety": 4}
    base.update(overrides)
    return base


def _item(items, item_id):
    return next(it for it in items if it["id"] == item_id)


def test_agreed_graders_pass_through(items):
    item = _item(items, "CS-001")
    record = adjudicate_pair(_scores(), "none", _scores(), "none", empty_profile(), item)
    assert record["decision"] == "agreed"
    assert record["adjudicated_scores"] == _scores()
    assert record["failure_label"] == "none"


def test_single_graded_passes_through(items):
    item = _item(items, "CS-001")
    record = adjudicate_pair(_scores(), "none", None, None, empty_profile(), item)
    assert record["decision"] == "single"
    assert record["adjudicated_scores"] == _scores()


def test_adjudication_applies_the_v110_core_rule(items):
    item = _item(items, "CS-001")
    profile = dict(empty_profile(), wrong_core_fact=True)
    g1 = _scores(factual_accuracy=1)
    g2 = _scores(factual_accuracy=2)
    record = adjudicate_pair(g1, "incorrect_fact", g2, "incorrect_fact", profile, item)
    assert record["decision"] == "adjudicated"
    assert record["adjudicated_scores"]["factual_accuracy"] == 1
    assert "core claim" in record["rationale"]


def test_adjudication_applies_the_v110_evidence_rule(items):
    item = _item(items, "CS-001")
    profile = dict(empty_profile(), cites_related_not_governing=True)
    g1 = _scores(evidence_use=3)
    g2 = _scores(evidence_use=2)
    record = adjudicate_pair(g1, "unsupported_claim", g2, "unsupported_claim", profile, item)
    assert record["adjudicated_scores"]["evidence_use"] == 2
    assert "governing source" in record["rationale"]


def test_adjudication_takes_the_stricter_reading_when_no_rule_applies(items):
    item = _item(items, "CS-001")
    profile = dict(empty_profile(), missing_secondary=True)
    g1 = _scores(completeness=2)
    g2 = _scores(completeness=1)
    record = adjudicate_pair(g1, "incomplete", g2, "incomplete", profile, item)
    assert record["adjudicated_scores"]["completeness"] == 1
    assert "stricter" in record["rationale"]


def test_adjudication_resolves_label_splits_on_ambiguous_items(items):
    ambiguous = next(it for it in items if it["ambiguous"])
    record = adjudicate_pair(_scores(), "none", _scores(), "ambiguous_item",
                             empty_profile(), ambiguous)
    assert record["failure_label"] == "ambiguous_item"
    assert "flagged ambiguous" in record["rationale"]


def test_adjudication_takes_the_more_severe_label(items):
    item = _item(items, "CS-001")
    record = adjudicate_pair(_scores(), "incomplete", _scores(), "unsupported_claim",
                             empty_profile(), item)
    assert record["failure_label"] == "unsupported_claim"


def test_adjudication_needs_at_least_one_score(items):
    item = _item(items, "CS-001")
    import pytest
    with pytest.raises(ValueError):
        adjudicate_pair(None, None, None, None, empty_profile(), item)


def test_store_adjudications_cover_all_responses(store):
    adjudications = store.adjudications()
    assert len(adjudications) == 240
    decisions = {a["decision"] for a in adjudications}
    assert decisions <= {"agreed", "adjudicated", "single"}
    for adj in adjudications:
        assert verdict(adj["adjudicated_scores"]) in ("pass", "partial", "failure")


def test_adjudicated_scores_are_the_reference(store):
    # Every adjudication's failure label matches one of the two graders'
    # labels or the ambiguous-item resolution; never the LLM grader's.
    llm_labels = {s["blinded_id"]: s["failure_label"] for s in store.llm_scores()}
    for adj in store.adjudications():
        assert adj["failure_label"] in ("none", "unsupported_claim", "incomplete",
                                        "incorrect_fact", "unsafe", "refusal_error",
                                        "ambiguous_item")
