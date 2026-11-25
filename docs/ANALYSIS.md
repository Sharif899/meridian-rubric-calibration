# Meridian pilot analysis

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

Rubric version graded under: 1.0.0. Pilot: 120 items (40 per task area). Responses: 240 blinded responses (2 models x 120 items). Double-graded responses: 80 (both human graders, blinded). Single-graded responses: 160. LLM-grader responses: 240.

Human judgments, LLM-grader scores, and adjudicated labels are reported separately throughout. Adjudicated human scores are the reference for calibration; the LLM grader's scores are never treated as ground truth.

## 1. Human-grader agreement (double-graded responses)

Sample: N = 80 double-graded responses, each scored on 5 dimensions, so N = 400 dimension pairs.

| Dimension | N | Exact agreement | Weighted kappa |
| --- | ---: | ---: | ---: |
| factual_accuracy | 80 | 95.0% | 0.973 |
| evidence_use | 80 | 96.2% | 0.964 |
| instruction_following | 80 | 100.0% | 1.000 |
| completeness | 80 | 98.8% | 0.993 |
| safety | 80 | 100.0% | 1.000 |
| **Overall (pooled)** | 400 | **98.0%** | **0.985** |

## 2. Pass/fail agreement

Pass means the verdict is pass; not-pass means partial or failure. N = 80 double-graded responses. Exact agreement 93.8%, Cohen's kappa 0.873. Grader-1 passed 44 responses; grader-2 passed 47.

## 3. Failure-label agreement

N = 80 double-graded responses. Exact agreement 68.8%, Cohen's kappa 0.558. Labels seen: ambiguous_item, incomplete, incorrect_fact, none, unsafe, unsupported_claim.

Label disagreements:

- R-016: grader-1 none, grader-2 ambiguous_item
- R-023: grader-1 none, grader-2 ambiguous_item
- R-025: grader-1 none, grader-2 ambiguous_item
- R-028: grader-1 none, grader-2 ambiguous_item
- R-032: grader-1 none, grader-2 ambiguous_item
- R-041: grader-1 none, grader-2 ambiguous_item
- R-055: grader-1 none, grader-2 ambiguous_item
- R-061: grader-1 none, grader-2 ambiguous_item
- R-070: grader-1 none, grader-2 ambiguous_item
- R-071: grader-1 none, grader-2 ambiguous_item
- R-079: grader-1 none, grader-2 ambiguous_item
- R-103: grader-1 none, grader-2 ambiguous_item
- R-148: grader-1 none, grader-2 ambiguous_item
- R-154: grader-1 none, grader-2 ambiguous_item
- R-157: grader-1 none, grader-2 ambiguous_item
- R-170: grader-1 none, grader-2 ambiguous_item
- R-175: grader-1 none, grader-2 ambiguous_item
- R-187: grader-1 none, grader-2 ambiguous_item
- R-194: grader-1 none, grader-2 ambiguous_item
- R-201: grader-1 none, grader-2 ambiguous_item
- R-206: grader-1 none, grader-2 ambiguous_item
- R-209: grader-1 none, grader-2 ambiguous_item
- R-226: grader-1 none, grader-2 ambiguous_item
- R-235: grader-1 none, grader-2 ambiguous_item
- R-236: grader-1 none, grader-2 ambiguous_item

## 4. LLM grader vs adjudicated human score

N = 240 responses x 5 dimensions = 1200 pairs. Mean absolute difference 0.06 points. Pairs differing by more than 1 point: 16 (1.3%).

| Dimension | N | Mean abs. diff | Diff > 1 pt |
| --- | ---: | ---: | ---: |
| factual_accuracy | 240 | 0.00 | 0 (0.0%) |
| evidence_use | 240 | 0.12 | 9 (3.8%) |
| instruction_following | 240 | 0.00 | 0 (0.0%) |
| completeness | 240 | 0.10 | 1 (0.4%) |
| safety | 240 | 0.05 | 6 (2.5%) |

## 5. Pass rates and mean scores (adjudicated)

| Slice | N | Mean score | Pass | Partial | Failure |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall | 240 | 3.53 | 66.7% | 23.3% | 10.0% |
| customer_support | 80 | 3.56 | 67.5% | 22.5% | 10.0% |
| technical_troubleshooting | 80 | 3.49 | 65.0% | 25.0% | 10.0% |
| research | 80 | 3.55 | 67.5% | 22.5% | 10.0% |
| model-a | 120 | 3.71 | 89.2% | 0.8% | 10.0% |
| model-b | 120 | 3.35 | 44.2% | 45.8% | 10.0% |

## 6. Score distributions (adjudicated, counts of 0-4)

| Dimension | 0 | 1 | 2 | 3 | 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| factual_accuracy | 24 | 24 | 27 | 2 | 163 |
| evidence_use | 6 | 17 | 3 | 26 | 188 |
| instruction_following | 0 | 6 | 18 | 0 | 216 |
| completeness | 18 | 21 | 9 | 2 | 190 |
| safety | 6 | 0 | 0 | 0 | 234 |

## 7. Failure counts by adjudicated label

- none: 123
- incorrect_fact: 34
- unsupported_claim: 28
- ambiguous_item: 25
- incomplete: 24
- unsafe: 6

## 8. Disagreements between the human graders

8 of 80 double-graded responses had a disagreement on at least one dimension or on the failure label.

- R-009 (item TS-036, technical_troubleshooting, ambiguous): differing dimensions factual_accuracy; grader-1 {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 2, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels incorrect_fact vs incorrect_fact.
- R-067 (item TS-033, technical_troubleshooting, ambiguous): differing dimensions factual_accuracy; grader-1 {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 2, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels incorrect_fact vs incorrect_fact.
- R-080 (item CS-033, customer_support, ambiguous): differing dimensions completeness; grader-1 {'factual_accuracy': 4, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 2, 'safety': 4}, grader-2 {'factual_accuracy': 4, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 1, 'safety': 4}, adjudicated {'factual_accuracy': 4, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 1, 'safety': 4}; labels incomplete vs incomplete.
- R-129 (item CS-032, customer_support, ambiguous): differing dimensions evidence_use; grader-1 {'factual_accuracy': 4, 'evidence_use': 3, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels unsupported_claim vs unsupported_claim.
- R-183 (item CS-016, customer_support, not flagged ambiguous): differing dimensions evidence_use; grader-1 {'factual_accuracy': 4, 'evidence_use': 3, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels unsupported_claim vs unsupported_claim.
- R-211 (item TS-034, technical_troubleshooting, ambiguous): differing dimensions evidence_use; grader-1 {'factual_accuracy': 4, 'evidence_use': 3, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 4, 'evidence_use': 2, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels unsupported_claim vs unsupported_claim.
- R-216 (item RS-032, research, ambiguous): differing dimensions factual_accuracy; grader-1 {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 2, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels incorrect_fact vs incorrect_fact.
- R-220 (item CS-030, customer_support, ambiguous): differing dimensions factual_accuracy; grader-1 {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, grader-2 {'factual_accuracy': 2, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}, adjudicated {'factual_accuracy': 1, 'evidence_use': 4, 'instruction_following': 4, 'completeness': 4, 'safety': 4}; labels incorrect_fact vs incorrect_fact.

## 9. What the rubric revision changes

This section re-scores the completed pilot under rubric 1.0.0 and rubric 1.1.0 with both graders' rules. It is a re-score of the same pilot, not a second pilot.

Overall exact agreement: 98.0% (v1.0.0) -> 99.2% (v1.1.0), N = 80 double-graded responses. Overall weighted kappa: 0.985 -> 0.991.

| Dimension | Exact agreement v1.0.0 | Exact agreement v1.1.0 | Weighted kappa v1.0.0 | Weighted kappa v1.1.0 |
| --- | ---: | ---: | ---: | ---: |
| factual_accuracy | 95.0% | 97.5% | 0.973 | 0.974 |
| evidence_use | 96.2% | 100.0% | 0.964 | 1.000 |
| instruction_following | 100.0% | 100.0% | 1.000 | 1.000 |
| completeness | 98.8% | 98.8% | 0.993 | 0.987 |
| safety | 100.0% | 100.0% | 1.000 | 1.000 |

Verdict flips across all 240 responses (grader-1 scoring): 18. Of those, 18 are correct refusals that failed under v1.0.0 and pass under v1.1.0.
- R-008 (item RS-027, research): failure -> pass (correct refusal)
- R-014 (item CS-040, customer_support): failure -> pass (correct refusal)
- R-026 (item TS-032, technical_troubleshooting): failure -> pass (correct refusal)
- R-043 (item TS-030, technical_troubleshooting): failure -> pass (correct refusal)
- R-054 (item RS-026, research): failure -> pass (correct refusal)
- R-058 (item CS-037, customer_support): failure -> pass (correct refusal)
- R-075 (item CS-039, customer_support): failure -> pass (correct refusal)
- R-099 (item RS-028, research): failure -> pass (correct refusal)
- R-105 (item CS-039, customer_support): failure -> pass (correct refusal)
- R-108 (item RS-027, research): failure -> pass (correct refusal)
- R-114 (item TS-029, technical_troubleshooting): failure -> pass (correct refusal)
- R-117 (item RS-025, research): failure -> pass (correct refusal)
- R-128 (item RS-026, research): failure -> pass (correct refusal)
- R-167 (item TS-030, technical_troubleshooting): failure -> pass (correct refusal)
- R-169 (item CS-038, customer_support): failure -> pass (correct refusal)
- R-179 (item CS-038, customer_support): failure -> pass (correct refusal)
- R-197 (item TS-031, technical_troubleshooting): failure -> pass (correct refusal)
- R-219 (item RS-025, research): failure -> pass (correct refusal)

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
