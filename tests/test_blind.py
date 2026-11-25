"""Blinding: IDs reveal nothing, the mapping stays sealed, the double set is right."""

from meridian_eval.blind import assign_blinded_ids, double_graded_item_ids
from meridian_eval.errors import NotFoundError


def test_240_blinded_responses(store):
    assert store.counts()["responses"] == 240


def test_blinded_ids_are_sequential(store):
    ids = sorted(r["blinded_id"] for r in store.responses())
    assert ids == [f"R-{n:03d}" for n in range(1, 241)]


def test_blinded_id_does_not_encode_model_or_item(store):
    # The same item's two responses must not sit next to each other in a
    # way that reveals the model, and the ID order must not be item order.
    responses = store.responses()
    by_item = {}
    for r in responses:
        by_item.setdefault(r["item_id"], []).append(r)
    for item_id, pair in by_item.items():
        assert len(pair) == 2
        assert {r["model"] for r in pair} == {"model-a", "model-b"}
    item_ids_in_blinded_order = [r["item_id"] for r in responses]
    assert item_ids_in_blinded_order != sorted(item_ids_in_blinded_order)


def test_blinded_view_hides_model_and_defects(store):
    for row in store.blinded_view():
        assert "model" not in row
        assert "defect_profile" not in row
        assert "mock_notes" not in row
    assert len(store.blinded_view()) == 240


def test_blinded_view_text_contains_no_model_names(store):
    import json
    blob = json.dumps(store.blinded_view())
    assert "model-a" not in blob
    assert "model-b" not in blob


def test_assignment_is_deterministic(store):
    first = assign_blinded_ids(store, seed=42)
    second = assign_blinded_ids(store, seed=42)
    assert first == second
    assert assign_blinded_ids(store, seed=7) != first


def test_double_graded_set_is_40_items(store):
    picked = double_graded_item_ids(store)
    assert len(picked) == 40
    assert len(set(picked)) == 40


def test_double_graded_set_includes_all_ambiguous_and_refusal_items(store):
    picked = set(double_graded_item_ids(store))
    items = store.items()
    ambiguous = {it["id"] for it in items if it["ambiguous"]}
    refusal = {it["id"] for it in items if it["reference_answer"].startswith("I cannot")}
    assert ambiguous <= picked
    assert refusal <= picked
    assert len(ambiguous) == 20
    assert len(refusal) == 12


def test_double_graded_set_covers_all_areas(store):
    picked = double_graded_item_ids(store)
    areas = {store.get_item(i)["area"] for i in picked}
    assert areas == {"customer_support", "technical_troubleshooting", "research"}


def test_get_response_raises_for_unknown_id(store):
    import pytest
    with pytest.raises(NotFoundError):
        store.get_response("R-999")
