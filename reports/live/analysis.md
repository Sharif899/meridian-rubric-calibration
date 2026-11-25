# Meridian pilot analysis report

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

N = 240 responses x 5 dimensions = 1200 pairs. Mean absolute difference 0.44 points. Pairs differing by more than 1 point: 124 (10.3%).

| Dimension | N | Mean abs. diff | Diff > 1 pt |
| --- | ---: | ---: | ---: |
| factual_accuracy | 240 | 0.60 | 30 (12.5%) |
| evidence_use | 240 | 0.57 | 32 (13.3%) |
| instruction_following | 240 | 0.34 | 25 (10.4%) |
| completeness | 240 | 0.65 | 34 (14.2%) |
| safety | 240 | 0.03 | 3 (1.2%) |

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
