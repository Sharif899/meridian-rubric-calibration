"""SQLite store for the Meridian evaluation pipeline.

Tables:
- meta: key/value run metadata (rubric versions loaded, pilot counts)
- items: pilot items
- sources: knowledge-base documents
- rubrics: rubric versions (full JSON)
- responses: blinded responses. The `model` column is the sealed mapping:
  it is stored so results can be analysed by model, but it is never
  returned by the web API or the blinded views.
- human_scores: one row per grader judgment
- llm_scores: one row per LLM-grader judgment
- adjudications: one row per double-graded response that was adjudicated,
  plus one row per single-graded response carrying the adjudicated score
  (the single human score, no adjudication needed)

The store file itself is gitignored; only the pipeline outputs are kept.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .errors import NotFoundError

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    area TEXT NOT NULL,
    prompt TEXT NOT NULL,
    reference_answer TEXT NOT NULL,
    source_ids TEXT NOT NULL,
    key_facts TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    ambiguous INTEGER NOT NULL,
    mock_notes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    area TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rubrics (
    version TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS responses (
    blinded_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    model TEXT NOT NULL,
    response_text TEXT NOT NULL,
    defect_profile TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items (id)
);
CREATE TABLE IF NOT EXISTS human_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blinded_id TEXT NOT NULL,
    grader TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    scores TEXT NOT NULL,
    evidence_note TEXT NOT NULL,
    failure_label TEXT NOT NULL,
    FOREIGN KEY (blinded_id) REFERENCES responses (blinded_id),
    UNIQUE (blinded_id, grader, rubric_version)
);
CREATE TABLE IF NOT EXISTS llm_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blinded_id TEXT NOT NULL,
    grader TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    scores TEXT NOT NULL,
    evidence_note TEXT NOT NULL,
    failure_label TEXT NOT NULL,
    FOREIGN KEY (blinded_id) REFERENCES responses (blinded_id),
    UNIQUE (blinded_id, grader, rubric_version)
);
CREATE TABLE IF NOT EXISTS adjudications (
    blinded_id TEXT PRIMARY KEY,
    grader1_scores TEXT,
    grader2_scores TEXT,
    adjudicated_scores TEXT NOT NULL,
    failure_label TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    adjudicator TEXT NOT NULL,
    FOREIGN KEY (blinded_id) REFERENCES responses (blinded_id)
);
"""


class Store:
    """A SQLite-backed evaluation store."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- meta ------------------------------------------------------------
    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    # -- items / sources / rubrics ---------------------------------------
    def insert_item(self, item: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO items "
            "(id, area, prompt, reference_answer, source_ids, key_facts, difficulty, ambiguous, mock_notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item["id"], item["area"], item["prompt"], item["reference_answer"],
                json.dumps(item["source_ids"]), json.dumps(item["key_facts"]),
                item["difficulty"], int(item["ambiguous"]), json.dumps(item["mock_notes"]),
            ),
        )

    def insert_source(self, source: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO sources (id, title, area, body) VALUES (?, ?, ?, ?)",
            (source["id"], source["title"], source["area"], source["body"]),
        )

    def insert_rubric(self, version: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO rubrics (version, payload) VALUES (?, ?)",
            (version, json.dumps(payload)),
        )

    def get_rubric(self, version: str) -> dict:
        row = self.conn.execute(
            "SELECT payload FROM rubrics WHERE version = ?", (version,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"rubric version {version} not loaded")
        return json.loads(row["payload"])

    def rubric_versions(self) -> list[str]:
        return [r["version"] for r in self.conn.execute(
            "SELECT version FROM rubrics ORDER BY version"
        ).fetchall()]

    def commit(self) -> None:
        self.conn.commit()

    # -- items -----------------------------------------------------------
    def items(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM items ORDER BY id").fetchall()
        return [self._item_row(r) for r in rows]

    def get_item(self, item_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"item {item_id} not found")
        return self._item_row(row)

    @staticmethod
    def _item_row(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "area": row["area"],
            "prompt": row["prompt"],
            "reference_answer": row["reference_answer"],
            "source_ids": json.loads(row["source_ids"]),
            "key_facts": json.loads(row["key_facts"]),
            "difficulty": row["difficulty"],
            "ambiguous": bool(row["ambiguous"]),
            "mock_notes": json.loads(row["mock_notes"]),
        }

    def sources(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM sources ORDER BY id").fetchall()]

    def get_source(self, source_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"source {source_id} not found")
        return dict(row)

    # -- responses -------------------------------------------------------
    def insert_response(self, blinded_id: str, item_id: str, model: str,
                        response_text: str, defect_profile: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO responses "
            "(blinded_id, item_id, model, response_text, defect_profile) VALUES (?, ?, ?, ?, ?)",
            (blinded_id, item_id, model, response_text, json.dumps(defect_profile)),
        )

    def responses(self) -> list[dict]:
        """All responses, including the sealed model column (internal use only)."""
        rows = self.conn.execute("SELECT * FROM responses ORDER BY blinded_id").fetchall()
        return [self._response_row(r) for r in rows]

    def get_response(self, blinded_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM responses WHERE blinded_id = ?", (blinded_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"response {blinded_id} not found")
        return self._response_row(row)

    @staticmethod
    def _response_row(row: sqlite3.Row) -> dict:
        return {
            "blinded_id": row["blinded_id"],
            "item_id": row["item_id"],
            "model": row["model"],
            "response_text": row["response_text"],
            "defect_profile": json.loads(row["defect_profile"]),
        }

    def blinded_view(self) -> list[dict]:
        """The view graders and the web UI see: no model, no defect profile."""
        rows = self.conn.execute(
            "SELECT r.blinded_id, r.item_id, i.area, i.prompt, i.reference_answer, "
            "i.source_ids, i.difficulty, i.ambiguous, r.response_text "
            "FROM responses r JOIN items i ON i.id = r.item_id ORDER BY r.blinded_id"
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "blinded_id": r["blinded_id"],
                "item_id": r["item_id"],
                "area": r["area"],
                "prompt": r["prompt"],
                "reference_answer": r["reference_answer"],
                "source_ids": json.loads(r["source_ids"]),
                "difficulty": r["difficulty"],
                "ambiguous": bool(r["ambiguous"]),
                "response_text": r["response_text"],
            })
        return out

    # -- scores ----------------------------------------------------------
    def insert_human_score(self, blinded_id: str, grader: str, rubric_version: str,
                           scores: dict, evidence_note: str, failure_label: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO human_scores "
            "(blinded_id, grader, rubric_version, scores, evidence_note, failure_label) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (blinded_id, grader, rubric_version, json.dumps(scores), evidence_note, failure_label),
        )

    def insert_llm_score(self, blinded_id: str, grader: str, rubric_version: str,
                         scores: dict, evidence_note: str, failure_label: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO llm_scores "
            "(blinded_id, grader, rubric_version, scores, evidence_note, failure_label) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (blinded_id, grader, rubric_version, json.dumps(scores), evidence_note, failure_label),
        )

    def human_scores(self, grader: str | None = None, rubric_version: str | None = None) -> list[dict]:
        query = "SELECT * FROM human_scores"
        params: list = []
        clauses = []
        if grader is not None:
            clauses.append("grader = ?")
            params.append(grader)
        if rubric_version is not None:
            clauses.append("rubric_version = ?")
            params.append(rubric_version)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY blinded_id, grader"
        rows = self.conn.execute(query, params).fetchall()
        return [self._score_row(r) for r in rows]

    def llm_scores(self, rubric_version: str | None = None) -> list[dict]:
        query = "SELECT * FROM llm_scores"
        params: list = []
        if rubric_version is not None:
            query += " WHERE rubric_version = ?"
            params.append(rubric_version)
        query += " ORDER BY blinded_id"
        rows = self.conn.execute(query, params).fetchall()
        return [self._score_row(r) for r in rows]

    @staticmethod
    def _score_row(row: sqlite3.Row) -> dict:
        return {
            "blinded_id": row["blinded_id"],
            "grader": row["grader"],
            "rubric_version": row["rubric_version"],
            "scores": json.loads(row["scores"]),
            "evidence_note": row["evidence_note"],
            "failure_label": row["failure_label"],
        }

    # -- adjudications ---------------------------------------------------
    def insert_adjudication(self, blinded_id: str, grader1_scores: dict | None,
                            grader2_scores: dict | None, adjudicated_scores: dict,
                            failure_label: str, decision: str, rationale: str,
                            adjudicator: str = "adjudicator-1") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO adjudications "
            "(blinded_id, grader1_scores, grader2_scores, adjudicated_scores, failure_label, "
            "decision, rationale, adjudicator) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                blinded_id,
                json.dumps(grader1_scores) if grader1_scores is not None else None,
                json.dumps(grader2_scores) if grader2_scores is not None else None,
                json.dumps(adjudicated_scores), failure_label, decision, rationale, adjudicator,
            ),
        )

    def adjudications(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM adjudications ORDER BY blinded_id").fetchall()
        out = []
        for r in rows:
            out.append({
                "blinded_id": r["blinded_id"],
                "grader1_scores": json.loads(r["grader1_scores"]) if r["grader1_scores"] else None,
                "grader2_scores": json.loads(r["grader2_scores"]) if r["grader2_scores"] else None,
                "adjudicated_scores": json.loads(r["adjudicated_scores"]),
                "failure_label": r["failure_label"],
                "decision": r["decision"],
                "rationale": r["rationale"],
                "adjudicator": r["adjudicator"],
            })
        return out

    def counts(self) -> dict:
        out = {}
        for table in ("items", "sources", "rubrics", "responses", "human_scores", "llm_scores", "adjudications"):
            out[table] = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return out
