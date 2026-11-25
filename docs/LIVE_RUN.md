# Meridian pilot — live LLM grader run

This is the live-model counterpart to the mock-grader pilot in
[`docs/ANALYSIS.md`](ANALYSIS.md). The mock-run numbers in that document are
unchanged. Everything below comes from a single live run against a real
Gemini model on the same pilot, the same rubric, and the same human
judgments. Human scores and adjudications are identical in both runs, so
every difference below is the grader, not the data.

- **Date:** 25 November 2026, 19:18–19:59 UTC (first call to last call)
- **Model:** `gemini-3.5-flash-lite` (Google Gemini API, free tier)
- **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
  (OpenAI-compatible chat completions; temperature 0; the grader posts the
  rubric, the reference answer, the source evidence and the blinded response,
  and parses the reply as JSON)
- **Rubric version graded under:** 1.0.0
- **Pilot:** 120 items (40 per task area), 240 blinded responses
  (2 models x 120 items), 80 double-graded by two human graders,
  160 single-graded, 240 adjudicated
- **Why this model:** `gemini-2.5-flash` is no longer offered to new API
  keys (404, Google directs new keys to the 3.x series), and
  `gemini-3.8-flash` returned 503 "high demand" twice on the day and its
  reported daily limit (~20 requests) would not have fitted 240 calls.
  `gemini-3.5-flash-lite` answered 200 on the first test call and its
  reported daily limit (~500 requests) fits the run.

## Run record

- **240 of 240 live calls completed, 0 failed.** Every blinded response has
  a live-llm score in the live store.
- **6 retries, all transient HTTP 503s** (R-025, R-064, R-083, R-102, R-136,
  R-141), each recovered on the first retry after a 15-second backoff.
- **No 429s and no quota exhaustion.** Total endpoint calls on the day:
  240 gradings + 6 retries + 2 earlier test calls = 248, inside the
  reported ~500/day free-tier limit for this model.
- **Throttled:** 6.5 seconds between calls (~7 requests/minute), per-row
  commits, resumable. Wall clock for the grading calls was about 35
  minutes; 41 minutes end to end including setup.
- The run was executed in resumable chunks: the first background attempt
  was terminated by the harness after 43 seconds with 6 rows already
  scored; those 6 rows were reused on resume and no work was lost.
  The live store (`store-live.db`, gitignored) holds only `live-llm` rows
  (240); the delivered mock-run store (`store.db`, 240 `mock-llm` rows)
  was not touched.
- The analysis was computed with the project's own commands on the live
  store (`meridian analyze --db store-live.db`, `meridian report --db
  store-live.db --out reports/live`). Full machine-readable output:
  `reports/live/analysis.json`; rendered report: `reports/live/analysis.md`.

## Live grader vs adjudicated human score

N = 240 responses x 5 dimensions = 1200 pairs. Adjudicated human scores
are the reference; the live grader's scores are never treated as ground
truth.

| Dimension | Live mean abs. diff | Live diff > 1 pt | Mock mean abs. diff | Mock diff > 1 pt |
| --- | ---: | ---: | ---: | ---: |
| factual_accuracy | 0.60 | 30 (12.5%) | 0.00 | 0 (0.0%) |
| evidence_use | 0.57 | 32 (13.3%) | 0.12 | 9 (3.8%) |
| instruction_following | 0.34 | 25 (10.4%) | 0.00 | 0 (0.0%) |
| completeness | 0.65 | 34 (14.2%) | 0.10 | 1 (0.4%) |
| safety | 0.03 | 3 (1.2%) | 0.05 | 6 (2.5%) |
| **Overall** | **0.44** | **124 (10.3%)** | **0.06** | **16 (1.3%)** |

The mock grader was unrealistically close to the humans: it differed by
more than a point on only 1.3% of pairs. The real model differs by more
than a point on 10.3% — roughly eight times as often — and its mean
absolute difference is 0.44 points against the mock's 0.06. That is the
headline of this run: a deterministic mock flatters a grader. A live
model does not.

## Which way the live grader leans

Signed difference = live score minus adjudicated score, per dimension
(N = 240 each).

| Dimension | Mean signed diff | Live higher | Live lower | Equal |
| --- | ---: | ---: | ---: | ---: |
| factual_accuracy | +0.09 | 29 | 47 | 164 |
| evidence_use | −0.21 | 34 | 67 | 139 |
| instruction_following | −0.03 | 19 | 38 | 183 |
| completeness | +0.27 | 41 | 43 | 156 |
| safety | +0.01 | 2 | 1 | 237 |

Two real tendencies, both worth calibrating against:

- **Evidence use: the live grader is stricter than the humans**
  (−0.21). It marks responses down for evidence the adjudicated human
  score accepted. This is the dimension where it disagrees most often in
  the harsh direction.
- **Completeness: the live grader is more lenient** (+0.27). It credits
  responses the humans judged incomplete.

At the verdict level the live grader is clearly more lenient overall:

| Verdict | Live grader | Adjudicated human |
| --- | ---: | ---: |
| Pass | 192 (80.0%) | 160 (66.7%) |
| Partial | 35 (14.6%) | 56 (23.3%) |
| Failure | 13 (5.4%) | 24 (10.0%) |

Verdict agreement between the live grader and the adjudicated human
score is 181/240 (75.4%). Failure-label agreement is 176/240 (73.3%).

And the overall means hide all of it: the live grader's mean score is
3.555 against the adjudicated 3.53 — nearly identical — while the
per-response disagreement averages 0.44 points. An average is not a
calibration result. This run exists because the brief says so: do not
hide disagreement behind an average score.

## Human agreement — unchanged

The human side of this run is byte-identical to the mock run (same human
scores, same adjudications), so these figures are the same as in
`docs/ANALYSIS.md` and are repeated here only to show that nothing about
the human calibration moved:

| Measure | Value | N |
| --- | ---: | ---: |
| Exact agreement, overall (pooled) | 98.0% | 400 dimension pairs |
| Weighted Cohen's kappa, overall | 0.985 | 400 |
| Pass/fail exact agreement / kappa | 93.8% / 0.873 | 80 responses |
| Failure-label agreement / kappa | 68.8% / 0.558 | 80 responses |

Pass rates (adjudicated, unchanged): overall 66.7%; customer support
67.5%, technical troubleshooting 65.0%, research 67.5%; model-a 89.2%
(mean 3.71), model-b 44.2% (mean 3.35). Rubric revision re-score is
unchanged: exact agreement 98.0% → 99.2%, weighted kappa 0.985 → 0.991,
18 verdict flips, all correct refusals (failure → pass).

## What this means

1. **The live grader is not a human replacement.** At 10.3% of pairs
   more than a point from adjudication and 75.4% verdict agreement, it
   is a useful first pass and a poor final judge. Human review of its
   disagreements is where the value is.
2. **Calibrate per dimension, not per model.** Evidence use needs the
   grader reined in (or the rubric's evidence anchors sharpened);
   completeness needs it tightened. A single "grader quality" number
   would miss both.
3. **The mock run's job was to prove the pipeline, not the grader.**
   The pipeline, the blinding, the adjudication record and the analysis
   all reproduced exactly under a live model. The grader numbers are
   the only thing that moved, which is what a calibration pilot is for.

## Limitations (read before quoting these numbers)

- **Free-tier model.** `gemini-3.5-flash-lite` is the smallest, fastest
  Gemini model. A larger model would grade differently; these numbers
  describe this model, on this pilot, on this day — not "LLM graders"
  in general.
- **Single run.** One pass, temperature 0, no retries of the grading
  itself beyond the transport-level 503 retries. No prompt tuning was
  done; the grader prompt is the rubric text plus the reference answer
  and sources, exactly as the mock grader received them.
- **Free-tier data terms.** Google may use free-tier prompts to improve
  its products. Nothing sensitive was sent: the pilot items, references
  and responses are synthetic, and no client data was involved.
- **The 503s.** Six transient overload responses, all recovered on
  first retry. If the model is busier on another day, the same run
  takes longer; the runner retries 429/5xx with backoff and stops
  hard on daily-quota exhaustion rather than looping.

## Reproduce

```bash
# Live store: load, blind, grade both human graders, live LLM grade,
# adjudicate, analyse, report. The API key comes from the environment
# only; never commit it.
MERIDIAN_LLM_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
MERIDIAN_LLM_API_KEY=<from the secure vault>
MERIDIAN_LLM_MODEL=gemini-3.5-flash-lite

meridian load --db store-live.db
meridian blind --db store-live.db
meridian grade --db store-live.db --grader grader-1
meridian grade --db store-live.db --grader grader-2
meridian llm-grade --db store-live.db --live
meridian adjudicate --db store-live.db
meridian analyze --db store-live.db --out reports/live/analysis.json
meridian report --db store-live.db --out reports/live
```

The throttled, resumable form of the live grading step (6.5 s between
calls, backoff on 429/5xx, per-row commits, resume by skipping
already-scored rows) is the runner used for this run; the
`meridian llm-grade --live` command above is the same grader without
the throttle. On the free tier, run the throttled form or expect
rate-limit failures.
