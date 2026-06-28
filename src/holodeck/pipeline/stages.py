from __future__ import annotations

from enum import Enum



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


class ProductionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    SUPERVISED = "supervised"


class CheckpointType(str, Enum):
    STORY = "story"
    SCRIPT = "script"
    VISUAL = "visual"
    FINAL_RELEASE = "final_release"


class CheckpointStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


class AgentRole(str, Enum):
    SHOWRUNNER = "showrunner"
    PRODUCER = "producer"
    HEAD_WRITER = "head_writer"
    STAFF_WRITER = "staff_writer"
    CANON_HISTORIAN = "canon_historian"
    PRODUCTION_DESIGNER = "production_designer"
    CHARACTER_DESIGNER = "character_designer"
    ENVIRONMENT_DESIGNER = "environment_designer"
    DIRECTOR = "director"
    STORYBOARD = "storyboard"
    COMPOSER = "composer"
    SOUND_DESIGNER = "sound_designer"
    VOICE_DIRECTOR = "voice_director"
    ASSET_GENERATION = "asset_generation"
    ANIMATION = "animation"
    RENDERING = "rendering"
    CRITIC = "critic"
    AUDIENCE_SIMULATION = "audience_simulation"
    QA = "qa"


STAGE_TRANSITIONS: dict[StageType, list[StageType]] = {
    StageType.CONCEPT: [StageType.OUTLINE],
    StageType.OUTLINE: [StageType.SCRIPT],
    StageType.SCRIPT: [StageType.STORYBOARD, StageType.REVIEW],
    StageType.STORYBOARD: [StageType.ASSET_GENERATION, StageType.REVIEW],
    StageType.ASSET_GENERATION: [StageType.AUDIO, StageType.REVIEW],
    StageType.AUDIO: [StageType.ANIMATION, StageType.REVIEW],
    StageType.ANIMATION: [StageType.REVIEW],
    StageType.RENDER: [StageType.REVIEW],
    StageType.REVIEW: [
        StageType.RELEASE,
        StageType.CONCEPT,
        StageType.OUTLINE,
        StageType.SCRIPT,
        StageType.RENDER,
    ],
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

MVP_SCRIPT_STAGES: list[StageType] = [
    StageType.CONCEPT,
    StageType.OUTLINE,
    StageType.SCRIPT,
    StageType.REVIEW,
    StageType.RELEASE,
]


def can_transition(from_stage: StageType, to_stage: StageType) -> bool:
    return to_stage in STAGE_TRANSITIONS.get(from_stage, [])


def get_revision_target(stage: StageType) -> StageType | None:
    return REVISION_TARGETS.get(stage)