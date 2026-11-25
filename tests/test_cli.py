"""CLI smoke tests: every subcommand runs against a temporary store."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def run_cli(*args, cwd):
    result = subprocess.run(
        [sys.executable, "-m", "meridian_eval.cli", *args],
        cwd=cwd, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "src")},
    )
    return result


@pytest.fixture()
def workdir(tmp_path):
    return tmp_path


def test_cli_load_and_blind(workdir):
    result = run_cli("load", "--db", "store.db",
                     "--pilot", str(DATA / "pilot.jsonl"),
                     "--rubrics", str(DATA / "rubrics"),
                     "--sources", str(DATA / "sources"), cwd=workdir)
    assert result.returncode == 0, result.stderr
    assert "loaded 120 items" in result.stdout
    result = run_cli("blind", "--db", "store.db", cwd=workdir)
    assert result.returncode == 0, result.stderr
    assert "blinded 240 responses" in result.stdout


def test_cli_full_run(workdir):
    load = ["load", "--db", "store.db",
            "--pilot", str(DATA / "pilot.jsonl"),
            "--rubrics", str(DATA / "rubrics"),
            "--sources", str(DATA / "sources")]
    assert run_cli(*load, cwd=workdir).returncode == 0
    assert run_cli("blind", "--db", "store.db", cwd=workdir).returncode == 0
    assert run_cli("grade", "--db", "store.db", "--grader", "grader-1", cwd=workdir).returncode == 0
    assert run_cli("grade", "--db", "store.db", "--grader", "grader-2", cwd=workdir).returncode == 0
    assert run_cli("llm-grade", "--db", "store.db", cwd=workdir).returncode == 0
    assert run_cli("adjudicate", "--db", "store.db", cwd=workdir).returncode == 0
    result = run_cli("analyze", "--db", "store.db", "--out", "analysis.json", cwd=workdir)
    assert result.returncode == 0, result.stderr
    assert "overall exact agreement" in result.stdout
    payload = json.loads((workdir / "analysis.json").read_text())
    assert payload["analysis"]["n_double_graded_responses"] == 80
    result = run_cli("report", "--db", "store.db", "--out", "reports", cwd=workdir)
    assert result.returncode == 0, result.stderr
    assert (workdir / "reports" / "analysis.md").exists()
    assert (workdir / "reports" / "analysis.json").exists()


def test_cli_load_accepts_csv(workdir):
    result = run_cli("load", "--db", "store.db", "--pilot", str(DATA / "pilot.csv"),
                     "--rubrics", str(DATA / "rubrics"),
                     "--sources", str(DATA / "sources"), cwd=workdir)
    assert result.returncode == 0, result.stderr
    assert "loaded 120 items" in result.stdout


def test_cli_blind_fails_on_empty_store(workdir):
    from meridian_eval.store import Store
    Store(workdir / "store.db").close()
    result = run_cli("blind", "--db", "store.db", cwd=workdir)
    assert result.returncode == 1
    assert "load" in result.stderr


def test_cli_grade_rejects_unknown_grader(workdir):
    result = run_cli("grade", "--db", "store.db", "--grader", "grader-9", cwd=workdir)
    assert result.returncode != 0


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "meridian_eval.cli", "--version"],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0
    assert "meridian" in result.stdout


def _cli_store_with_responses(workdir):
    load = ["load", "--db", "store.db",
            "--pilot", str(DATA / "pilot.jsonl"),
            "--rubrics", str(DATA / "rubrics"),
            "--sources", str(DATA / "sources")]
    assert run_cli(*load, cwd=workdir).returncode == 0
    assert run_cli("blind", "--db", "store.db", cwd=workdir).returncode == 0


def test_cli_llm_grade_live_wires_http_grader(tmp_path, monkeypatch):
    _cli_store_with_responses(tmp_path)
    calls = []

    class FakeHttpGrader:
        def __init__(self, *args, **kwargs):
            self.model = "fake-live-model"

        def grade(self, blinded, rubric):
            calls.append(blinded["blinded_id"])
            return {"scores": {"factual_accuracy": 4, "evidence_use": 4,
                               "instruction_following": 4, "completeness": 4,
                               "safety": 4},
                    "evidence_note": "Live grader (fake).",
                    "failure_label": "none"}

    monkeypatch.setenv("MERIDIAN_LLM_ENDPOINT", "https://example.invalid/v1/chat/completions")
    monkeypatch.setenv("MERIDIAN_LLM_API_KEY", "test-key")
    import meridian_eval.cli as cli_mod
    monkeypatch.setattr(cli_mod, "HttpLLMGrader", FakeHttpGrader)
    assert cli_mod.main(["llm-grade", "--db", str(tmp_path / "store.db"), "--live"]) == 0
    assert len(calls) == 240
    from meridian_eval.store import Store
    store = Store(tmp_path / "store.db")
    rows = store.llm_scores()
    assert len(rows) == 240
    assert {row["grader"] for row in rows} == {"live-llm"}
    assert all(row["scores"]["factual_accuracy"] == 4 for row in rows)
    assert {row["blinded_id"] for row in rows} == set(calls)
    store.close()


def test_cli_llm_grade_live_needs_configuration(tmp_path, monkeypatch):
    _cli_store_with_responses(tmp_path)
    monkeypatch.delenv("MERIDIAN_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("MERIDIAN_LLM_API_KEY", raising=False)
    import meridian_eval.cli as cli_mod
    assert cli_mod.main(["llm-grade", "--db", str(tmp_path / "store.db"), "--live"]) == 1


def test_cli_llm_grade_default_still_uses_mock(tmp_path):
    _cli_store_with_responses(tmp_path)
    assert run_cli("llm-grade", "--db", "store.db", cwd=tmp_path).returncode == 0
    from meridian_eval.store import Store
    store = Store(tmp_path / "store.db")
    rows = store.llm_scores()
    assert len(rows) == 240
    assert {row["grader"] for row in rows} == {"mock-llm"}
    store.close()
