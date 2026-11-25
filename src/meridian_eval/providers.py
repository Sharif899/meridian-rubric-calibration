"""Mock model providers.

Two deterministic mock models produce a response for every pilot item.
They are simulations, not language models, and the README says so plainly.
What is being tested is the evaluation system (blinding, agreement,
calibration) — not the models' language ability.

model-a — careful, evidence-grounded. Usually gives the reference answer
unchanged. Occasionally drops the last sentence (an abridged answer) or
slips on a peripheral detail (a card ending, a date). On refusal items
(prompts that should be refused) it always refuses correctly, with the
reason and the compliant route.

model-b — fluent but sloppier. On a deterministic schedule it:
- states a core fact wrong (the item's wrong_number pair),
- asserts an unsupported claim (the item's fabricated sentence),
- gives an incomplete answer (the core element dropped),
- cites a related source instead of the governing one,
- or, on refusal items, complies with a request that should have been
  refused (using the item's fabricated sentence as the non-compliant
  advice).

The schedule is a seeded draw per (model, item) — a SHA-256 hash of the
model and item id seeds a Random instance — so it is deterministic across
runs but varies naturally across task areas instead of repeating the same
pattern in every area. Approximate rates for non-refusal items:
model-a: 64% clean, 8% trivial wording imprecision, 15% abridged
(a minor elaboration or a secondary element dropped), 13% peripheral slip.
model-b: 28% clean, 20% wrong fact, 20% unsupported claim, 15%
incomplete, 17% wrong source. On refusal items model-b complies about
two thirds of the time.

Every response carries a defect profile: a record of what the response
contains. The mock graders score from that profile, which is the
deterministic stand-in for "a grader read the response and found the
defect". The response text is generated to match the profile, so a human
reading the text sees the same defect the profile records. The profile
is stored in the sealed part of the store and never shown to graders.
"""

from __future__ import annotations

import hashlib
import random
import re

MODEL_A = "model-a"
MODEL_B = "model-b"

MODELS = (MODEL_A, MODEL_B)


def _rng(model: str, item_id: str) -> random.Random:
    """Deterministic per-(model, item) random draw, stable across runs."""
    digest = hashlib.sha256(f"meridian:{model}:{item_id}".encode()).hexdigest()
    return random.Random(int(digest[:8], 16))


def is_refusal_item(item: dict) -> bool:
    """True when the reference answer is a refusal (the prompt should be refused)."""
    return item["reference_answer"].startswith("I cannot")


def empty_profile() -> dict:
    return {
        "unsupported_claim": False,
        "wrong_core_fact": False,
        "wrong_peripheral": False,
        "trivial_imprecision": False,
        "missing_core": False,
        "missing_secondary": False,
        "minor_elaboration_missing": False,
        "cites_related_not_governing": False,
        "uncited_minor_claim": False,
        "refusal": False,
        "refusal_correct": False,
        "refusal_explained": False,
        "complies_with_unsafe": False,
        "unsafe_advice": False,
        "ignores_instruction": False,
        "misses_secondary_instruction": False,
    }


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def _peripheral_candidates(item: dict) -> list[str]:
    """Key facts that are secondary details: they contain a digit, are not
    the core number (the wrong_number pair), not a source id, not a
    shipment id, and not a bare status code (429, 401, 403, 200)."""
    wrong_correct = item["mock_notes"]["wrong_number"][0]
    out = []
    for fact in item["key_facts"]:
        if fact == wrong_correct:
            continue
        if fact in item["source_ids"]:
            continue
        if re.search(r"MF-\d+", fact):
            continue
        if re.fullmatch(r"\d{3}", fact):
            continue
        if re.search(r"\d", fact):
            out.append(fact)
    return out


def mutate_peripheral(item: dict, reference: str) -> tuple[str, str] | None:
    """Change one peripheral detail in the reference: the last digit of
    the first digit run in the first secondary key fact. Returns
    (new_text, description) or None when the item has no secondary
    number to slip on.
    """
    for fact in _peripheral_candidates(item):
        match = re.search(r"\d+", fact)
        if not match:
            continue
        run = match.group(0)
        new_digit = str((int(run[-1]) + 1) % 10)
        new_run = run[:-1] + new_digit
        new_fact = fact[:match.start()] + new_run + fact[match.end():]
        if new_fact == fact:
            continue
        return reference.replace(fact, new_fact, 1), f"{fact!r} -> {new_fact!r}"
    return None


_TRIVIAL_REPHRASES = [
    (" USD", " dollars"),
    ("%", " percent"),
    (" per minute", " a minute"),
    ("HTTP 200", "a 200 response"),
    ("business days", "working days"),
]


def trivial_rephrase(reference: str) -> str | None:
    """Reword one figure without changing the fact. Returns the new text
    or None when no rephrase applies."""
    for old, new in _TRIVIAL_REPHRASES:
        if old in reference:
            return reference.replace(old, new, 1)
    return None


def generate_response(item: dict, model: str) -> tuple[str, dict]:
    """Generate one model's response for one pilot item.

    Returns (response_text, defect_profile). Deterministic: the defect
    is a seeded draw per (model, item).
    """
    reference = item["reference_answer"]
    notes = item["mock_notes"]
    profile = empty_profile()

    if model == MODEL_A:
        return _model_a(item, reference, notes, profile)
    if model == MODEL_B:
        return _model_b(item, reference, notes, profile)
    raise ValueError(f"unknown model {model!r}")


def _model_a(item, reference, notes, profile):
    if is_refusal_item(item):
        profile["refusal"] = True
        profile["refusal_correct"] = True
        profile["refusal_explained"] = True
        return reference, profile
    roll = _rng(MODEL_A, item["id"]).random()
    if roll < 0.08:
        # Trivial wording imprecision: same fact, worded differently.
        rephrased = trivial_rephrase(reference)
        if rephrased is not None:
            profile["trivial_imprecision"] = True
            return rephrased, profile
    elif roll < 0.23:
        sentences = split_sentences(reference)
        if len(sentences) >= 2:
            dropped = sentences[-1]
            if any(phrase in dropped for phrase in
                   ("reply here", "let us know", "hear back", "flagged",
                    "will reply", "asked billing", "escalated")):
                # A minor elaboration, not a required element.
                profile["minor_elaboration_missing"] = True
            else:
                profile["missing_secondary"] = True
            return " ".join(sentences[:-1]), profile
    elif roll < 0.36:
        mutated = mutate_peripheral(item, reference)
        if mutated is not None:
            text, _ = mutated
            profile["wrong_peripheral"] = True
            return text, profile
    return reference, profile


def _model_b(item, reference, notes, profile):
    if is_refusal_item(item):
        if _rng(MODEL_B, item["id"]).random() < 0.67:
            profile["complies_with_unsafe"] = True
            profile["unsafe_advice"] = True
            profile["wrong_core_fact"] = True
            profile["unsupported_claim"] = True
            lead = "Here is how to do it. "
            return lead + notes["fabricated_sentence"], profile
        profile["refusal"] = True
        profile["refusal_correct"] = True
        profile["refusal_explained"] = True
        return reference, profile
    roll = _rng(MODEL_B, item["id"]).random()
    if roll < 0.20:
        correct, wrong = notes["wrong_number"]
        assert correct in reference, f"wrong_number {correct!r} not in reference for {item['id']}"
        profile["wrong_core_fact"] = True
        return reference.replace(correct, wrong, 1), profile
    if roll < 0.40:
        profile["unsupported_claim"] = True
        return reference + " " + notes["fabricated_sentence"], profile
    if roll < 0.55:
        sentences = split_sentences(reference)
        if len(sentences) >= 3:
            profile["missing_core"] = True
            return " ".join(sentences[:2]), profile
        if len(sentences) == 2:
            profile["missing_secondary"] = True
            return sentences[0], profile
        return reference, profile
    if roll < 0.72:
        governing = item["source_ids"][0]
        related = notes["related_source"]
        assert governing in reference, f"governing source {governing} not in reference for {item['id']}"
        profile["cites_related_not_governing"] = True
        return reference.replace(governing, related), profile
    return reference, profile


def describe_model(model: str) -> str:
    if model == MODEL_A:
        return (
            "model-a is careful and evidence-grounded: it usually gives the reference "
            "answer unchanged, occasionally drops a secondary element, and rarely slips "
            "on a peripheral detail. It always refuses correctly where a refusal is due."
        )
    if model == MODEL_B:
        return (
            "model-b is fluent but sloppier: on a deterministic schedule it states a core "
            "fact wrong, asserts an unsupported claim, gives an incomplete answer, cites a "
            "related source instead of the governing one, and complies with requests that "
            "should have been refused."
        )
    raise ValueError(f"unknown model {model!r}")
