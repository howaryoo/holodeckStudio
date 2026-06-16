from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class VoiceDirectorAgent:
    stage = StageType.AUDIO
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Voice Director",
                role="You are a voice director for a TV production. You cast voices, direct vocal performances, and ensure consistent character voices across every scene. You match vocal qualities to character personalities and emotional states.",
                instructions=[
                    "Define vocal profiles for each character: pitch, accent, cadence, energy.",
                    "Describe emotional vocal delivery for key lines in each scene.",
                    "Cast voice types that match character descriptions and personality.",
                    "Ensure vocal consistency across scenes — same character, same voice.",
                    "Direct group scenes with distinct voice layering and spatial positioning.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for voice direction"])
        return ValidationResult(valid=True)

    @observe(name="voice_director.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        character_designs = context.get("character_designs", "")
        prompt = (
            f"Script:\n{script}\n\nCharacter designs:\n{character_designs}\n\n"
            "Direct the voice performances. For each character:\n"
            "CHARACTER: <name>\n"
            "- VOICE PROFILE: pitch range, accent, speech rate, vocal texture\n"
            "- CAST SUGGESTION: comparable actor or archetype\n"
            "- EMOTIONAL RANGE: how voice changes with anger, fear, joy, sadness\n"
            "\nThen per scene:\n"
            "SCENE <N>: <character lines with vocal direction in brackets>\n"
            "  e.g. [whispering, breathless] \"Did you hear that?\"\n"
            "  [booming, authoritative] \"Stand down, soldier.\"\n"
            "Be specific about delivery, pacing, and emotional inflection."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "audio", "agent": "voice_director"})

    @observe(name="voice_director.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Voice direction is too sparse.")
        prompt = (
            "Review this voice direction for character vocal distinctiveness, emotional range coverage, and per-line delivery specificity.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
