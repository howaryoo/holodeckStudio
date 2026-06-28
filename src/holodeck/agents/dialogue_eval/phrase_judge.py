from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from agno.agent import Agent

from holodeck.agents.dialogue_eval.schemas import DimensionResult, LinePhraseScore
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model

_FRIENDS_CHARACTERS = {"RACHEL", "MONICA", "PHOEBE", "JOEY", "CHANDLER", "ROSS"}

_CHARACTER_PROFILES = """
## Friends Character Voice Profiles

### RACHEL
Core signals: fashion/beauty references, emotional candour, past-privilege irony,
  sarcastic when defensive, grew from spoiled to independent
Red flags: academic or scientific vocabulary, engineering/medical terminology

### MONICA
Core signals: competition framing, cooking/food metaphors, direct instruction,
  perfectionist language, nurturing but controlling
Red flags: careless or disorganised language, indifference to quality or cleanliness

### PHOEBE
Core signals: non-sequiturs, spiritual/mystical references, earnest tone,
  unusual beliefs stated as fact, songs or poetry fragments
Red flags: cynicism, sarcasm without warmth, materialistic focus

### JOEY
Core signals: short sentences, food and acting references,
  literal interpretation of figurative speech, charming and simple
Red flags: sarcasm, complex abstractions, academic vocabulary, self-deprecation

### CHANDLER
Core signals: rhetorical self-deprecation, parenthetical jokes that undercut sincere
  statements, "Could X BE any more Y?" pattern
Red flags: earnest declarations without comic undercut, confidence without irony

### ROSS
Core signals: scientific analogies, over-explanation, passionate digression into
  paleontology or history, correct-the-record impulse
Red flags: casual dismissal of facts, anti-intellectual statements,
  unqualified opinions stated as fact
"""

_SYSTEM_PROMPT = f"""You are a dialogue quality judge for the TV show Friends.
You score individual dialogue lines for character authenticity, naturalness,
and comedy contribution.

{_CHARACTER_PROFILES}

## Task
Given a character name and one dialogue line, return a JSON object with EXACTLY these keys:
- character_authenticity: {{"score": <int 0-10>, "reasoning": "<1-2 sentences>"}}
- dialogue_naturalness: {{"score": <int 0-10>, "reasoning": "<1-2 sentences>"}}
- comedy_contribution: {{"score": <int 0-10>, "reasoning": "<1-2 sentences>"}}

Scoring guide:
- character_authenticity: Does this sound exactly like this character?
  10=perfect voice, 0=completely wrong
- dialogue_naturalness: Could an actor deliver this naturally on stage?
  10=flows perfectly, 0=stilted/undeliverable
- comedy_contribution: Does this line land a joke, set one up, or pay one off?
  10=hilarious, 0=no comedy value

Return ONLY the JSON object. No markdown, no preamble.
"""


def _extract_json(content: str) -> dict[str, Any]:
    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\s*", "", content).strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"Failed to parse PhraseJudge response — no JSON found: {content[:200]!r}")
    raw = match.group()
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        # Replace smart quotes and other common LLM response quirks
        cleaned = raw.replace("‘", "'").replace("’", "'")
        cleaned = cleaned.replace("“", '"').replace("”", '"')
        try:
            return json.loads(cleaned)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse PhraseJudge response — invalid JSON: {exc}\n"
                f"Raw content: {raw[:300]!r}"
            ) from exc


class PhraseJudge:
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict[str, Any] = dict(
                name="PhraseJudge",
                role="Score dialogue lines for character authenticity, naturalness, and comedy.",
                instructions=[_SYSTEM_PROMPT],
                structured_outputs=True,
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    @observe(name="phrase_judge.score", as_type="generation")
    def score(self, character: str, text: str) -> LinePhraseScore:
        if not text.strip():
            empty = DimensionResult(score=0, reasoning="empty line — nothing to evaluate")
            return LinePhraseScore(
                character=character,
                text=text,
                character_authenticity=empty,
                dialogue_naturalness=empty,
                comedy_contribution=empty,
            )

        char_upper = character.upper()
        is_known = char_upper in _FRIENDS_CHARACTERS

        if is_known:
            prompt = f'Character: {char_upper}\nLine: "{text}"'
            response = self._get_agent().run(prompt)
            try:
                raw = _extract_json(str(response.content))
                return LinePhraseScore(
                    character=character,
                    text=text,
                    character_authenticity=DimensionResult(**raw["character_authenticity"]),
                    dialogue_naturalness=DimensionResult(**raw["dialogue_naturalness"]),
                    comedy_contribution=DimensionResult(**raw["comedy_contribution"]),
                )
            except (ValueError, KeyError):
                fallback = DimensionResult(score=5, reasoning="parse error — could not score")
                return LinePhraseScore(
                    character=character, text=text,
                    character_authenticity=fallback,
                    dialogue_naturalness=fallback,
                    comedy_contribution=fallback,
                )
        else:
            prompt = (
                f'Character: {char_upper} (not a main Friends character — skip authenticity)\n'
                f'Line: "{text}"\n'
                f'Return JSON with only dialogue_naturalness and comedy_contribution keys.'
            )
            response = self._get_agent().run(prompt)
            try:
                raw = _extract_json(str(response.content))
                return LinePhraseScore(
                    character=character,
                    text=text,
                    character_authenticity=DimensionResult(
                        score=0,
                        reasoning="unknown character — authenticity not scored",
                    ),
                    dialogue_naturalness=DimensionResult(**raw["dialogue_naturalness"]),
                    comedy_contribution=DimensionResult(**raw["comedy_contribution"]),
                )
            except (ValueError, KeyError):
                fallback = DimensionResult(score=5, reasoning="parse error — could not score")
                return LinePhraseScore(
                    character=character, text=text,
                    character_authenticity=DimensionResult(
                        score=0, reasoning="unknown character — authenticity not scored"
                    ),
                    dialogue_naturalness=fallback,
                    comedy_contribution=fallback,
                )
