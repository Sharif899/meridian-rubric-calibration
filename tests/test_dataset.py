"""Pilot dataset integrity: 120 items, 40 per area, CSV == JSONL."""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from meridian_eval.dataset import load_items_csv, load_items_jsonl, load_sources
from meridian_eval.errors import ValidationError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def test_120_items_40_per_area(items):
    assert len(items) == 120
    counts = Counter(it["area"] for it in items)
    assert counts == {"customer_support": 40, "technical_troubleshooting": 40, "research": 40}


def test_ids_are_sequential_per_area(items):
    for prefix in ("CS", "TS", "RS"):
        ids = sorted(it["id"] for it in items if it["id"].startswith(prefix))
        assert ids == [f"{prefix}-{n:03d}" for n in range(1, 41)]


def test_prompts_are_distinct(items):
    assert len({it["prompt"] for it in items}) == 120


def test_difficulty_mix(items):
    counts = Counter(it["difficulty"] for it in items)
    assert counts["ambiguous"] == 20
    assert counts["straightforward"] + counts["tricky"] == 100
    assert all(it["ambiguous"] == (it["difficulty"] == "ambiguous") for it in items)


def test_references_cite_sources_and_contain_key_facts(items):
    for it in items:
        for src in it["source_ids"]:
            assert src in it["reference_answer"], it["id"]
        for fact in it["key_facts"]:
            assert fact in it["reference_answer"], it["id"]


def test_mock_notes_are_complete(items):
    for it in items:
        notes = it["mock_notes"]
        correct, wrong = notes["wrong_number"]
        assert correct in it["reference_answer"], it["id"]
        assert correct != wrong
        assert notes["fabricated_sentence"].strip()
        assert notes["related_source"] not in it["source_ids"], it["id"]


def test_csv_matches_jsonl(items):
    rows = list(csv.DictReader((DATA / "pilot.csv").open(newline="", encoding="utf-8")))
    assert len(rows) == 120
    for it, row in zip(items, rows):
        assert it["id"] == row["id"]
        assert it["prompt"] == row["prompt"]
        assert it["reference_answer"] == row["reference_answer"]
        assert it["source_ids"] == row["source_ids"].split(";")
        assert it["key_facts"] == row["key_facts"].split(";")
        assert it["difficulty"] == row["difficulty"]
        assert str(it["ambiguous"]).lower() == row["ambiguous"]


def test_csv_loads_through_the_loader():
    from_csv = load_items_csv(DATA / "pilot.csv")
    from_jsonl = load_items_jsonl(DATA / "pilot.jsonl")
    assert from_csv == from_jsonl


def test_sources_cover_every_referenced_id(items):
    sources = load_sources(DATA / "sources")
    assert len(sources) == 12
    known = {s["id"] for s in sources}
    referenced = {src for it in items for src in it["source_ids"]}
    assert referenced <= known
    for source in sources:
        assert source["body"].strip()
        assert source["area"] in ("customer_support", "technical_troubleshooting", "research")


def test_refusal_items_exist_in_each_area(items):
    refusals = [it for it in items if it["reference_answer"].startswith("I cannot")]
    assert len(refusals) == 12
    assert Counter(it["area"] for it in refusals) == {
        "customer_support": 4, "technical_troubleshooting": 4, "research": 4,
    }


def test_loader_rejects_wrong_count(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "CS-001", "area": "customer_support", "prompt": "x",
                               "reference_answer": "y", "source_ids": ["KB-REF-01"],
                               "key_facts": ["y"], "difficulty": "straightforward",
                               "ambiguous": False,
                               "mock_notes": {"wrong_number": ["a", "b"],
                                              "fabricated_sentence": "c",
                                              "related_source": "KB-BIL-01"}}) + "\n")
    with pytest.raises(ValidationError):
        load_items_jsonl(bad)


def test_loader_rejects_unknown_area(items):
    broken = dict(items[0])
    broken["area"] = "sales"
    from meridian_eval.dataset import validate_item
    with pytest.raises(ValidationError):
        validate_item(broken)
