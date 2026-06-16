from __future__ import annotations

from uuid import uuid4

import pytest

from holodeck.agents.base import AgentOutput, ReviewResult
from holodeck.memory.episode import EpisodeMemory
from holodeck.memory.production import ProductionMemory, register_production
from holodeck.pipeline.events import AsyncioEventBus
from holodeck.pipeline.orchestrator import PipelineOrchestrator
from holodeck.pipeline.runner import ProductionPipeline
from holodeck.pipeline.stages import StageType, ProductionStatus


class MockAgent:
    stage = StageType.REVIEW

    def validate_input(self, context):
        from holodeck.agents.base import ValidationResult
        return ValidationResult(valid=True)

    def process(self, context):
        name = getattr(self, "_name", "unknown")
        return AgentOutput(content=f"Output from {name}")

    def review_output(self, output):
        return ReviewResult(approved=True, score=85, feedback="good")


def _make_mock(name: str) -> MockAgent:
    a = MockAgent()
    a._name = name
    a.stage = StageType.REVIEW
    return a


@pytest.mark.asyncio
class TestPipelineFlow:
    async def test_production_memory_lifecycle(self):
        pid = uuid4()
        mem = ProductionMemory(pid)
        register_production(mem)
        assert mem.status == ProductionStatus.PENDING
        mem.set_theme_prompt("test prompt")
        assert mem.get_theme_prompt() == "test prompt"
        mem.status = ProductionStatus.RUNNING
        assert mem.status == ProductionStatus.RUNNING
        mem.add_agent_execution({"agent_role": "showrunner", "stage": "concept", "approved": True, "score": 90, "cost_usd": 0.001})
        assert len(mem.get_agent_executions()) == 1
        assert mem.calculate_total_cost() == 0.001
        mem.status = ProductionStatus.COMPLETED
        assert mem.status == ProductionStatus.COMPLETED

    async def test_episode_memory_lifecycle(self):
        eid = uuid4()
        ep = EpisodeMemory(eid)
        assert ep.current_stage == StageType.CONCEPT
        ep.set_stage_data(StageType.CONCEPT, {"output": "test"})
        assert ep.get_stage_data(StageType.CONCEPT) == {"output": "test"}
        assert ep.get_feedback_iterations(StageType.CONCEPT) == 0
        ep.increment_feedback_iteration(StageType.CONCEPT)
        assert ep.get_feedback_iterations(StageType.CONCEPT) == 1
        ep.add_review({"reviewer": "critic", "score": 85, "approved": True})
        assert len(ep.get_reviews()) == 1
        ep.current_stage = StageType.SCRIPT
        assert ep.current_stage == StageType.SCRIPT

    async def test_orchestrator_emits_events(self):
        bus = AsyncioEventBus()
        orch = PipelineOrchestrator(bus)
        pid = uuid4()
        eid = uuid4()
        sid = uuid4()
        events = []

        async def collector():
            async for e in bus.subscribe(["production.started", "stage.started", "stage.completed", "production.completed"]):
                events.append(e)
                if len(events) >= 4:
                    break

        import asyncio
        async def run():
            await orch.start_production(pid, "test prompt", "autonomous")
            await orch.start_stage(pid, eid, sid, StageType.CONCEPT, "showrunner")
            await orch.complete_stage(pid, eid, sid, StageType.CONCEPT, "showrunner")
            await orch.complete_production(pid, "/out")

        await asyncio.gather(collector(), run())
        assert len(events) == 4
        assert events[0].event_type == "production.started"
        assert events[1].event_type == "stage.started"
        assert events[2].event_type == "stage.completed"
        assert events[3].event_type == "production.completed"

    async def test_pipeline_runner_returns_result(self):
        pipeline = ProductionPipeline()
        pipeline.showrunner = _make_mock("showrunner")
        pipeline.head_writer = _make_mock("head_writer")
        pipeline.staff_writer = _make_mock("staff_writer")
        pipeline.canon_historian = _make_mock("canon_historian")
        pipeline.critic = _make_mock("critic")
        pipeline.producer = _make_mock("producer")
        pipeline.production_designer = _make_mock("production_designer")
        pipeline.director = _make_mock("director")
        pipeline.character_designer = _make_mock("character_designer")
        pipeline.environment_designer = _make_mock("environment_designer")
        pipeline.storyboard = _make_mock("storyboard")
        pipeline.composer = _make_mock("composer")
        pipeline.sound_designer = _make_mock("sound_designer")
        pipeline.voice_director = _make_mock("voice_director")
        pipeline.asset_generator = _make_mock("asset_generator")
        pipeline.animator = _make_mock("animator")
        pipeline.renderer = _make_mock("renderer")
        pipeline.qa = _make_mock("qa")
        pipeline.audience_sim = _make_mock("audience_sim")

        result = await pipeline.run("A test prompt for integration testing", use_cache=False)
        assert result.production_id is not None
        assert len(result.script) > 0
        assert len(result.canon_report) > 0
        assert len(result.critique) > 0
        assert result.budget_report is not None
        assert result.visual_style is not None
        assert result.storyboard is not None
        assert result.musical_score is not None
        assert result.sound_design is not None
        assert result.voice_direction is not None
        assert result.asset_descriptions is not None
        assert result.animation is not None
        assert result.render_plan is not None
        assert result.qa_report is not None
        assert result.audience_report is not None

    async def test_pipeline_production_state(self):
        pipeline = ProductionPipeline()
        pipeline.showrunner = _make_mock("showrunner")
        pipeline.head_writer = _make_mock("head_writer")
        pipeline.staff_writer = _make_mock("staff_writer")
        pipeline.canon_historian = _make_mock("canon_historian")
        pipeline.critic = _make_mock("critic")
        pipeline.producer = _make_mock("producer")
        pipeline.production_designer = _make_mock("production_designer")
        pipeline.director = _make_mock("director")
        pipeline.character_designer = _make_mock("character_designer")
        pipeline.environment_designer = _make_mock("environment_designer")
        pipeline.storyboard = _make_mock("storyboard")
        pipeline.composer = _make_mock("composer")
        pipeline.sound_designer = _make_mock("sound_designer")
        pipeline.voice_director = _make_mock("voice_director")
        pipeline.asset_generator = _make_mock("asset_generator")
        pipeline.animator = _make_mock("animator")
        pipeline.renderer = _make_mock("renderer")
        pipeline.qa = _make_mock("qa")
        pipeline.audience_sim = _make_mock("audience_sim")
        pipeline.voice_synth = _make_mock("voice_synth")
        pipeline.frame_renderer = _make_mock("frame_renderer")
        pipeline.video_assembler = _make_mock("video_assembler")

        from holodeck.memory.production import get_production
        result = await pipeline.run("State test prompt", use_cache=False)
        prod = get_production(result.production_id)
        assert prod is not None
        assert prod.status == ProductionStatus.COMPLETED
        assert len(prod.get_agent_executions()) == 22
        assert prod.get_theme_prompt() == "State test prompt"
        assert prod.calculate_total_cost() >= 0

    async def test_pipeline_error_handling(self):
        pipeline = ProductionPipeline()
        bad_agent = MockAgent()
        bad_agent._name = "showrunner"

        def _bad_process(ctx):
            raise RuntimeError("mock failure")

        bad_agent.process = _bad_process
        pipeline.showrunner = bad_agent
        pipeline.head_writer = _make_mock("hw")
        pipeline.staff_writer = _make_mock("sw")
        pipeline.canon_historian = _make_mock("ch")
        pipeline.critic = _make_mock("c")
        pipeline.producer = _make_mock("p")
        pipeline.production_designer = _make_mock("production_designer")
        pipeline.director = _make_mock("director")
        pipeline.character_designer = _make_mock("character_designer")
        pipeline.environment_designer = _make_mock("environment_designer")
        pipeline.storyboard = _make_mock("storyboard")
        pipeline.composer = _make_mock("composer")
        pipeline.sound_designer = _make_mock("sound_designer")
        pipeline.voice_director = _make_mock("voice_director")
        pipeline.asset_generator = _make_mock("asset_generator")
        pipeline.animator = _make_mock("animator")
        pipeline.renderer = _make_mock("renderer")
        pipeline.qa = _make_mock("qa")
        pipeline.audience_sim = _make_mock("audience_sim")

        with pytest.raises(RuntimeError, match="mock failure"):
            await pipeline.run("Error test", use_cache=False)

    async def test_pipeline_with_bible_context(self):
        pipeline = ProductionPipeline()
        pipeline.showrunner = _make_mock("showrunner")
        pipeline.head_writer = _make_mock("head_writer")
        pipeline.staff_writer = _make_mock("staff_writer")
        pipeline.canon_historian = _make_mock("canon_historian")
        pipeline.critic = _make_mock("critic")
        pipeline.producer = _make_mock("producer")
        pipeline.production_designer = _make_mock("production_designer")
        pipeline.director = _make_mock("director")
        pipeline.character_designer = _make_mock("character_designer")
        pipeline.environment_designer = _make_mock("environment_designer")
        pipeline.storyboard = _make_mock("storyboard")
        pipeline.composer = _make_mock("composer")
        pipeline.sound_designer = _make_mock("sound_designer")
        pipeline.voice_director = _make_mock("voice_director")
        pipeline.asset_generator = _make_mock("asset_generator")
        pipeline.animator = _make_mock("animator")
        pipeline.renderer = _make_mock("renderer")
        pipeline.qa = _make_mock("qa")
        pipeline.audience_sim = _make_mock("audience_sim")

        from holodeck.memory.franchise_bible import create_bible
        bible = create_bible("Test Bible", "For testing")
        await bible.add_entry("character", "Hero", "Brave hero")
        result = await pipeline.run("Bible test", bible=str(bible.id), use_cache=False)
        assert result.production_id is not None
