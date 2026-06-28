"""Golden dataset evaluation CLI entry point.

Usage:
    uv run python tests/evals/script_eval.py --validate-only
    uv run python tests/evals/script_eval.py --entry rival-chef-s01
    uv run python tests/evals/script_eval.py --entry rival-chef-s01 --script-file /path/to/script.txt
    uv run python tests/evals/script_eval.py --entry rival-chef-s01 --dry-run
    uv run python tests/evals/script_eval.py --all
    uv run python tests/evals/script_eval.py --all --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = ROOT / "tests" / "evals" / "fixtures" / "friends_golden.json"


def cmd_validate_only() -> int:
    from holodeck.evaluation.loader import GoldenDatasetValidationError, load_golden_dataset

    try:
        entries = load_golden_dataset(FIXTURES)
    except GoldenDatasetValidationError as e:
        print(f"❌ Validation failed: {e}", file=sys.stderr)
        return 1

    print(f"✅ {len(entries)} entries validated")
    for entry in entries:
        print(f"  - {entry.prompt_id}")
    return 0


def cmd_single(prompt_id: str, dry_run: bool = False, script_file: str | None = None) -> int:
    from holodeck.evaluation.loader import GoldenDatasetValidationError, load_golden_dataset
    from holodeck.evaluation.runner import EvaluationRunner

    try:
        entries = load_golden_dataset(FIXTURES)
    except GoldenDatasetValidationError as e:
        print(f"❌ Dataset validation failed: {e}", file=sys.stderr)
        return 1

    matching = [e for e in entries if e.prompt_id == prompt_id]
    if not matching:
        print(f"❌ No entry found with prompt_id '{prompt_id}'", file=sys.stderr)
        print(f"Available: {[e.prompt_id for e in entries]}", file=sys.stderr)
        return 1

    entry = matching[0]
    runner = EvaluationRunner()

    if dry_run:
        print(f"Evaluating '{prompt_id}' (dry-run — stub scores, no LLM calls)...")
        result = runner.evaluate_single(entry, dry_run=True)
    elif script_file:
        script_path = Path(script_file)
        if not script_path.exists():
            print(f"❌ Script file not found: {script_file}", file=sys.stderr)
            return 1
        script_content = script_path.read_text(encoding="utf-8")
        print(f"Evaluating '{prompt_id}' with provided script ({len(script_content)} chars)...")
        result = runner.evaluate_single(entry, script_content=script_content)
    else:
        print(f"Evaluating '{prompt_id}' — generating script via pipeline then scoring...")
        print(f"  Prompt: {entry.user_prompt[:80]}...")
        result = runner.run_full(entry)

    output = {
        "result_id": str(result.result_id),
        "golden_entry_id": result.golden_entry_id,
        "script_id": result.script_id,
        "overall_score": result.overall_score(),
        "passed_quality_gate": result.passed_quality_gate,
        "regression_detected": result.regression_detected,
        "dimension_scores": [
            {
                "dimension": ds.dimension,
                "score": ds.score,
                "weighted": round(ds.weighted_score, 4),
                "reasoning": ds.reasoning,
            }
            for ds in result.dimension_scores
        ],
    }
    print(json.dumps(output, indent=2))
    return 0


def cmd_all(dry_run: bool = False) -> int:
    from holodeck.evaluation.loader import GoldenDatasetValidationError, load_golden_dataset
    from holodeck.evaluation.reporter import BatchReporter
    from holodeck.evaluation.runner import EvaluationRunner

    try:
        entries = load_golden_dataset(FIXTURES)
    except GoldenDatasetValidationError as e:
        print(f"❌ Dataset validation failed: {e}", file=sys.stderr)
        return 1

    runner = EvaluationRunner()

    if dry_run:
        print(f"Running batch evaluation on {len(entries)} entries (dry-run)...")
        report = runner.run_batch(entries, dry_run=True)
    else:
        print(f"Running batch evaluation on {len(entries)} entries (live — pipeline + LLM scoring)...")
        report = runner.run_full_batch(entries)

    reporter = BatchReporter()
    report.summary_statistics = reporter.aggregate(report.evaluation_results, report.failures)

    stats = report.summary_statistics
    print(f"\n{'='*50}")
    print("BATCH EVALUATION COMPLETE")
    print(f"{'='*50}")
    print(f"Total entries : {stats.total_entries}")
    print(f"Evaluated     : {stats.evaluated}")
    print(f"Failed        : {stats.failed}")
    print(f"Passed gate   : {stats.pass_count}")
    print(f"Failed gate   : {stats.fail_count}")
    print(f"Avg score     : {stats.average_overall_score:.3f}")
    print(f"Regressions   : {stats.regressions_detected}")

    if report.failures:
        print("\nFailures:")
        for failure in report.failures:
            print(f"  ❌ {failure.golden_entry_id}: {failure.error_message}")

    exit_code = 1 if report.failures and not report.evaluation_results else 0
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Sitcom golden dataset evaluation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate-only", action="store_true", help="Validate dataset structure only")
    group.add_argument("--entry", metavar="PROMPT_ID", help="Evaluate a single golden dataset entry")
    group.add_argument("--all", action="store_true", dest="all_entries", help="Evaluate all entries")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Skip LLM calls; return zero-score stubs (default: live evaluation)",
    )
    parser.add_argument(
        "--script-file",
        metavar="PATH",
        help="Evaluate a pre-written script file instead of generating one (use with --entry)",
    )
    args = parser.parse_args()

    if args.validate_only:
        sys.exit(cmd_validate_only())
    elif args.entry:
        sys.exit(cmd_single(args.entry, dry_run=args.dry_run, script_file=args.script_file))
    elif args.all_entries:
        sys.exit(cmd_all(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
