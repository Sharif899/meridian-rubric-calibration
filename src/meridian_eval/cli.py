"""Command line interface for the Meridian evaluation pipeline.

Canonical pilot run, from the repository root:

    meridian load
    meridian blind
    meridian grade --grader grader-1
    meridian grade --grader grader-2
    meridian llm-grade
    meridian adjudicate
    meridian analyze
    meridian report
    meridian serve

Use `meridian llm-grade --live` instead of `meridian llm-grade` to
score with a real LLM endpoint (MERIDIAN_LLM_ENDPOINT,
MERIDIAN_LLM_API_KEY, MERIDIAN_LLM_MODEL); see the README.

Every step is rerunnable: load, blind, grade, llm-grade and adjudicate
replace their rows rather than duplicating them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .adjudication import adjudicate_pair, adjudication_summary
from .analysis import analyze, revision_impact
from .blind import assign_blinded_ids, double_graded_item_ids
from .dataset import load_items_csv, load_items_jsonl, load_sources
from .errors import MeridianError
from .graders import (
    GRADER_1,
    GRADER_2,
    LIVE_LLM_GRADER,
    LLM_GRADER,
    HttpLLMGrader,
    grade_human,
    grade_llm_mock,
)
from .providers import generate_response
from .report import dumps_json, render_json, render_markdown
from .rubric import load_rubrics
from .store import Store


def _store(args) -> Store:
    return Store(args.db)


def _rubric_version(args) -> str:
    return args.rubric_version


def cmd_load(args) -> int:
    pilot = Path(args.pilot)
    if pilot.suffix == ".csv":
        items = load_items_csv(pilot)
    else:
        items = load_items_jsonl(pilot)
    sources = load_sources(args.sources)
    rubrics = load_rubrics(args.rubrics)
    store = _store(args)
    for item in items:
        store.insert_item(item)
    for source in sources:
        store.insert_source(source)
    for version, payload in rubrics.items():
        store.insert_rubric(version, payload)
    store.set_meta("n_items", str(len(items)))
    store.set_meta("rubric_versions", ",".join(sorted(rubrics)))
    store.commit()
    store.close()
    print(f"loaded {len(items)} items, {len(sources)} sources, "
          f"{len(rubrics)} rubric versions ({', '.join(sorted(rubrics))}) into {args.db}")
    return 0


def cmd_blind(args) -> int:
    store = _store(args)
    items = store.items()
    if not items:
        print("store is empty: run `meridian load` first", file=sys.stderr)
        return 1
    assignment = assign_blinded_ids(store, seed=args.seed)
    for entry in assignment:
        item = store.get_item(entry["item_id"])
        text, profile = generate_response(item, entry["model"])
        store.insert_response(entry["blinded_id"], entry["item_id"], entry["model"], text, profile)
    store.set_meta("blinded", "yes")
    store.commit()
    counts = store.counts()
    store.close()
    print(f"blinded {counts['responses']} responses "
          f"({len(items)} items x 2 models) with seed {args.seed}")
    return 0


def cmd_grade(args) -> int:
    store = _store(args)
    version = _rubric_version(args)
    store.get_rubric(version)
    double_items = set(double_graded_item_ids(store))
    responses = store.responses()
    if args.grader == GRADER_2:
        targets = [r for r in responses if r["item_id"] in double_items]
    elif args.double_only:
        targets = [r for r in responses if r["item_id"] in double_items]
    else:
        targets = responses
    for response in targets:
        item = store.get_item(response["item_id"])
        judgment = grade_human(response["defect_profile"], item, version, args.grader)
        store.insert_human_score(
            response["blinded_id"], args.grader, version,
            judgment["scores"], judgment["evidence_note"], judgment["failure_label"],
        )
    store.commit()
    store.close()
    print(f"{args.grader} scored {len(targets)} blinded responses under rubric {version}")
    return 0


def cmd_llm_grade(args) -> int:
    store = _store(args)
    version = _rubric_version(args)
    rubric = store.get_rubric(version)
    if args.live:
        grader = HttpLLMGrader()
        rows = store.blinded_view()
        for row in rows:
            judgment = grader.grade(row, rubric)
            store.insert_llm_score(
                row["blinded_id"], LIVE_LLM_GRADER, version,
                judgment["scores"], judgment["evidence_note"], judgment["failure_label"],
            )
        store.commit()
        store.close()
        print(f"{LIVE_LLM_GRADER} scored {len(rows)} blinded responses "
              f"under rubric {version} (model {grader.model})")
        return 0
    for response in store.responses():
        item = store.get_item(response["item_id"])
        judgment = grade_llm_mock(
            response["defect_profile"], item, version, response["response_text"],
        )
        store.insert_llm_score(
            response["blinded_id"], LLM_GRADER, version,
            judgment["scores"], judgment["evidence_note"], judgment["failure_label"],
        )
    store.commit()
    counts = store.counts()
    store.close()
    print(f"{LLM_GRADER} scored {counts['llm_scores']} blinded responses under rubric {version}")
    return 0


def cmd_adjudicate(args) -> int:
    store = _store(args)
    version = _rubric_version(args)
    g1 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_1, rubric_version=version)}
    g2 = {s["blinded_id"]: s for s in store.human_scores(grader=GRADER_2, rubric_version=version)}
    for response in store.responses():
        item = store.get_item(response["item_id"])
        s1 = g1.get(response["blinded_id"])
        s2 = g2.get(response["blinded_id"])
        record = adjudicate_pair(
            s1["scores"] if s1 else None,
            s1["failure_label"] if s1 else None,
            s2["scores"] if s2 else None,
            s2["failure_label"] if s2 else None,
            response["defect_profile"],
            item,
        )
        store.insert_adjudication(
            response["blinded_id"],
            s1["scores"] if s1 else None,
            s2["scores"] if s2 else None,
            record["adjudicated_scores"],
            record["failure_label"],
            record["decision"],
            record["rationale"],
        )
    store.commit()
    summary = adjudication_summary(store.adjudications())
    store.close()
    print(f"adjudicated {sum(summary.values())} responses: "
          f"{summary['agreed']} agreed, {summary['adjudicated']} adjudicated, "
          f"{summary['single']} single-graded")
    return 0


def cmd_analyze(args) -> int:
    store = _store(args)
    version = _rubric_version(args)
    analysis = analyze(store, version)
    revision = revision_impact(store)
    meta = {
        "n_items": int(store.get_meta("n_items") or 120),
        "items_per_area": 40,
        "n_responses": store.counts()["responses"],
    }
    store.close()
    if args.out:
        Path(args.out).write_text(
            dumps_json(render_json(analysis, revision, meta)), encoding="utf-8"
        )
        print(f"wrote {args.out}")
    overall = analysis["overall"]
    llm = analysis["llm_vs_adjudicated"]
    print(f"rubric {version}: double-graded N={analysis['n_double_graded_responses']} responses")
    print(f"  overall exact agreement {overall['exact_agreement']:.1%}, "
          f"weighted kappa {overall['weighted_kappa']:.3f}")
    print(f"  pass/fail kappa {analysis['pass_fail']['kappa']:.3f} "
          f"(N={analysis['pass_fail']['n']})")
    print(f"  failure-label agreement {analysis['failure_labels']['exact_agreement']:.1%} "
          f"(kappa {analysis['failure_labels']['kappa']:.3f}, N={analysis['failure_labels']['n']})")
    print(f"  LLM vs adjudicated: mean abs diff {llm['mean_abs_diff']:.2f}, "
          f"diff > 1pt {llm['diff_gt_1_rate']:.1%} (N={llm['n_pairs']} pairs)")
    print(f"  pass rates: model-a {analysis['by_model']['model-a']['pass_rate']:.1%}, "
          f"model-b {analysis['by_model']['model-b']['pass_rate']:.1%}")
    return 0


def cmd_report(args) -> int:
    store = _store(args)
    version = _rubric_version(args)
    analysis = analyze(store, version)
    revision = revision_impact(store)
    meta = {
        "n_items": int(store.get_meta("n_items") or 120),
        "items_per_area": 40,
        "n_responses": store.counts()["responses"],
    }
    store.close()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "analysis.md"
    json_path = out_dir / "analysis.json"
    md_path.write_text(render_markdown(analysis, revision, meta), encoding="utf-8")
    json_path.write_text(dumps_json(render_json(analysis, revision, meta)), encoding="utf-8")
    print(f"wrote {md_path} and {json_path}")
    return 0


def cmd_serve(args) -> int:
    from .web.app import create_app
    import uvicorn

    app = create_app(args.db)
    print(f"serving reviewer UI on http://{args.host}:{args.port} (store: {args.db})")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meridian",
        description="Enterprise LLM rubric evaluation and calibration system.",
    )
    parser.add_argument("--version", action="version", version=f"meridian {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("load", help="import pilot items, sources and rubric versions")
    p.add_argument("--db", default="store.db")
    p.add_argument("--pilot", default="data/pilot.jsonl")
    p.add_argument("--rubrics", default="data/rubrics")
    p.add_argument("--sources", default="data/sources")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("blind", help="generate model responses and assign blinded IDs")
    p.add_argument("--db", default="store.db")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_blind)

    p = sub.add_parser("grade", help="record mock human-grader scores")
    p.add_argument("--db", default="store.db")
    p.add_argument("--grader", choices=[GRADER_1, GRADER_2], required=True)
    p.add_argument("--rubric-version", default="1.0.0")
    p.add_argument("--double-only", action="store_true",
                   help="grade only the double-graded items (grader-2 always does this)")
    p.set_defaults(func=cmd_grade)

    p = sub.add_parser("llm-grade", help="run the LLM grader over all blinded responses (mock by default; --live for a real endpoint)")
    p.add_argument("--db", default="store.db")
    p.add_argument("--rubric-version", default="1.0.0")
    p.add_argument("--live", action="store_true",
                   help="use the HTTP LLM grader (MERIDIAN_LLM_ENDPOINT, MERIDIAN_LLM_API_KEY, "
                        "MERIDIAN_LLM_MODEL) instead of the mock; scores are stored under grader live-llm")
    p.set_defaults(func=cmd_llm_grade)

    p = sub.add_parser("adjudicate", help="resolve grader disagreements with recorded decisions")
    p.add_argument("--db", default="store.db")
    p.add_argument("--rubric-version", default="1.0.0")
    p.set_defaults(func=cmd_adjudicate)

    p = sub.add_parser("analyze", help="compute agreement and calibration metrics")
    p.add_argument("--db", default="store.db")
    p.add_argument("--rubric-version", default="1.0.0")
    p.add_argument("--out", help="optional path for the analysis JSON")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("report", help="export the Markdown + JSON analysis report")
    p.add_argument("--db", default="store.db")
    p.add_argument("--rubric-version", default="1.0.0")
    p.add_argument("--out", default="reports")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("serve", help="start the reviewer web UI")
    p.add_argument("--db", default="store.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MeridianError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
