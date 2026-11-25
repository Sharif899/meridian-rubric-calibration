"""End-to-end pipeline: load -> blind -> grade -> llm-grade -> adjudicate
-> analyze -> report, and determinism across runs."""

import json
from pathlib import Path

from conftest import build_store
from meridian_eval.analysis import analyze


def test_pipeline_produces_consistent_numbers(tmp_path):
    db1 = build_store(tmp_path / "a.db")
    db2 = build_store(tmp_path / "b.db")
    a1 = analyze(db1, "1.0.0")
    a2 = analyze(db2, "1.0.0")
    assert a1 == a2
    db1.close()
    db2.close()


def test_pipeline_counts(tmp_path):
    db = build_store(tmp_path / "store.db")
    counts = db.counts()
    assert counts == {
        "items": 120, "sources": 12, "rubrics": 2, "responses": 240,
        "human_scores": 320, "llm_scores": 240, "adjudications": 240,
    }
    db.close()


def test_every_response_has_a_human_score(tmp_path):
    db = build_store(tmp_path / "store.db")
    g1 = {s["blinded_id"] for s in db.human_scores(grader="grader-1")}
    assert len(g1) == 240
    g2 = {s["blinded_id"] for s in db.human_scores(grader="grader-2")}
    assert len(g2) == 80
    db.close()


def test_every_score_traces_to_a_rubric_version(tmp_path):
    db = build_store(tmp_path / "store.db")
    for score in db.human_scores() + db.llm_scores():
        assert score["rubric_version"] in ("1.0.0", "1.1.0")
        assert score["scores"].keys() == {
            "factual_accuracy", "evidence_use", "instruction_following",
            "completeness", "safety",
        }
    db.close()


def test_report_files_are_generated(tmp_path):
    from meridian_eval.analysis import revision_impact
    from meridian_eval.report import render_json, render_markdown

    db = build_store(tmp_path / "store.db")
    analysis = analyze(db, "1.0.0")
    revision = revision_impact(db)
    meta = {"n_items": 120, "items_per_area": 40, "n_responses": 240}
    md = render_markdown(analysis, revision, meta)
    assert "Human-grader agreement" in md
    assert "LLM grader vs adjudicated" in md
    assert "What the rubric revision changes" in md
    payload = render_json(analysis, revision, meta)
    assert payload["analysis"]["n_double_graded_responses"] == 80
    assert payload["revision_impact"]["n_verdict_flips"] > 0
    db.close()


def test_report_numbers_match_the_analysis(tmp_path):
    from meridian_eval.analysis import revision_impact
    from meridian_eval.report import render_markdown

    db = build_store(tmp_path / "store.db")
    analysis = analyze(db, "1.0.0")
    revision = revision_impact(db)
    meta = {"n_items": 120, "items_per_area": 40, "n_responses": 240}
    md = render_markdown(analysis, revision, meta)
    overall = analysis["overall"]
    assert f"{overall['exact_agreement'] * 100:.1f}%" in md
    assert f"{overall['weighted_kappa']:.3f}" in md
    assert f"{analysis['pass_fail']['kappa']:.3f}" in md
    db.close()


def test_store_survives_reopen(tmp_path):
    path = tmp_path / "store.db"
    db = build_store(path)
    db.close()
    from meridian_eval.store import Store
    reopened = Store(path)
    assert reopened.counts()["responses"] == 240
    reopened.close()
