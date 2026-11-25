"""Reviewer web UI.

A single-page interface for blinded human review: load a task set, select
a rubric version, inspect blinded responses, and submit or review
judgments. The API never exposes the model behind a blinded response or
its defect profile.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..errors import NotFoundError
from ..rubric import DIMENSION_IDS, FAILURE_LABEL_IDS, validate_scores
from ..store import Store

INDEX_HTML = Path(__file__).resolve().parent / "index.html"


class JudgmentIn(BaseModel):
    blinded_id: str
    grader: str = "reviewer"
    rubric_version: str
    scores: dict
    evidence_note: str = ""
    failure_label: str = "none"


def create_app(db_path: str = "store.db") -> FastAPI:
    app = FastAPI(title="Meridian reviewer UI")

    def store() -> Store:
        return Store(db_path)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML.read_text(encoding="utf-8")

    @app.get("/api/health")
    def health() -> dict:
        db = store()
        try:
            counts = db.counts()
            return {
                "status": "ok",
                "rubric_versions": db.rubric_versions(),
                "items": counts["items"],
                "responses": counts["responses"],
            }
        finally:
            db.close()

    @app.get("/api/rubrics")
    def rubrics() -> dict:
        db = store()
        try:
            return {"rubrics": [db.get_rubric(v) for v in db.rubric_versions()]}
        finally:
            db.close()

    @app.get("/api/items")
    def items(area: str | None = None) -> dict:
        db = store()
        try:
            view = db.blinded_view()
            if area:
                view = [row for row in view if row["area"] == area]
            out = []
            for row in view:
                sources = []
                for source_id in row["source_ids"]:
                    try:
                        sources.append(db.get_source(source_id))
                    except NotFoundError:
                        continue
                out.append({**row, "sources": sources})
            return {"items": out}
        finally:
            db.close()

    @app.get("/api/judgments")
    def judgments(blinded_id: str | None = None) -> dict:
        db = store()
        try:
            rows = db.human_scores()
            if blinded_id:
                rows = [r for r in rows if r["blinded_id"] == blinded_id]
            return {"judgments": rows}
        finally:
            db.close()

    @app.post("/api/judgments", status_code=201)
    def submit_judgment(body: JudgmentIn) -> dict:
        db = store()
        try:
            try:
                db.get_response(body.blinded_id)
            except NotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            try:
                db.get_rubric(body.rubric_version)
            except NotFoundError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            try:
                scores = validate_scores(body.scores)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if body.failure_label not in FAILURE_LABEL_IDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"failure_label must be one of {FAILURE_LABEL_IDS}",
                )
            db.insert_human_score(
                body.blinded_id, body.grader, body.rubric_version,
                scores, body.evidence_note, body.failure_label,
            )
            db.commit()
            return {
                "blinded_id": body.blinded_id,
                "grader": body.grader,
                "rubric_version": body.rubric_version,
                "scores": scores,
                "evidence_note": body.evidence_note,
                "failure_label": body.failure_label,
            }
        finally:
            db.close()

    return app
