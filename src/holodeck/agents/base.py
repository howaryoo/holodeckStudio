from __future__ import annotations

import re
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


def _extract_score(text: str) -> int:
    match = re.search(r'SCORE:\s*(\d+)', text, re.IGNORECASE)
    if match:
        return min(max(int(match.group(1)), 0), 100)
    numbers = re.findall(r'\b(\d{1,3})\b', text)
    for num in numbers:
        val = int(num)
        if 0 <= val <= 100:
            return val
    return 0


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class AgentOutput(BaseModel):
    content: str
    artifacts: list[dict] = []
    metadata: dict = {}


class ReviewResult(BaseModel):
    approved: bool
    score: int = 0
    feedback: str = ""
    issues: list[str] = []


@runtime_checkable
class HolodeckAgentProtocol(Protocol):
    @property
    def stage(self) -> StageType:
        ...

    def validate_input(self, context: dict) -> ValidationResult:
        ...

    def process(self, context: dict) -> AgentOutput:
        ...

    def review_output(self, output: AgentOutput) -> ReviewResult:
        ...


class StageType(str, Enum):
    CONCEPT = "concept"
    OUTLINE = "outline"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    ASSET_GENERATION = "asset_generation"
    AUDIO = "audio"
    ANIMATION = "animation"
    RENDER = "render"
    REVIEW = "review"
    RELEASE = "release"


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


STAGE_TRANSITIONS: dict[StageType, list[StageType]] = {
    StageType.CONCEPT: [StageType.OUTLINE],
    StageType.OUTLINE: [StageType.SCRIPT],
    StageType.SCRIPT: [StageType.STORYBOARD, StageType.REVIEW],
    StageType.STORYBOARD: [StageType.ASSET_GENERATION, StageType.REVIEW],
    StageType.ASSET_GENERATION: [StageType.AUDIO, StageType.REVIEW],
    StageType.AUDIO: [StageType.ANIMATION, StageType.REVIEW],
    StageType.ANIMATION: [StageType.REVIEW],
    StageType.RENDER: [StageType.REVIEW],
    StageType.REVIEW: [StageType.RELEASE, StageType.CONCEPT, StageType.OUTLINE, StageType.SCRIPT, StageType.RENDER],
    StageType.RELEASE: [],
}

REVISION_TARGETS: dict[StageType, StageType] = {
    StageType.SCRIPT: StageType.OUTLINE,
    StageType.STORYBOARD: StageType.SCRIPT,
    StageType.ASSET_GENERATION: StageType.STORYBOARD,
    StageType.AUDIO: StageType.SCRIPT,
    StageType.ANIMATION: StageType.ASSET_GENERATION,
    StageType.RENDER: StageType.ANIMATION,
}
