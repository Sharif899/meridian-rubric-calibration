"""Assemble docs/ANALYSIS.md from the generated pipeline report.

Run after a full pipeline run: python scripts/build_analysis_doc.py
Reads reports/analysis.md (generated, gitignored) and wraps it with an
introduction and an interpretation section. The numbers in the tables
come from the pipeline run itself; the interpretation is written against
those numbers and must be re-checked if the pilot changes.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INTRO = """# Meridian pilot analysis

## What was run

- Pilot: 120 items, 40 per task area (customer support, technical
  troubleshooting, research grounded in reference documents).
- Responses: 240 blinded responses, two mock models (model-a, model-b)
  answering all 120 items.
- Human grading: every response scored by grader-1; 80 responses (40 items,
  all 20 ambiguous items, all 12 refusal items, plus 8 stratified items)
  independently double-graded by grader-2, blinded, without seeing model
  identity or each other's scores.
- LLM grading: the mock LLM grader scored all 240 blinded responses.
- Adjudication: all 80 double-graded responses went through adjudication;
  47 agreed outright, 33 were adjudicated with a recorded decision and
  rationale. The remaining 160 responses are single-graded.
- Rubric version graded under: 1.0.0. Section 9 re-scores the same pilot
  under 1.1.0; that is a re-score of the same pilot, not a second pilot.

## How to read this report

Human judgments, LLM-grader scores, and adjudicated labels are reported
separately throughout. Adjudicated human scores are the reference for
calibration. The LLM grader's scores are never treated as ground truth.

Every number below is the output of running the pipeline on the pilot
data. Nothing in this report is an estimate, a target, or a projection.
The committed sample export of the same analysis is
reports/sample-analysis.json.

"""

INTERPRETATION = """
## What the numbers mean

### Score agreement is high; label agreement is not

Overall exact agreement on dimension scores is 98.0% (weighted kappa
0.985, N = 400 dimension pairs). The 8 score disagreements are all
one-point splits, and all 8 sit on the three unclear points in rubric
v1.0.0: four on factual accuracy where a core error met the "partly
correct = 2" guidance (grader-1 scored 1 from the anchor, grader-2
scored 2 from the guidance), three on evidence use where the response
cited a related source instead of the governing one (grader-1 scored 3,
grader-2 scored 2), and one on completeness for an abridged answer to
an ambiguous item (grader-1 scored 2, grader-2 scored 1). Pass/fail
agreement is 93.8% (kappa 0.873, N = 80); the five pass/fail splits are
all one-point score differences that cross the mean >= 3.0 line.

Failure-label agreement is 68.8% (kappa 0.558, N = 80), and all 25
disagreements are the same pattern: grader-1 labels a clean response to
an ambiguous item "none", grader-2 labels it "ambiguous_item". The
graders never disagree about which defect a response has. They disagree
about whether a clean answer to an ambiguous item should carry the
ambiguous_item label. That is a labelling-rule gap, not a judgement gap,
and it is what the v1.1.0 escalation rule is written to close.

### The 10% failure rate is a rubric artefact, not a model difference

All 24 adjudicated failures are the 12 refusal items (4 per area, 2
models each). Under v1.0.0 every correct refusal fails (completeness 0,
factual accuracy 0) and every compliance fails (safety 0). Model-a's 12
failures are all correct refusals; model-b's 12 are 6 correct refusals
plus 6 compliances. The real model gap is pass versus partial:
model-a passes 89.2% and is partial 0.8% of the time; model-b passes
44.2% and is partial 45.8% of the time. Model-b's partial verdicts come
from unsupported claims (28 adjudicated) and incorrect facts (34): its
answers are fluent and complete-looking, which is exactly why the LLM
grader's completeness over-score matters.

### The LLM grader is close on average and wrong where it matters

Mean absolute difference from the adjudicated score is 0.06 points,
and 16 of 1200 pairs (1.3%) differ by more than one point. The misses
concentrate on evidence use (9 of 240, 3.8%), the blind spot for
unsupported claims, and safety (6 of 240, 2.5%), compliances scored 2
instead of 0. On factual accuracy and instruction following it never
differs by more than one point. The LLM grader must not be used as a
gate on evidence or safety until those two biases are measured on real
data.

### Coverage gaps in this pilot

Instruction following never scores 3 in the pilot (0 of 240 responses).
No defect in the mock models produces a trivial format deviation, so
the 3 anchor for that dimension is untested. This is a coverage gap in
the pilot, not a rubric problem, and it is recorded here rather than
engineered away.

Five reference answers were corrected for date arithmetic on
2026-11-25 (four return-window deadlines that did not equal delivery
plus 30 days, and one late-fee item whose invoice date, due date,
payment date, days overdue and fee did not agree with each other or
with KB-BIL-01; the re-scan also fixed the same late-fee error in the
three sibling items). The correction changed one pilot number. The
corrected late-fee reference has three sentences instead of two, so
model-b's incomplete-answer rule drops a core element rather than a
secondary one on response R-174 (CS-025, model-b), moving it from pass
to partial: model-b's pass rate is 44.2% (was 45.0%), the overall pass
rate is 66.7% (was 67.1%), and customer support passes 67.5% (was
68.8%). Every agreement metric is unchanged. The generator
(scripts/build_pilot.py) now computes the deadlines and the late-fee
timeline instead of drawing them independently, and a regeneration
produces the corrected data byte for byte.

### What v1.1.0 changes

Re-scoring the same pilot under v1.1.0 moves overall exact agreement
from 98.0% to 99.2% and weighted kappa from 0.985 to 0.991. Evidence-use
agreement reaches 100%: the related-versus-governing split is closed.
Factual accuracy rises to 97.5% but does not reach 100%: under v1.1.0
the peripheral-error judgement splits 3 (grader-1, minor) against 2
(grader-2, matters), a smaller disagreement than the 1-versus-2 split
it replaced. Completeness exact agreement is unchanged at 98.8%; its
weighted kappa moves 0.993 to 0.987, a marginal-distribution effect,
not a real worsening. Eighteen verdicts flip, all of them correct
refusals moving from failure to pass. The revision fixes the rubric; it
does not change what the models did.

## Limitations

- Mock graders and mock models. The agreement numbers measure the
  rubric's clarity under two simulated graders with documented
  tendencies, not the agreement of real graders. They show the rubric
  can be applied consistently; they do not show that real graders will
  agree.
- The pilot is 120 items, 40 per area. Kappa values at this size have
  wide confidence intervals; read 0.985 as "high in this pilot", not as
  a guarantee.
- The LLM grader in this run is a rule-based mock with documented
  biases. Its 1.3% rate of differences over one point is a property of
  the mock, not of any real LLM grader.
- Re-scoring under v1.1.0 is a re-score of the same pilot, not a second
  pilot. A fresh pilot run under v1.1.0 is the real test of the revision.
"""


def main() -> None:
    generated = (ROOT / "reports" / "analysis.md").read_text(encoding="utf-8")
    # Drop the generated title line; the intro supplies the heading.
    body = generated.split("\n", 1)[1].lstrip("\n")
    out = INTRO + body.rstrip() + "\n\n" + INTERPRETATION.strip() + "\n"
    path = ROOT / "docs" / "ANALYSIS.md"
    path.write_text(out, encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
