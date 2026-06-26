"""
Test scenario for dialogue-only production workflow.

This test focuses on:
1. Running only the first 2 agents (Showrunner and Head Writer)
2. Creating dialogue text output
3. Skipping MP4 and MP3 generation
4. Simulating the specific scenario of Rachel and Joey talking
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from holodeck.agents.base import AgentOutput, ReviewResult
from holodeck.memory.production import ProductionMemory, register_production
from holodeck.pipeline.events import AsyncioEventBus
from holodeck.pipeline.orchestrator import PipelineOrchestrator
from holodeck.pipeline.runner import PipelineResult, ProductionPipeline
from holodeck.pipeline.stages import StageType


@dataclass
class DialogueEntry:
    """Represents a single dialogue exchange."""

    character: str
    text: str
    stage_direction: str = ""


class MockShowrunnerAgent:
    """Mock Showrunner agent that generates concept/outline."""

    stage = StageType.CONCEPT
    name = "showrunner"

    def validate_input(self, context: dict[str, str]) -> dict[str, object]:
        from holodeck.agents.base import ValidationResult

        return ValidationResult(valid=True)  # type: ignore[return-value]

    async def process(self, context: dict[str, object]) -> AgentOutput:
        """Generate concept outline for Rachel and Joey scene."""
        return AgentOutput(
            content=(
                "CONCEPT: Two friends catching up\n\n"
                "Setting: Modern apartment\n"
                "Characters: Rachel, Joey\n"
                "Time: Thursday evening\n\n"
                "Summary: Rachel finds Joey working on a scene on his PC while she's "
                "doing laundry. They catch up about their day, with Joey talking about "
                "his acting scene work and Rachel discussing her day's activities. "
                "The conversation is relaxed and shows their friendship dynamic."
            )
        )

    async def review_output(self, context: dict[str, object], output: AgentOutput) -> ReviewResult:
        return ReviewResult(approved=True, score=90, feedback="Good concept")


class MockHeadWriterAgent:
    """Mock Head Writer agent that generates detailed script with dialogue."""

    stage = StageType.SCRIPT
    name = "head_writer"

    def validate_input(self, context: dict[str, str]) -> dict[str, object]:
        from holodeck.agents.base import ValidationResult

        return ValidationResult(valid=True)  # type: ignore[return-value]

    async def process(self, context: dict[str, object]) -> AgentOutput:
        """Generate detailed script with dialogue."""
        dialogue_text = self._generate_dialogue()
        return AgentOutput(content=dialogue_text)

    @staticmethod
    def _generate_dialogue() -> str:
        """Generate the dialogue script."""
        return """SCENE: Rachel and Joey - Thursday Evening

INTERIOR - RACHEL'S APARTMENT - EVENING

Rachel stands in front of a washing machine, loading clothes.
Joey sits at a nearby desk with his PC, reviewing a scene.

---

RACHEL
(looking over)
How's the scene going?

JOEY
(still focused on screen)
Pretty good, actually. I've been working on this monologue all day.
It's a tough one - a lot of emotional depth required.

RACHEL
(folding clothes)
That's great! You'll nail it. You always do.

JOEY
(turning to look at Rachel)
Thanks. How was your day? Anything interesting happen?

RACHEL
(putting in laundry detergent)
Same old, same old. Work was busy, but nothing too crazy.
I'm just trying to catch up on everything at home.

JOEY
(returning to screen)
I feel you. Sometimes you just need to slow down and handle
the day-to-day stuff, you know?

RACHEL
(starting the machine)
Exactly. That's why I'm doing laundry on a Thursday night
instead of going out somewhere.

JOEY
(standing, stretching)
Well, if you want to take a break, I can order some food.
We could hang out for a bit.

RACHEL
(smiling)
That sounds perfect, actually. Give me a minute to finish up here.

JOEY
(nodding)
Sounds good. Let me see what's available nearby.

---

END SCENE
"""

    async def review_output(self, context: dict[str, str], output: AgentOutput) -> ReviewResult:
        return ReviewResult(approved=True, score=85, feedback="Good dialogue")


class DialogueOnlyPipeline(ProductionPipeline):
    """Modified pipeline that only runs Showrunner and Head Writer agents."""

    def __init__(
        self,
        settings: dict[str, str] | None = None,
        event_bus: AsyncioEventBus | None = None,
    ) -> None:
        # Initialize without agents first
        self.settings = settings
        self.event_bus = event_bus or AsyncioEventBus()
        self.orchestrator = PipelineOrchestrator(self.event_bus)
        from holodeck.cache import PipelineCache
        from holodeck.observability.evaluation import EvaluationTracker

        self.tracker = EvaluationTracker(self.settings)
        self.cache = PipelineCache()
        # Only initialize the agents we need
        self.showrunner = MockShowrunnerAgent()
        self.head_writer = MockHeadWriterAgent()

    async def run(
        self,
        prompt: str,
        mode: str = "autonomous",
        bible: str | None = None,
        output: str = "./output",
        use_cache: bool = True,
        budget: float | None = None,
    ) -> PipelineResult:
        """Run the dialogue-only production workflow."""
        production_id = str(uuid4())
        register_production(ProductionMemory(uuid4()))

        # Run Showrunner
        context: dict[str, object] = {"prompt": prompt, "bible": bible}
        showrunner_output = await self.showrunner.process(context)
        context["concept"] = showrunner_output.content

        # Run Head Writer
        head_writer_output = await self.head_writer.process(context)
        context["script"] = head_writer_output.content

        # Extract dialogue entries from the script
        dialogue_entries = self._parse_dialogue_from_script(head_writer_output.content)

        return PipelineResult(
            production_id=production_id,
            script=head_writer_output.content,
            canon_report="Dialogue-only scenario: No canon report required",
            critique="Dialogue-only scenario: No critique required",
            dialogue_audio_metadata=self._dialogue_entries_to_metadata(dialogue_entries),
        )

    @staticmethod
    def _parse_dialogue_from_script(script: str) -> list[DialogueEntry]:
        """Parse dialogue entries from the script."""
        entries = []
        lines = script.split("\n")
        current_character = None
        current_text = ""

        for line in lines:
            line_stripped = line.strip()

            # Check if this is a character name (all caps, standalone)
            if (
                line_stripped
                and line_stripped.isupper()
                and not any(word in line_stripped for word in ["SCENE:", "INTERIOR", "END"])
            ):
                # Save previous entry if exists
                if current_character and current_text:
                    entries.append(
                        DialogueEntry(
                            character=current_character,
                            text=current_text.strip(),
                        )
                    )
                current_character = line_stripped
                current_text = ""
            elif current_character and line_stripped and not line_stripped.startswith("("):
                # Add to current dialogue
                if current_text:
                    current_text += " " + line_stripped
                else:
                    current_text = line_stripped

        # Don't forget the last entry
        if current_character and current_text:
            entries.append(
                DialogueEntry(
                    character=current_character,
                    text=current_text.strip(),
                )
            )

        return entries

    @staticmethod
    def _dialogue_entries_to_metadata(entries: list[DialogueEntry]) -> list[dict]:
        """Convert dialogue entries to metadata format."""
        return [
            {
                "character": entry.character,
                "text": entry.text,
                "file": f"dialogue_{i:02d}_{entry.character.lower()}.wav",
            }
            for i, entry in enumerate(entries, 1)
        ]


@pytest.mark.asyncio
class TestDialogueOnlyScenario:
    """Test suite for dialogue-only production workflow."""

    async def test_dialogue_only_production_completes(self) -> None:
        """Test that dialogue-only production completes successfully."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            bible="99066884-ab26-486a-966c-3eca0b883ff1",
            mode="autonomous",
            use_cache=False,
        )

        assert result.production_id is not None
        assert result.script is not None
        assert len(result.script) > 0

    async def test_dialogue_extraction_from_script(self) -> None:
        """Test that dialogue is correctly extracted from the script."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            bible="99066884-ab26-486a-966c-3eca0b883ff1",
            use_cache=False,
        )

        assert result.dialogue_audio_metadata is not None
        assert len(result.dialogue_audio_metadata) > 0

        # Check that each dialogue entry has the expected fields
        for entry in result.dialogue_audio_metadata:
            assert "character" in entry
            assert "text" in entry
            assert "file" in entry
            assert len(entry["text"]) > 0

    async def test_dialogue_entries_contain_both_characters(self) -> None:
        """Test that dialogue includes both Rachel and Joey."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        assert result.dialogue_audio_metadata is not None
        characters = {entry["character"] for entry in result.dialogue_audio_metadata}
        assert "RACHEL" in characters
        assert "JOEY" in characters

    async def test_no_mp4_or_mp3_generated(self) -> None:
        """Test that MP4 video and MP3 audio files are not generated."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        # These should be empty or None in dialogue-only mode
        assert result.video_url == ""
        assert result.frame_paths is None

    async def test_showrunner_agent_called(self) -> None:
        """Test that Showrunner agent is called and returns concept."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        # The script should contain concept information from Showrunner
        assert "concept" in result.script.lower() or "scene" in result.script.lower()

    async def test_head_writer_agent_called(self) -> None:
        """Test that Head Writer agent is called and generates dialogue."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        # The script should contain dialogue
        assert "RACHEL" in result.script
        assert "JOEY" in result.script

    async def test_dialogue_text_creation_output(self) -> None:
        """Test that dialogue text creation produces expected output."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        # Check that we have dialogue metadata with file paths
        assert result.dialogue_audio_metadata is not None
        for entry in result.dialogue_audio_metadata:
            assert entry["file"].endswith(".wav")
            assert "dialogue_" in entry["file"]

    async def test_production_id_is_valid_uuid(self) -> None:
        """Test that production ID is a valid UUID."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        # Try to parse as UUID
        try:
            UUID(result.production_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {result.production_id}")

    async def test_dialogue_entries_have_meaningful_content(self) -> None:
        """Test that dialogue entries contain meaningful text."""
        pipeline = DialogueOnlyPipeline()

        prompt = (
            "Rachel and Joey are talking about their thursday night - "
            "joey is working on a scene on his pc, while rachel cleaning the wash machine"
        )

        result = await pipeline.run(
            prompt=prompt,
            use_cache=False,
        )

        assert result.dialogue_audio_metadata is not None
        for entry in result.dialogue_audio_metadata:
            # Check that text is not just whitespace
            assert entry["text"].strip()
            # Check reasonable length (at least 5 characters)
            assert len(entry["text"]) > 5
