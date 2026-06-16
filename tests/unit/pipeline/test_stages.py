from __future__ import annotations

from holodeck.pipeline.stages import (
    MVP_SCRIPT_STAGES,
    REVISION_TARGETS,
    STAGE_TRANSITIONS,
    StageType,
    can_transition,
    get_revision_target,
)


class TestStageTransitions:
    def test_concept_to_outline(self):
        assert can_transition(StageType.CONCEPT, StageType.OUTLINE)

    def test_concept_to_script_invalid(self):
        assert not can_transition(StageType.CONCEPT, StageType.SCRIPT)

    def test_outline_to_script(self):
        assert can_transition(StageType.OUTLINE, StageType.SCRIPT)

    def test_script_to_storyboard(self):
        assert can_transition(StageType.SCRIPT, StageType.STORYBOARD)

    def test_script_to_review(self):
        assert can_transition(StageType.SCRIPT, StageType.REVIEW)

    def test_review_to_release(self):
        assert can_transition(StageType.REVIEW, StageType.RELEASE)

    def test_review_to_concept_revision(self):
        assert can_transition(StageType.REVIEW, StageType.CONCEPT)

    def test_review_to_outline_revision(self):
        assert can_transition(StageType.REVIEW, StageType.OUTLINE)

    def test_review_to_script_revision(self):
        assert can_transition(StageType.REVIEW, StageType.SCRIPT)

    def test_release_has_no_transitions(self):
        assert STAGE_TRANSITIONS[StageType.RELEASE] == []

    def test_self_transition_not_allowed(self):
        for st in StageType:
            allowed = STAGE_TRANSITIONS.get(st, [])
            assert st not in allowed, f"{st} should not self-transition"

    def test_all_stages_have_entries(self):
        for st in StageType:
            assert st in STAGE_TRANSITIONS, f"{st} missing from transitions"

    def test_mvp_script_stages_order(self):
        assert MVP_SCRIPT_STAGES == [
            StageType.CONCEPT,
            StageType.OUTLINE,
            StageType.SCRIPT,
            StageType.REVIEW,
            StageType.RELEASE,
        ]


class TestRevisionTargets:
    def test_script_revision_goes_to_outline(self):
        assert get_revision_target(StageType.SCRIPT) == StageType.OUTLINE

    def test_storyboard_revision_goes_to_script(self):
        assert get_revision_target(StageType.STORYBOARD) == StageType.SCRIPT

    def test_concept_has_no_revision(self):
        assert get_revision_target(StageType.CONCEPT) is None

    def test_outline_has_no_revision(self):
        assert get_revision_target(StageType.OUTLINE) is None

    def test_release_has_no_revision(self):
        assert get_revision_target(StageType.RELEASE) is None


class TestStageTypeEnum:
    def test_values(self):
        assert StageType.CONCEPT.value == "concept"
        assert StageType.OUTLINE.value == "outline"
        assert StageType.SCRIPT.value == "script"
        assert StageType.REVIEW.value == "review"
        assert StageType.RELEASE.value == "release"

    def test_from_string(self):
        assert StageType("concept") == StageType.CONCEPT
        assert StageType("storyboard") == StageType.STORYBOARD
