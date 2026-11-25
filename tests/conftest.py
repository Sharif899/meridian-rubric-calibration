"""Shared fixtures: a populated store built by running the real pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from meridian_eval.adjudication import adjudicate_pair
from meridian_eval.blind import assign_blinded_ids, double_graded_item_ids
from meridian_eval.dataset import load_items_jsonl, load_sources
from meridian_eval.graders import GRADER_1, GRADER_2, grade_human, grade_llm_mock
from meridian_eval.providers import generate_response
from meridian_eval.rubric import load_rubrics
from meridian_eval.store import Store

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def build_store(path: Path) -> Store:
    """Load the pilot, blind it, grade it, and adjudicate it."""
    store = Store(path)
    for item in load_items_jsonl(DATA / "pilot.jsonl"):
        store.insert_item(item)
    for source in load_sources(DATA / "sources"):
        store.insert_source(source)
    for version, payload in load_rubrics(DATA / "rubrics").items():
        store.insert_rubric(version, payload)
    store.set_meta("n_items", "120")
    store.commit()
    assignment = assign_blinded_ids(store, seed=42)
    for entry in assignment:
        item = store.get_item(entry["item_id"])
        text, profile = generate_response(item, entry["model"])
        store.insert_response(entry["blinded_id"], entry["item_id"], entry["model"], text, profile)
    store.commit()
    double_items = set(double_graded_item_ids(store))
    for response in store.responses():
        item = store.get_item(response["item_id"])
        for grader in (GRADER_1, GRADER_2):
            if grader == GRADER_2 and response["item_id"] not in double_items:
                continue
            judgment = grade_human(response["defect_profile"], item, "1.0.0", grader)
            store.insert_human_score(
                response["blinded_id"], grader, "1.0.0",
                judgment["scores"], judgment["evidence_note"], judgment["failure_label"],
            )
        judgment = grade_llm_mock(response["defect_profile"], item, "1.0.0", response["response_text"])
        store.insert_llm_score(
            response["blinded_id"], "mock-llm", "1.0.0",
            judgment["scores"], judgment["evidence_note"], judgment["failure_label"],
        )
    store.commit()
    g1 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_1, rubric_version="1.0.0")}
    g2 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_2, rubric_version="1.0.0")}
    for response in store.responses():
        item = store.get_item(response["item_id"])
        s1 = g1.get(response["blinded_id"])
        s2 = g2.get(response["blinded_id"])
        record = adjudicate_pair(
            s1["scores"] if s1 else None,
            s1["failure_label"] if s1 else None,
            s2["scores"] if s2 else None,
            s2["failure_label"] if s2 else None,
            response["defect_profile"],
            item,
        )
        store.insert_adjudication(
            response["blinded_id"],
            s1["scores"] if s1 else None,
            s2["scores"] if s2 else None,
            record["adjudicated_scores"],
            record["failure_label"],
            record["decision"],
            record["rationale"],
        )
    store.commit()
    return store


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    path = tmp_path_factory.mktemp("meridian") / "store.db"
    db = build_store(path)
    yield db
    db.close()


@pytest.fixture(scope="module")
def items():
    return load_items_jsonl(DATA / "pilot.jsonl")


@pytest.fixture(scope="module")
def rubrics():
    return load_rubrics(DATA / "rubrics")
