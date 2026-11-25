"""Blinded response IDs.

Every model response gets a blinded ID (R-001, R-002, ...) assigned in a
seeded shuffled order, so the ID reveals nothing about the model or the
item. The mapping from blinded ID to model lives only in the store's
`responses` table (the sealed mapping); it is never returned by the
blinded view or the web API.
"""

from __future__ import annotations

import random

from .providers import is_refusal_item
from .store import Store


def assign_blinded_ids(store: Store, seed: int = 42) -> list[dict]:
    """Assign blinded IDs to every (item, model) pair in the store.

    The caller must have loaded the items first. Returns the assignment
    list of dicts with blinded_id, item_id, model. The assignment is
    deterministic for a given seed.
    """
    rng = random.Random(seed)
    items = store.items()
    pairs = [(item["id"], model) for item in items for model in ("model-a", "model-b")]
    rng.shuffle(pairs)
    assignment = []
    for n, (item_id, model) in enumerate(pairs, start=1):
        assignment.append({
            "blinded_id": f"R-{n:03d}",
            "item_id": item_id,
            "model": model,
        })
    return assignment


def double_graded_item_ids(store: Store, count: int = 40) -> list[str]:
    """Pick the items both human graders score independently.

    All ambiguous items are included first (they are where disagreement
    concentrates), then all refusal items (they are where safety is
    exercised), then a stratified sample of the remaining items until
    `count` is reached. Deterministic.
    """
    items = store.items()
    ambiguous = sorted(it["id"] for it in items if it["ambiguous"])
    refusal = sorted(it["id"] for it in items if is_refusal_item(it))
    picked = sorted(set(ambiguous) | set(refusal))
    rest = sorted(it["id"] for it in items if it["id"] not in picked)
    for item_id in rest[::3]:
        if len(picked) >= count:
            break
        picked.append(item_id)
    for item_id in rest:
        if len(picked) >= count:
            break
        if item_id not in picked:
            picked.append(item_id)
    return sorted(picked)
