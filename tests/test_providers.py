"""Mock model providers: deterministic behaviour, text matches the defect profile."""

from meridian_eval.providers import (
    MODEL_A,
    MODEL_B,
    describe_model,
    generate_response,
    is_refusal_item,
    mutate_peripheral,
    split_sentences,
    trivial_rephrase,
)


def _item(items, item_id):
    return next(it for it in items if it["id"] == item_id)


def test_model_a_refusal_is_always_correct(items):
    refusal = next(it for it in items if is_refusal_item(it))
    text, profile = generate_response(refusal, MODEL_A)
    assert text == refusal["reference_answer"]
    assert profile["refusal"] and profile["refusal_correct"] and profile["refusal_explained"]


def test_model_b_complies_or_refuses_on_refusal_items(items):
    refusals = [it for it in items if is_refusal_item(it)]
    complies = 0
    correct = 0
    for it in refusals:
        text, profile = generate_response(it, MODEL_B)
        if profile["complies_with_unsafe"]:
            complies += 1
            assert profile["unsafe_advice"] and profile["wrong_core_fact"]
            assert it["mock_notes"]["fabricated_sentence"] in text
        else:
            correct += 1
            assert profile["refusal_correct"]
    assert complies > 0 and correct > 0
    assert complies + correct == len(refusals)


def test_generation_is_deterministic(items):
    item = _item(items, "CS-001")
    assert generate_response(item, MODEL_A) == generate_response(item, MODEL_A)
    assert generate_response(item, MODEL_B) == generate_response(item, MODEL_B)


def test_model_a_clean_response_equals_reference(items):
    # Find an item where model-a is clean (no defect flags set).
    for it in items:
        if is_refusal_item(it):
            continue
        text, profile = generate_response(it, MODEL_A)
        if not any(profile.values()):
            assert text == it["reference_answer"]
            return
    raise AssertionError("no clean model-a response found")


def test_model_b_wrong_fact_replaces_the_number(items):
    for it in items:
        text, profile = generate_response(it, MODEL_B)
        if profile["wrong_core_fact"] and not profile["complies_with_unsafe"]:
            correct, wrong = it["mock_notes"]["wrong_number"]
            assert wrong in text
            assert text != it["reference_answer"]
            return
    raise AssertionError("no wrong-fact model-b response found")


def test_model_b_unsupported_claim_appends_the_fabrication(items):
    for it in items:
        text, profile = generate_response(it, MODEL_B)
        if profile["unsupported_claim"] and not profile["complies_with_unsafe"]:
            assert it["mock_notes"]["fabricated_sentence"] in text
            return
    raise AssertionError("no unsupported-claim model-b response found")


def test_model_b_wrong_source_cites_the_related_source(items):
    for it in items:
        text, profile = generate_response(it, MODEL_B)
        if profile["cites_related_not_governing"]:
            assert it["mock_notes"]["related_source"] in text
            assert it["source_ids"][0] not in text
            return
    raise AssertionError("no wrong-source model-b response found")


def test_incomplete_response_drops_sentences(items):
    for it in items:
        text, profile = generate_response(it, MODEL_B)
        if profile["missing_core"]:
            assert len(split_sentences(text)) < len(split_sentences(it["reference_answer"]))
            return
    raise AssertionError("no missing-core model-b response found")


def test_abridged_response_drops_the_last_sentence(items):
    for it in items:
        text, profile = generate_response(it, MODEL_A)
        if profile["missing_secondary"] or profile["minor_elaboration_missing"]:
            assert text == " ".join(split_sentences(it["reference_answer"])[:-1])
            return
    raise AssertionError("no abridged model-a response found")


def test_peripheral_mutation_changes_a_secondary_number(items):
    for it in items:
        if is_refusal_item(it):
            continue
        text, profile = generate_response(it, MODEL_A)
        if profile["wrong_peripheral"]:
            assert text != it["reference_answer"]
            return
    raise AssertionError("no peripheral-slip model-a response found")


def test_trivial_rephrase_keeps_the_fact(items):
    for it in items:
        text, profile = generate_response(it, MODEL_A)
        if profile["trivial_imprecision"]:
            assert text != it["reference_answer"]
            return
    raise AssertionError("no trivial-imprecision model-a response found")


def test_mutate_peripheral_returns_none_without_a_secondary_number():
    item = {
        "id": "XX-001", "area": "research", "prompt": "p",
        "reference_answer": "The answer is yes.",
        "source_ids": ["DOC-SLA-03"], "key_facts": ["yes"],
        "difficulty": "straightforward", "ambiguous": False,
        "mock_notes": {"wrong_number": ["a", "b"], "fabricated_sentence": "c",
                       "related_source": "DOC-PRC-01"},
    }
    assert mutate_peripheral(item, item["reference_answer"]) is None


def test_trivial_rephrase_returns_none_without_a_match():
    assert trivial_rephrase("Nothing to rephrase here.") is None
    assert trivial_rephrase("It costs 5 dollars.") is None


def test_split_sentences():
    assert split_sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]
    assert split_sentences("Single sentence.") == ["Single sentence."]


def test_describe_model():
    assert "careful" in describe_model(MODEL_A)
    assert "sloppier" in describe_model(MODEL_B)
    import pytest
    with pytest.raises(ValueError):
        describe_model("model-c")
    with pytest.raises(ValueError):
        generate_response({"id": "x", "reference_answer": "y",
                           "mock_notes": {"wrong_number": ["a", "b"],
                                          "fabricated_sentence": "c",
                                          "related_source": "d"}},
                          "model-c")
