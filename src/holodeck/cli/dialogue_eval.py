from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="dialogue-eval", help="Evaluate dialogue quality using LLM-as-judge scoring.")  # noqa: E501
console = Console()


def _print_line_scores(line_scores: list, scene_score: Any) -> None:  # type: ignore[type-arg]  # noqa: ANN401
    console.print("\n[bold]=== DIALOGUE EVALUATION ===[/bold]\n")
    console.print("[bold]Per-phrase scores:[/bold]")
    for ls in line_scores:
        composite = ls.composite_score
        color = "green" if composite >= 7 else "yellow" if composite >= 5 else "red"
        text_preview = ls.text[:50] + ("…" if len(ls.text) > 50 else "")
        console.print(f"\n  [[bold]{ls.character}[/bold]] {text_preview}")
        console.print(
            f"    Character authenticity : {ls.character_authenticity.score}/10  "
            f"{ls.character_authenticity.reasoning}"
        )
        console.print(
            f"    Dialogue naturalness   : {ls.dialogue_naturalness.score}/10  "
            f"{ls.dialogue_naturalness.reasoning}"
        )
        console.print(
            f"    Comedy contribution    : {ls.comedy_contribution.score}/10  "
            f"{ls.comedy_contribution.reasoning}"
        )
        console.print(f"    [{color}]Composite              : {composite:.1f}/10[/{color}]")
        if composite < 6:
            dims = {
                "character_authenticity": ls.character_authenticity.score,
                "dialogue_naturalness": ls.dialogue_naturalness.score,
                "comedy_contribution": ls.comedy_contribution.score,
            }
            worst = min(dims, key=dims.get)  # type: ignore[arg-type]
            console.print(f"    [yellow]⚠ Weakest dimension: {worst}[/yellow]")

    overall = scene_score.overall_score
    scene_color = "green" if overall >= 7 else "yellow" if overall >= 5 else "red"
    console.print("\n[bold]=== SCENE SCORE ===[/bold]")
    console.print(f"  [{scene_color}]Overall: {overall:.1f}/10[/{scene_color}]")
    cp = scene_score.comedy_pacing
    console.print(f"  Comedy pacing       : {cp.score}/10  {cp.reasoning}")
    ed = scene_score.ensemble_dynamics
    na = scene_score.narrative_arc
    tc = scene_score.thematic_coherence
    console.print(f"  Ensemble dynamics   : {ed.score}/10  {ed.reasoning}")
    console.print(f"  Narrative arc       : {na.score}/10  {na.reasoning}")
    console.print(f"  Thematic coherence  : {tc.score}/10  {tc.reasoning}")
    console.print(f"\n  [italic]{scene_score.summary}[/italic]")


@app.command("run")
def run_command(path: str = typer.Argument(..., help="Path to dialogue JSON file")) -> None:
    """Evaluate a single dialogue file (raw metadata list or golden fixture)."""
    from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

    file_path = Path(path)
    if not file_path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    raw = json.loads(file_path.read_text())
    dialogue: list[dict[str, str]]
    if isinstance(raw, list):
        dialogue = raw
    elif isinstance(raw, dict) and "dialogue" in raw:
        dialogue = raw["dialogue"]
    else:
        console.print(
            "[red]Unrecognised format: expected a list or a dict with a 'dialogue' key[/red]"
        )
        raise typer.Exit(1)

    runner = DialogueEvaluationRunner()
    with console.status("Evaluating dialogue…"):
        line_scores, scene_score = runner.evaluate(dialogue)

    _print_line_scores(line_scores, scene_score)

    if scene_score.overall_score < 5.0:
        console.print(
            "\n[bold red]Scene score below quality bar (5.0). Review required.[/bold red]"
        )
        raise typer.Exit(1)


@app.command("batch")
def batch_command(
    fixtures_dir: str = typer.Option(
        "tests/fixtures/dialogue", help="Directory containing fixture JSON files"
    ),
) -> None:
    """Batch-evaluate all golden fixture files and print a summary table."""
    from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

    fixture_paths = sorted(Path(fixtures_dir).glob("*.json"))
    if not fixture_paths:
        console.print(f"[yellow]No JSON fixtures found in {fixtures_dir}[/yellow]")
        raise typer.Exit(0)

    runner = DialogueEvaluationRunner()
    table = Table(title="Dialogue Batch Evaluation", show_lines=True)
    table.add_column("Fixture", style="cyan")
    table.add_column("Overall", justify="center")
    table.add_column("Comedy Pacing", justify="center")
    table.add_column("Ensemble", justify="center")
    table.add_column("Narrative Arc", justify="center")
    table.add_column("Thematic", justify="center")

    for fp in fixture_paths:
        with console.status(f"Evaluating {fp.name}…"):
            _, scene_score = runner.evaluate_fixture(str(fp))

        def fmt(s: float) -> str:
            color = "green" if s >= 7 else "yellow" if s >= 5 else "red"
            return f"[{color}]{s:.1f}[/{color}]"

        table.add_row(
            fp.stem,
            fmt(scene_score.overall_score),
            fmt(float(scene_score.comedy_pacing.score)),
            fmt(float(scene_score.ensemble_dynamics.score)),
            fmt(float(scene_score.narrative_arc.score)),
            fmt(float(scene_score.thematic_coherence.score)),
        )

    console.print(table)
