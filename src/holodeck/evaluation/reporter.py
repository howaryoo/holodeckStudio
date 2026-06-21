from __future__ import annotations

from collections import Counter
from pathlib import Path  # noqa: TC003

from holodeck.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationFailure,
    EvaluationResult,
    SummaryStatistics,
)


class BatchReporter:
    def aggregate(
        self,
        results: list[EvaluationResult],
        failures: list[EvaluationFailure],
    ) -> SummaryStatistics:
        total = len(results) + len(failures)
        evaluated = len(results)
        failed = len(failures)
        pass_count = sum(1 for r in results if r.passed_quality_gate)
        fail_count = evaluated - pass_count
        regressions = sum(1 for r in results if r.regression_detected)

        avg_overall = (
            sum(r.overall_score() for r in results) / evaluated if evaluated else 0.0
        )

        dim_scores: dict[str, list[float]] = {}
        all_red_flags: list[str] = []

        for result in results:
            for ds in result.dimension_scores:
                dim_scores.setdefault(ds.dimension, []).append(ds.score)
            all_red_flags.extend(result.red_flags_triggered)

        avg_by_dim = {
            dim: sum(scores) / len(scores)
            for dim, scores in dim_scores.items()
        }

        flag_counts = Counter(all_red_flags)
        threshold = evaluated * 0.5
        common_flags = [flag for flag, count in flag_counts.items() if count >= threshold]

        return SummaryStatistics(
            total_entries=total,
            evaluated=evaluated,
            failed=failed,
            pass_count=pass_count,
            fail_count=fail_count,
            average_overall_score=avg_overall,
            average_score_by_dimension=avg_by_dim,
            regressions_detected=regressions,
            common_red_flags=common_flags,
        )

    def detect_regressions(self, report: BatchEvaluationReport) -> list[dict]:
        regressions = []
        for result in report.evaluation_results:
            if result.regression_detected and result.previous_score is not None:
                current = result.overall_score()
                delta = (result.previous_score - current) / result.previous_score * 100
                regressions.append(
                    {
                        "golden_entry_id": result.golden_entry_id,
                        "previous_score": round(result.previous_score, 4),
                        "current_score": round(current, 4),
                        "delta_pct": round(delta, 2),
                    }
                )
        return regressions

    def export_report(
        self,
        report: BatchEvaluationReport,
        output_dir: Path,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        formats = formats or ["json", "md"]
        written: dict[str, Path] = {}

        if "json" in formats:
            path = output_dir / "report.json"
            path.write_text(
                report.model_dump_json(indent=2), encoding="utf-8"
            )
            written["json"] = path

        if "md" in formats:
            path = output_dir / "report.md"
            path.write_text(self._render_markdown(report), encoding="utf-8")
            written["md"] = path

        return written

    def _render_markdown(self, report: BatchEvaluationReport) -> str:
        stats = report.summary_statistics
        regressions = self.detect_regressions(report)
        lines: list[str] = [
            "# Evaluation Report",
            "",
            f"**Generated**: {report.generated_timestamp.isoformat()}  ",
            f"**Dataset version**: {report.golden_dataset_version}  ",
            f"**Report ID**: {report.report_id}",
            "",
            "## Summary",
            "",
        ]

        if stats:
            lines += [
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total entries | {stats.total_entries} |",
                f"| Evaluated | {stats.evaluated} |",
                f"| Failed | {stats.failed} |",
                f"| Passed quality gate | {stats.pass_count} |",
                f"| Failed quality gate | {stats.fail_count} |",
                f"| Average overall score | {stats.average_overall_score:.3f} |",
                f"| Regressions detected | {stats.regressions_detected} |",
                "",
                "## Dimension Averages",
                "",
                "| Dimension | Average Score |",
                "|-----------|--------------|",
            ]
            for dim, avg in stats.average_score_by_dimension.items():
                lines.append(f"| {dim} | {avg:.3f} |")

            if stats.common_red_flags:
                lines += [
                    "",
                    "## Common Red Flags (>50% of evaluations)",
                    "",
                ]
                lines += [f"- {flag}" for flag in stats.common_red_flags]

        if regressions:
            lines += [
                "",
                "## Regressions Detected",
                "",
                "| Entry | Previous | Current | Delta % |",
                "|-------|----------|---------|---------|",
            ]
            for r in regressions:
                lines.append(
                    f"| {r['golden_entry_id']} | {r['previous_score']:.3f} "
                    f"| {r['current_score']:.3f} | -{r['delta_pct']:.1f}% |"
                )

        if report.failures:
            lines += ["", "## Evaluation Failures", "", "| Entry | Error | Type |", "|-------|-------|------|"]
            for f in report.failures:
                lines.append(f"| {f.golden_entry_id} | {f.error_message[:60]} | {f.error_type} |")

        lines += ["", "## Individual Results", ""]
        for result in report.evaluation_results:
            overall = result.overall_score()
            gate = "✅ PASS" if result.passed_quality_gate else "❌ FAIL"
            reg = " ⚠️ REGRESSION" if result.regression_detected else ""
            lines.append(f"### {result.golden_entry_id} — {overall:.3f} {gate}{reg}")
            lines.append("")
            lines.append("| Dimension | Score |")
            lines.append("|-----------|-------|")
            for ds in result.dimension_scores:
                lines.append(f"| {ds.dimension} | {ds.score:.3f} |")
            if result.guideline_comparison.missed:
                lines.append("")
                lines.append(f"**Missed guidelines**: {', '.join(result.guideline_comparison.missed)}")
            lines.append("")

        return "\n".join(lines)
