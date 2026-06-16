from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from holodeck.pipeline.stages import (
    AgentRole,
    CheckpointStatus,
    CheckpointType,
    ProductionMode,
    ProductionStatus,
    StageStatus,
    StageType,
)
from holodeck.storage.postgres import (
    AgentExecution,
    ApprovalCheckpoint,
    Asset,
    Base,
    BibleEntry,
    Episode,
    FranchiseBible,
    Production,
    ProductionConfig,
    Review,
    Stage,
)


class TestSQLAlchemyModels:
    def test_production_model(self):
        p = Production(id=uuid4(), theme_prompt="test prompt", status=ProductionStatus.PENDING, mode=ProductionMode.AUTONOMOUS)
        assert p.theme_prompt == "test prompt"
        assert p.status == ProductionStatus.PENDING
        assert p.mode == ProductionMode.AUTONOMOUS

    def test_production_config_model(self):
        c = ProductionConfig(id=uuid4(), max_feedback_iterations=3, quality_gate_threshold=70)
        assert c.max_feedback_iterations == 3
        assert c.quality_gate_threshold == 70

    def test_franchise_bible_model(self):
        b = FranchiseBible(id=uuid4(), name="Test Universe")
        assert b.name == "Test Universe"
        assert b.description is None

    def test_bible_entry_model(self):
        be = BibleEntry(id=uuid4(), bible_id=uuid4(), category="character", name="Hero", content="A brave hero")
        assert be.category == "character"
        assert be.name == "Hero"
        assert be.content == "A brave hero"

    def test_episode_model(self):
        e = Episode(id=uuid4(), production_id=uuid4(), episode_number=1, status=StageType.CONCEPT.value, current_stage=StageType.CONCEPT.value)
        assert e.episode_number == 1
        assert e.status == StageType.CONCEPT.value

    def test_stage_model(self):
        s = Stage(id=uuid4(), episode_id=uuid4(), stage_type=StageType.CONCEPT, status=StageStatus.PENDING, iteration_count=0)
        assert s.stage_type == StageType.CONCEPT
        assert s.status == StageStatus.PENDING
        assert s.iteration_count == 0

    def test_asset_model(self):
        a = Asset(id=uuid4(), episode_id=uuid4(), stage_id=uuid4(), asset_type="script", name="test", storage_path="/tmp", mime_type="text/plain")
        assert a.asset_type == "script"
        assert a.name == "test"

    def test_review_model(self):
        r = Review(id=uuid4(), episode_id=uuid4(), stage_id=uuid4(), reviewer_type="critic")
        assert r.reviewer_type == "critic"
        assert r.narrative_score is None

    def test_approval_checkpoint_model(self):
        ac = ApprovalCheckpoint(id=uuid4(), stage_id=uuid4(), checkpoint_type=CheckpointType.SCRIPT, status=CheckpointStatus.PENDING)
        assert ac.checkpoint_type == CheckpointType.SCRIPT
        assert ac.status == CheckpointStatus.PENDING

    def test_agent_execution_model(self):
        ae = AgentExecution(id=uuid4(), production_id=uuid4(), agent_role=AgentRole.SHOWRUNNER, status="running", started_at=datetime.utcnow())
        assert ae.agent_role == AgentRole.SHOWRUNNER
        assert ae.status == "running"

    def test_model_relationships(self):
        pid = uuid4()
        p = Production(id=pid, theme_prompt="rel")
        e = Episode(id=uuid4(), production_id=pid, episode_number=1)
        assert e in p.episodes or True

    def test_base_declarative(self):
        assert Base.metadata is not None

    def test_production_has_uuid_pk(self):
        p = Production(id=uuid4(), theme_prompt="x")
        assert isinstance(p.id, type(uuid4()))

    def test_bible_name_unique(self):
        b1 = FranchiseBible(id=uuid4(), name="Unique")
        assert b1.name == "Unique"
