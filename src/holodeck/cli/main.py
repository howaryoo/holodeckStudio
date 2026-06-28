from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from holodeck.pipeline.runner import PipelineResult

app = typer.Typer(name="holodeck", help="Holodeck Studio — Agentic AI production pipeline")
console = Console()

MIN_PROMPT_LENGTH = 20

VAGUE_PATTERNS: list[tuple[str, str]] = [
    ("genre", "Please specify a genre (e.g., science-fiction, fantasy, drama)"),
    ("theme", "Please specify themes or story elements"),
    ("character", "Please mention at least one character or character type"),
    ("story", "Please provide a story direction or plot premise"),
]


def _validate_prompt(prompt: str) -> tuple[bool, str]:
    if len(prompt.strip()) < MIN_PROMPT_LENGTH:
        return False, f"Prompt is too short (minimum {MIN_PROMPT_LENGTH} characters). Please provide more detail."
    guidance: list[str] = []
    lowered = prompt.lower()
    for keyword, message in VAGUE_PATTERNS:
        if keyword not in lowered and len(guidance) < 2:
            guidance.append(message)
    if len(guidance) >= 3:
        return False, "Prompt is too vague. " + " ".join(guidance)
    return True, ""


def _display_media(result: PipelineResult, console: Console) -> None:
    if result.dialogue_audio_metadata:
        console.print("\n[bold]=== DIALOGUE AUDIO ===[/bold]")
        for entry in result.dialogue_audio_metadata:
            console.print(f"  [{entry['character']}] {entry['text']}")
            console.print(f"    → {entry['file']}")
    elif result.dialogue_audio_urls:
        console.print("\n[bold]=== DIALOGUE AUDIO ===[/bold]")
        for url in result.dialogue_audio_urls:
            console.print(f"  {url}")
    if result.video_url:
        console.print("\n[bold]=== VIDEO ===[/bold]")
        console.print(f"  {result.video_url}")
    if result.frame_paths:
        console.print("\n[bold]=== FRAMES ===[/bold]")
        console.print(f"  {len(result.frame_paths)} frames generated")


@app.command()
def produce(
    prompt: str = typer.Argument(help="Theme or story prompt (min 20 characters)"),
    mode: str = typer.Option("autonomous", help="Production mode: autonomous|supervised"),
    bible: str | None = typer.Option(None, help="Franchise bible name or ID"),
    config: str | None = typer.Option(None, help="Path to custom configuration file"),
    output: str = typer.Option("./output", help="Output directory for production assets"),
    no_approve: bool = typer.Option(False, "--no-approve", help="Skip all approval checkpoints"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the result cache and force LLM calls"),
    budget: float | None = typer.Option(None, "--budget", help="Maximum budget in USD for this production"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate prompt without executing"),
    open_video: bool = typer.Option(False, "--open", help="Open the final video after generation"),
) -> None:
    valid, error = _validate_prompt(prompt)
    if not valid:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)
    if dry_run:
        console.print(f"[green]Prompt validated:[/green] {prompt[:80]}...")
        console.print(f"  Mode: {mode}")
        console.print(f"  Bible: {bible or 'None'}")
        raise typer.Exit(code=0)
    if not no_cache:
        from holodeck.cache import PipelineCache
        cached = PipelineCache().get(prompt, bible, mode)
        if cached is not None:
            import os as _os
            console.print("[yellow]Returning cached result. Use --no-cache to force fresh LLM calls.[/yellow]")
            console.print("\n[green]Production (cached) complete![/green]")
            console.print(f"  Production ID: {cached.get('production_id', '?')}")
            console.print(f"  Output folder: {_os.path.abspath(output)}")
            console.print("\n[bold]=== SCRIPT ===[/bold]")
            console.print(cached.get("script", "")[:2000])
            if len(cached.get("script", "")) > 2000:
                console.print(f"[dim]... ({len(cached['script']) - 2000} more characters)[/dim]")
            console.print("\n[bold]=== CANON HISTORIAN REPORT ===[/bold]")
            console.print(cached.get("canon_report", "")[:500])
            console.print("\n[bold]=== CRITIC REVIEW ===[/bold]")
            console.print(cached.get("critique", "")[:500])
            if cached.get("musical_score"):
                console.print("\n[bold]=== MUSICAL SCORE ===[/bold]")
                console.print(cached["musical_score"][:500])
            if cached.get("sound_design"):
                console.print("\n[bold]=== SOUND DESIGN ===[/bold]")
                console.print(cached["sound_design"][:500])
            if cached.get("voice_direction"):
                console.print("\n[bold]=== VOICE DIRECTION ===[/bold]")
                console.print(cached["voice_direction"][:500])
            if cached.get("qa_report"):
                console.print("\n[bold]=== QA REPORT ===[/bold]")
                console.print(cached["qa_report"][:500])
            if cached.get("audience_report"):
                console.print("\n[bold]=== AUDIENCE SIMULATION ===[/bold]")
                console.print(cached["audience_report"][:500])
            if cached.get("dialogue_audio_metadata"):
                console.print("\n[bold]=== DIALOGUE AUDIO ===[/bold]")
                for entry in cached["dialogue_audio_metadata"]:
                    console.print(f"  [{entry['character']}] {entry['text']}")
                    console.print(f"    → {entry['file']}")
            elif cached.get("dialogue_audio_urls"):
                console.print("\n[bold]=== DIALOGUE AUDIO ===[/bold]")
                for url in cached["dialogue_audio_urls"]:
                    console.print(f"  {url}")
            if cached.get("video_url"):
                console.print("\n[bold]=== VIDEO ===[/bold]")
                console.print(f"  {cached['video_url']}")
                if open_video:
                    typer.launch(cached["video_url"])
            return
    console.print(f"[blue]Starting production:[/blue] {prompt[:80]}...")
    console.print(f"  Mode: {mode}")
    console.print(f"  Output: {output}")

    from holodeck.config.settings import Settings
    from holodeck.observability.tracing import setup_tracing
    setup_tracing(Settings())

    import asyncio

    from holodeck.pipeline.runner import ProductionPipeline

    pipeline = ProductionPipeline()
    try:
        result = asyncio.run(pipeline.run(
            prompt=prompt,
            mode=mode,
            bible=bible,
            output=output,
            use_cache=not no_cache,
            budget=budget,
        ))
        import os as _os
        console.print(f"\n[green]Production {result.production_id} complete![/green]")
        console.print(f"  Output folder: {_os.path.abspath(output)}")
        console.print("\n[bold]=== SCRIPT ===[/bold]")
        console.print(result.script[:2000])
        if len(result.script) > 2000:
            console.print(f"[dim]... ({len(result.script) - 2000} more characters)[/dim]")
        console.print("\n[bold]=== CANON HISTORIAN REPORT ===[/bold]")
        console.print(result.canon_report[:500])
        console.print("\n[bold]=== CRITIC REVIEW ===[/bold]")
        console.print(result.critique[:500])
        if result.budget_report:
            console.print("\n[bold]=== PRODUCER BUDGET REPORT ===[/bold]")
            console.print(result.budget_report[:500])
        if result.visual_style:
            console.print("\n[bold]=== VISUAL STYLE GUIDE ===[/bold]")
            console.print(result.visual_style[:500])
        if result.storyboard:
            console.print("\n[bold]=== STORYBOARD ===[/bold]")
            console.print(result.storyboard[:500])
        if result.character_designs:
            console.print("\n[bold]=== CHARACTER DESIGNS ===[/bold]")
            console.print(result.character_designs[:500])
        if result.environment_designs:
            console.print("\n[bold]=== ENVIRONMENT DESIGNS ===[/bold]")
            console.print(result.environment_designs[:500])
        if result.musical_score:
            console.print("\n[bold]=== MUSICAL SCORE ===[/bold]")
            console.print(result.musical_score[:500])
        if result.sound_design:
            console.print("\n[bold]=== SOUND DESIGN ===[/bold]")
            console.print(result.sound_design[:500])
        if result.voice_direction:
            console.print("\n[bold]=== VOICE DIRECTION ===[/bold]")
            console.print(result.voice_direction[:500])
        if result.asset_descriptions:
            console.print("\n[bold]=== ASSET DESCRIPTIONS ===[/bold]")
            console.print(result.asset_descriptions[:500])
        if result.animation:
            console.print("\n[bold]=== ANIMATION ===[/bold]")
            console.print(result.animation[:500])
        if result.render_plan:
            console.print("\n[bold]=== RENDER PLAN ===[/bold]")
            console.print(result.render_plan[:500])
        if result.qa_report:
            console.print("\n[bold]=== QA REPORT ===[/bold]")
            console.print(result.qa_report[:500])
        if result.audience_report:
            console.print("\n[bold]=== AUDIENCE SIMULATION ===[/bold]")
            console.print(result.audience_report[:500])
        _display_media(result, console)
        if open_video and result.video_url:
            typer.launch(result.video_url)
    except Exception as e:
        console.print(f"[red]Production failed:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def status(
    production_id: str = typer.Argument(help="Production UUID"),
    episode: int | None = typer.Option(None, help="Show specific episode number"),
    stage: str | None = typer.Option(None, help="Show details for a specific stage"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Include agent execution details and costs"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from holodeck.memory.production import get_production
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    data = prod.to_dict()
    if json_output:
        import json as _json
        console.print(_json.dumps(data, indent=2, default=str))
        return
    table = Table(title=f"Production {production_id[:8]}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Status", data["status"])
    table.add_row("Mode", data["mode"])
    table.add_row("Theme Prompt", data["theme_prompt"][:80])
    table.add_row("Episodes", str(len(data["episodes"])))
    table.add_row("Agent Executions", str(len(data["agent_executions"])))
    table.add_row("Total Cost (USD)", f"${data['total_cost_usd']:.4f}")
    console.print(table)
    if verbose and data["agent_executions"]:
        exec_table = Table(title="Agent Executions")
        exec_table.add_column("Agent", style="magenta")
        exec_table.add_column("Stage", style="cyan")
        exec_table.add_column("Approved", style="green")
        exec_table.add_column("Score", style="yellow")
        for ex in data["agent_executions"]:
            exec_table.add_row(ex.get("agent_role", "?"), ex.get("stage", "?"), str(ex.get("approved", "?")), str(ex.get("score", "?")))
        console.print(exec_table)


@app.command()
def approve(
    production_id: str = typer.Argument(help="Production UUID"),
    stage: str | None = typer.Option(None, help="Stage to approve"),
    episode: int = typer.Option(1, help="Episode number"),
    note: str | None = typer.Option(None, help="Optional approval note"),
) -> None:
    from holodeck.memory.production import get_production
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    prod.add_approval({
        "type": "approved",
        "stage": stage or "unknown",
        "episode": episode,
        "note": note or "",
        "reviewer": "human",
    })
    if stage:
        for ex in prod._agent_executions:
            if ex.get("stage") == stage:
                ex["approved"] = True
    console.print(f"[green]Approved:[/green] Production {production_id}, Stage: {stage}, Episode: {episode}")
    if note:
        console.print(f"  Note: {note}")


@app.command()
def reject(
    production_id: str = typer.Argument(help="Production UUID"),
    stage: str = typer.Option(..., help="Stage to reject"),
    episode: int = typer.Option(1, help="Episode number"),
    feedback: str = typer.Option(..., help="Revision feedback for agents"),
) -> None:
    from holodeck.memory.production import get_production
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    prod.add_approval({
        "type": "rejected",
        "stage": stage,
        "episode": episode,
        "note": feedback,
        "reviewer": "human",
    })
    for ex in prod._agent_executions:
        if ex.get("stage") == stage:
            ex["approved"] = False
    console.print(f"[red]Rejected:[/red] Production {production_id}, Stage: {stage}")
    console.print(f"  Feedback: {feedback}")


@app.command()
def pause(
    production_id: str = typer.Argument(help="Production UUID"),
) -> None:
    from holodeck.memory.production import get_production
    from holodeck.pipeline.stages import ProductionStatus
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    prod.status = ProductionStatus.PAUSED
    console.print(f"[yellow]Paused:[/yellow] Production {production_id}")


@app.command()
def resume(
    production_id: str = typer.Argument(help="Production UUID"),
) -> None:
    from holodeck.memory.production import get_production
    from holodeck.pipeline.stages import ProductionStatus
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    prod.status = ProductionStatus.RUNNING
    console.print(f"[green]Resumed:[/green] Production {production_id}")


@app.command()
def review(
    production_id: str = typer.Argument(help="Production UUID"),
    episode: int | None = typer.Option(None, help="Review specific episode number"),
    type: str | None = typer.Option(None, help="Filter by: canon_historian|critic|audience_simulation|qa"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Include full review content"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from holodeck.memory.production import get_production
    prod = get_production(production_id)
    if not prod:
        console.print(f"[red]Error:[/red] Production not found: {production_id}")
        raise typer.Exit(code=1)
    all_reviews: list[dict] = []
    ep_memories = prod.get_all_episode_memories()
    if not ep_memories:
        console.print("[yellow]No episode data found for this production.[/yellow]")
        raise typer.Exit(code=0)
    for ep_mem in ep_memories:
        reviews = ep_mem.get_reviews()
        all_reviews.extend(reviews)
    if type:
        all_reviews = [r for r in all_reviews if r.get("reviewer") == type]
    if not all_reviews:
        console.print("[yellow]No reviews found matching criteria.[/yellow]")
        raise typer.Exit(code=0)
    if json_output:
        import json as _json
        console.print(_json.dumps(all_reviews, indent=2, default=str))
        return
    table = Table(title=f"Reviews — {production_id[:8]}")
    table.add_column("Reviewer", style="magenta")
    table.add_column("Score", style="yellow")
    table.add_column("Approved", style="green")
    table.add_column("Content Preview", style="white")
    for rv in all_reviews:
        content = rv.get("critique") or rv.get("report") or rv.get("content") or ""
        table.add_row(
            rv.get("reviewer", "?"),
            str(rv.get("score", "?")),
            str(rv.get("approved", "?")),
            content[:80],
        )
    console.print(table)
    if verbose:
        for rv in all_reviews:
            content = rv.get("critique") or rv.get("report") or rv.get("content") or ""
            console.print(f"\n[bold]{rv.get('reviewer', '?')}[/bold] (score: {rv.get('score', '?')}, approved: {rv.get('approved', '?')})")
            console.print(content[:2000])
            if len(content) > 2000:
                console.print(f"[dim]... ({len(content) - 2000} more characters)[/dim]")


bible_app = typer.Typer(help="Manage franchise bibles")
app.add_typer(bible_app, name="bible")


@bible_app.command("list")
def bible_list() -> None:
    from holodeck.memory.franchise_bible import list_bibles
    bibles = list_bibles()
    if not bibles:
        console.print("[yellow]No bibles found. Create one with: holodeck bible create <name>[/yellow]")
        return
    table = Table(title="Franchise Bibles")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    table.add_column("Entries", style="yellow")
    for b in bibles:
        table.add_row(b["id"][:8], b["name"], b["description"], str(b["entry_count"]))
    console.print(table)


@bible_app.command("show")
def bible_show(bible_id: str = typer.Argument(help="Bible ID")) -> None:
    from holodeck.memory.franchise_bible import get_bible
    bible = get_bible(bible_id)
    if not bible:
        console.print(f"[red]Error:[/red] Bible not found: {bible_id}")
        raise typer.Exit(code=1)
    console.print(f"[bold]Bible:[/bold] {bible.name}")
    console.print(f"  [bold]ID:[/bold] {bible.id}")
    console.print(f"  [bold]Entries:[/bold] {len(bible.get_entries())}")
    entries = bible.get_entries()
    if entries:
        entry_table = Table(title="Entries")
        entry_table.add_column("ID", style="cyan")
        entry_table.add_column("Category", style="magenta")
        entry_table.add_column("Name", style="green")
        entry_table.add_column("Content Preview", style="white")
        for e in entries:
            entry_table.add_row(str(e["id"])[:8], e["category"], e["name"], e["content"][:60])
        console.print(entry_table)


@bible_app.command("create")
def bible_create(
    name: str = typer.Argument(help="Bible name"),
    description: str | None = typer.Argument(None, help="Bible description"),
) -> None:
    from holodeck.memory.franchise_bible import create_bible
    import asyncio
    try:
        from holodeck.memory.franchise_bible import async_create_bible
        bible = asyncio.run(async_create_bible(name, description or ""))
    except Exception:
        bible = create_bible(name, description or "")
    console.print(f"[green]Created bible:[/green] {name}")
    console.print(f"  ID: {bible.id}")


@bible_app.command("add-entry")
def bible_add_entry(
    bible_id: str = typer.Argument(help="Bible ID"),
    category: str = typer.Option(..., help="Category: character|location|technology|lore|event"),
    name: str = typer.Option(..., help="Entry name"),
    content: str = typer.Option(..., help="Entry content"),
) -> None:
    import asyncio
    from holodeck.memory.franchise_bible import get_bible
    bible = get_bible(bible_id)
    if not bible:
        console.print(f"[red]Error:[/red] Bible not found: {bible_id}")
        raise typer.Exit(code=1)
    entry_id = asyncio.run(bible.add_entry(category, name, content))
    console.print(f"[green]Added entry:[/green] {name} ({category}) to bible {bible_id}")
    console.print(f"  Entry ID: {entry_id}")


@bible_app.command("clear-entries")
def bible_clear_entries(
    bible_id: str = typer.Argument(help="Bible ID"),
) -> None:
    import asyncio
    from holodeck.memory.franchise_bible import get_bible
    bible = get_bible(bible_id)
    if not bible:
        console.print(f"[red]Error:[/red] Bible not found: {bible_id}")
        raise typer.Exit(code=1)
    count = len(bible._entries)
    asyncio.run(bible.clear_entries())
    console.print(f"[green]Cleared {count} entries from bible {bible_id}[/green]")


@bible_app.command("search")
def bible_search(
    bible_id: str = typer.Argument(help="Bible ID"),
    query: str = typer.Argument(help="Search query"),
) -> None:
    import asyncio
    from holodeck.memory.franchise_bible import get_bible
    bible = get_bible(bible_id)
    if not bible:
        console.print(f"[red]Error:[/red] Bible not found: {bible_id}")
        raise typer.Exit(code=1)
    results = asyncio.run(bible.search(query))
    if not results:
        console.print(f"[yellow]No results for:[/yellow] {query}")
        return
    table = Table(title=f"Search results for '{query}'")
    table.add_column("Category", style="magenta")
    table.add_column("Name", style="green")
    table.add_column("Content Preview", style="white")
    for e in results:
        table.add_row(e["category"], e["name"], e["content"][:80])
    console.print(table)


voice_sample_app = typer.Typer(help="Manage actor voice samples for voice cloning")
bible_app.add_typer(voice_sample_app, name="voice-sample")


@voice_sample_app.command("add")
def voice_sample_add(
    bible: str = typer.Option(..., "--bible", help="Bible ID"),
    character: str = typer.Option(..., "--character", help="Character display name (e.g. 'Rachel Green')"),
    file: str = typer.Option(..., "--file", help="Path to audio file (MP3, WAV, OGG, FLAC)"),
    description: str | None = typer.Option(None, "--description", help="Optional notes about this sample"),
) -> None:
    import asyncio
    from pathlib import Path
    from uuid import UUID, uuid4
    from holodeck.storage.voice_sample_store import validate_audio_file, upload_voice_sample
    from holodeck.storage.postgres import ActorVoiceSample, ActorVoiceSampleRepository
    from holodeck.config.settings import Settings

    if not Path(file).exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(code=1)

    try:
        duration, fmt = validate_audio_file(file)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"Validated: {fmt.upper()}, {duration:.1f}s")

    try:
        bible_id = UUID(bible)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid bible ID: {bible}")
        raise typer.Exit(code=1)

    async def _run() -> None:
        settings = Settings()
        repo = ActorVoiceSampleRepository()
        await repo.deactivate(bible_id, character)
        object_key = await upload_voice_sample(file, bible_id, character, settings)
        sample = ActorVoiceSample(
            id=uuid4(),
            bible_id=bible_id,
            character_name=character,
            sample_file_path=object_key,
            source_format=fmt,
            duration_seconds=duration,
            description=description,
            is_active=True,
        )
        await repo.create(sample)
        console.print(f"[green]Added voice sample:[/green] {character}")
        console.print(f"  Sample ID: {sample.id}")
        console.print(f"  Duration:  {duration:.1f}s ({fmt.upper()})")
        console.print(f"  MinIO key: {object_key}")

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@voice_sample_app.command("list")
def voice_sample_list(
    bible: str = typer.Option(..., "--bible", help="Bible ID"),
) -> None:
    import asyncio
    from uuid import UUID
    from holodeck.storage.postgres import ActorVoiceSampleRepository

    try:
        bible_id = UUID(bible)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid bible ID: {bible}")
        raise typer.Exit(code=1)

    async def _run() -> None:
        repo = ActorVoiceSampleRepository()
        samples = await repo.list_by_bible(bible_id)
        if not samples:
            console.print("[yellow]No voice samples found for this bible.[/yellow]")
            return
        table = Table(title=f"Voice samples — bible {bible}")
        table.add_column("Character", style="cyan")
        table.add_column("Format", style="magenta")
        table.add_column("Duration", style="white")
        table.add_column("Active", style="white")
        table.add_column("Voice ID", style="dim")
        table.add_column("Uploaded", style="dim")
        for s in samples:
            table.add_row(
                s.character_name,
                s.source_format.upper(),
                f"{s.duration_seconds:.0f}s",
                "[green]✓[/green]" if s.is_active else "[dim]—[/dim]",
                s.elevenlabs_voice_id or "—",
                s.upload_date.strftime("%Y-%m-%d") if s.upload_date else "—",
            )
        console.print(table)

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@voice_sample_app.command("disable")
def voice_sample_disable(
    bible: str = typer.Option(..., "--bible", help="Bible ID"),
    character: str = typer.Option(..., "--character", help="Character display name"),
) -> None:
    import asyncio
    from uuid import UUID
    from holodeck.storage.postgres import ActorVoiceSampleRepository

    try:
        bible_id = UUID(bible)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid bible ID: {bible}")
        raise typer.Exit(code=1)

    async def _run() -> None:
        repo = ActorVoiceSampleRepository()
        await repo.deactivate(bible_id, character)
        console.print(f"[green]Disabled voice sample for:[/green] {character}")
        console.print("  Production will fall back to Piper TTS for this character.")

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    from holodeck.config.settings import Settings
    from holodeck.config.persistence import get_all_overrides
    settings = Settings()
    overrides = get_all_overrides()
    table = Table(title="Holodeck Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    for field_name, value in settings.model_dump().items():
        marker = " [yellow]*[/yellow]" if field_name in overrides else ""
        table.add_row(field_name + marker, str(value))
    if overrides:
        console.print(f"[dim]Overrides active: {len(overrides)} entries from ~/.holodeck/config.json[/dim]")
    console.print(table)


@config_app.command("set")
def config_set(key: str = typer.Argument(help="Configuration key"), value: str = typer.Argument(help="Configuration value")) -> None:
    from holodeck.config.persistence import save_override
    overrides = save_override(key, value)
    console.print(f"[green]Set:[/green] {key} = {value}")
    console.print(f"  Overrides saved to ~/.holodeck/config.json ({len(overrides)} entries)")


@config_app.command("reset")
def config_reset() -> None:
    from holodeck.config.persistence import clear_overrides
    clear_overrides()
    console.print("[green]Configuration reset to defaults.[/green]")
    console.print("  ~/.holodeck/config.json cleared")


cache_app = typer.Typer(help="Manage the production result cache")
app.add_typer(cache_app, name="cache")

from holodeck.cli.dialogue_eval import app as dialogue_eval_app  # noqa: E402
app.add_typer(dialogue_eval_app, name="dialogue-eval")


@cache_app.command("clear")
def cache_clear() -> None:
    from holodeck.cache import PipelineCache, clear_agent_cache
    PipelineCache().clear()
    clear_agent_cache()
    console.print("[green]Cache cleared (pipeline + agent).[/green]")


@cache_app.command("status")
def cache_status() -> None:
    from holodeck.cache import PipelineCache
    cache = PipelineCache()
    backend = cache.backend
    if hasattr(backend, "_store"):
        count = len(backend._store)
    elif hasattr(backend, "list_keys"):
        count = len(backend.list_keys())
    else:
        count = 0
    console.print(f"[blue]Cache backend:[/blue] {type(backend).__name__}")
    console.print(f"[blue]Cached entries:[/blue] {count}")


if __name__ == "__main__":
    app()
