"""Pilot dataset loading: JSONL / CSV items and knowledge-base sources.

An item is a dict with: id, area, prompt, reference_answer, source_ids,
key_facts, difficulty, ambiguous, mock_notes. The CSV export carries the
same items; this module can load either format and asserts they agree.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .errors import ValidationError
from .rubric import AREAS

ITEM_FIELDS = {
    "id", "area", "prompt", "reference_answer", "source_ids", "key_facts",
    "difficulty", "ambiguous", "mock_notes",
}

DIFFICULTIES = {"straightforward", "tricky", "ambiguous"}


def load_items_jsonl(path: str | Path) -> list[dict]:
    """Load and validate pilot items from a JSONL file."""
    path = Path(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ValidationError(f"pilot file not found: {path}") from exc
    items = []
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        validate_item(item, source=f"{path}:{line_no}")
        items.append(item)
    _check_item_set(items, source=str(path))
    return items


def load_items_csv(path: str | Path) -> list[dict]:
    """Load and validate pilot items from the CSV export."""
    path = Path(path)
    try:
        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    except FileNotFoundError as exc:
        raise ValidationError(f"pilot file not found: {path}") from exc
    items = []
    for line_no, row in enumerate(rows, start=2):
        item = {
            "id": row["id"],
            "area": row["area"],
            "prompt": row["prompt"],
            "reference_answer": row["reference_answer"],
            "source_ids": row["source_ids"].split(";") if row["source_ids"] else [],
            "key_facts": row["key_facts"].split(";") if row["key_facts"] else [],
            "difficulty": row["difficulty"],
            "ambiguous": row["ambiguous"].strip().lower() == "true",
            "mock_notes": {
                "wrong_number": [row["wrong_number_correct"], row["wrong_number_wrong"]],
                "fabricated_sentence": row["fabricated_sentence"],
                "related_source": row["related_source"],
            },
        }
        validate_item(item, source=f"{path}:{line_no}")
        items.append(item)
    _check_item_set(items, source=str(path))
    return items


def validate_item(item: dict, source: str = "<item>") -> None:
    """Validate one pilot item. Raises ValidationError."""
    if not isinstance(item, dict):
        raise ValidationError(f"{source}: item must be an object")
    if set(item) != ITEM_FIELDS:
        raise ValidationError(
            f"{source}: item fields must be exactly {sorted(ITEM_FIELDS)}, got {sorted(item)}"
        )
    if not isinstance(item["id"], str) or not item["id"]:
        raise ValidationError(f"{source}: item needs a non-empty id")
    if item["area"] not in AREAS:
        raise ValidationError(f"{source}: unknown area {item['area']!r}")
    if not isinstance(item["prompt"], str) or not item["prompt"].strip():
        raise ValidationError(f"{source}: item needs a prompt")
    if not isinstance(item["reference_answer"], str) or not item["reference_answer"].strip():
        raise ValidationError(f"{source}: item needs a reference answer")
    if not item["source_ids"] or not all(isinstance(s, str) for s in item["source_ids"]):
        raise ValidationError(f"{source}: item needs at least one source id")
    if not item["key_facts"]:
        raise ValidationError(f"{source}: item needs at least one key fact")
    if item["difficulty"] not in DIFFICULTIES:
        raise ValidationError(f"{source}: unknown difficulty {item['difficulty']!r}")
    if item["difficulty"] == "ambiguous" and not item["ambiguous"]:
        raise ValidationError(f"{source}: ambiguous difficulty requires ambiguous=true")
    if not isinstance(item["ambiguous"], bool):
        raise ValidationError(f"{source}: ambiguous must be a boolean")
    notes = item["mock_notes"]
    if not isinstance(notes, dict) or len(notes.get("wrong_number", [])) != 2:
        raise ValidationError(f"{source}: mock_notes needs a wrong_number pair")
    if not notes.get("fabricated_sentence") or not notes.get("related_source"):
        raise ValidationError(f"{source}: mock_notes needs fabricated_sentence and related_source")


def _check_item_set(items: list[dict], source: str) -> None:
    """Check the whole pilot set: 120 items, 40 per area, unique ids/prompts."""
    if len(items) != 120:
        raise ValidationError(f"{source}: pilot must have 120 items, got {len(items)}")
    for area in AREAS:
        count = sum(1 for it in items if it["area"] == area)
        if count != 40:
            raise ValidationError(f"{source}: area {area} must have 40 items, got {count}")
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        raise ValidationError(f"{source}: duplicate item ids")
    prompts = [it["prompt"] for it in items]
    if len(set(prompts)) != len(prompts):
        raise ValidationError(f"{source}: duplicate prompts")
    for it in items:
        for fact in it["key_facts"]:
            if fact not in it["reference_answer"]:
                raise ValidationError(
                    f"{source}: item {it['id']} key fact {fact!r} not in reference answer"
                )
        for src in it["source_ids"]:
            if src not in it["reference_answer"]:
                raise ValidationError(
                    f"{source}: item {it['id']} source {src} not cited in reference answer"
                )


def load_sources(directory: str | Path) -> list[dict]:
    """Load every knowledge-base source document from a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValidationError(f"source directory not found: {directory}")
    sources = []
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}: invalid JSON: {exc}") from exc
        if not doc.get("id") or not doc.get("title") or not doc.get("body"):
            raise ValidationError(f"{path}: source needs id, title and body")
        if doc["area"] not in AREAS:
            raise ValidationError(f"{path}: unknown area {doc['area']!r}")
        sources.append(doc)
    if not sources:
        raise ValidationError(f"no source documents found in {directory}")
    return sources
