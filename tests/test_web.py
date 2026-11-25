"""Reviewer web UI: index, health, items, rubrics, judgments."""

import json

import pytest
from fastapi.testclient import TestClient

from meridian_eval.web.app import create_app


@pytest.fixture(scope="module")
def client(store):
    app = create_app(str(store.path))
    with TestClient(app) as test_client:
        yield test_client


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Meridian reviewer" in response.text
    assert "blinded" in response.text.lower()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["items"] == 120
    assert body["responses"] == 240
    assert body["rubric_versions"] == ["1.0.0", "1.1.0"]


def test_rubrics_endpoint(client):
    response = client.get("/api/rubrics")
    assert response.status_code == 200
    rubrics = response.json()["rubrics"]
    assert [r["version"] for r in rubrics] == ["1.0.0", "1.1.0"]
    assert len(rubrics[0]["dimensions"]) == 5


def test_items_endpoint_returns_blinded_view(client):
    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 240
    blob = json.dumps(items)
    assert "model-a" not in blob
    assert "model-b" not in blob
    assert "defect_profile" not in blob
    assert "mock_notes" not in blob


def test_items_endpoint_filters_by_area(client):
    response = client.get("/api/items", params={"area": "research"})
    items = response.json()["items"]
    assert len(items) == 80
    assert all(it["area"] == "research" for it in items)


def test_items_include_reference_and_sources(client):
    response = client.get("/api/items")
    item = response.json()["items"][0]
    assert item["reference_answer"]
    assert item["sources"]
    assert item["sources"][0]["body"]


def test_judgment_submit_and_list_round_trip(client):
    items = client.get("/api/items").json()["items"]
    blinded_id = items[0]["blinded_id"]
    payload = {
        "blinded_id": blinded_id,
        "grader": "web-reviewer",
        "rubric_version": "1.0.0",
        "scores": {"factual_accuracy": 4, "evidence_use": 3, "instruction_following": 4,
                   "completeness": 4, "safety": 4},
        "evidence_note": "Cites the governing source for the main claim.",
        "failure_label": "none",
    }
    response = client.post("/api/judgments", json=payload)
    assert response.status_code == 201
    assert response.json()["grader"] == "web-reviewer"
    listed = client.get("/api/judgments", params={"blinded_id": blinded_id}).json()["judgments"]
    assert any(j["grader"] == "web-reviewer" for j in listed)


def test_judgment_rejects_bad_scores(client):
    items = client.get("/api/items").json()["items"]
    payload = {
        "blinded_id": items[0]["blinded_id"],
        "grader": "web-reviewer",
        "rubric_version": "1.0.0",
        "scores": {"factual_accuracy": 9, "evidence_use": 3, "instruction_following": 4,
                   "completeness": 4, "safety": 4},
        "failure_label": "none",
    }
    assert client.post("/api/judgments", json=payload).status_code == 400


def test_judgment_rejects_unknown_response(client):
    payload = {
        "blinded_id": "R-999",
        "grader": "web-reviewer",
        "rubric_version": "1.0.0",
        "scores": {"factual_accuracy": 4, "evidence_use": 4, "instruction_following": 4,
                   "completeness": 4, "safety": 4},
        "failure_label": "none",
    }
    assert client.post("/api/judgments", json=payload).status_code == 404


def test_judgment_rejects_unknown_rubric_version(client):
    items = client.get("/api/items").json()["items"]
    payload = {
        "blinded_id": items[0]["blinded_id"],
        "grader": "web-reviewer",
        "rubric_version": "9.9.9",
        "scores": {"factual_accuracy": 4, "evidence_use": 4, "instruction_following": 4,
                   "completeness": 4, "safety": 4},
        "failure_label": "none",
    }
    assert client.post("/api/judgments", json=payload).status_code == 400


def test_judgment_rejects_unknown_failure_label(client):
    items = client.get("/api/items").json()["items"]
    payload = {
        "blinded_id": items[0]["blinded_id"],
        "grader": "web-reviewer",
        "rubric_version": "1.0.0",
        "scores": {"factual_accuracy": 4, "evidence_use": 4, "instruction_following": 4,
                   "completeness": 4, "safety": 4},
        "failure_label": "made_up",
    }
    assert client.post("/api/judgments", json=payload).status_code == 400


def test_judgments_list_all(client):
    response = client.get("/api/judgments")
    assert response.status_code == 200
    assert len(response.json()["judgments"]) >= 320
