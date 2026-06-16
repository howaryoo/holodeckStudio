from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import uuid4

from holodeck.cache import PipelineCache

logger = logging.getLogger(__name__)
from holodeck.config.settings import Settings
from holodeck.pipeline.events import AsyncioEventBus
from holodeck.pipeline.orchestrator import PipelineOrchestrator
from holodeck.pipeline.stages import StageType, ProductionStatus


@dataclass
class PipelineResult:
    production_id: str
    script: str
    canon_report: str
    critique: str
    budget_report: str = ""
    visual_style: str = ""
    visual_direction: str = ""
    character_designs: str = ""
    environment_designs: str = ""
    storyboard: str = ""
    musical_score: str = ""
    sound_design: str = ""
    voice_direction: str = ""
    asset_descriptions: str = ""
    animation: str = ""
    render_plan: str = ""
    qa_report: str = ""
    audience_report: str = ""
    dialogue_audio_urls: list[str] | None = None
    frame_paths: list[str] | None = None
    video_url: str = ""
    stage_outputs: dict = field(default_factory=dict)


class ProductionPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        event_bus: AsyncioEventBus | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.event_bus = event_bus or AsyncioEventBus()
        self.orchestrator = PipelineOrchestrator(self.event_bus)
        from holodeck.observability.evaluation import EvaluationTracker
        self.tracker = EvaluationTracker(self.settings)
        self.cache = PipelineCache()
        self._init_agents()

    def _init_agents(self) -> None:
        from holodeck.agents.review.critic import CriticAgent
        from holodeck.agents.showrunner import ShowrunnerAgent
        from holodeck.agents.writers.canon_historian import CanonHistorianAgent
        from holodeck.agents.writers.head_writer import HeadWriterAgent
        from holodeck.agents.writers.staff_writer import StaffWriterAgent
        from holodeck.config.registry import model_for_agent

        self.showrunner = ShowrunnerAgent(
            model=model_for_agent("showrunner", self.settings)
        )
        self.head_writer = HeadWriterAgent(
            model=model_for_agent("head_writer", self.settings)
        )
        self.staff_writer = StaffWriterAgent(
            model=model_for_agent("staff_writer", self.settings)
        )
        self.canon_historian = CanonHistorianAgent(
            model=model_for_agent("canon_historian", self.settings)
        )
        self.critic = CriticAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.producer import ProducerAgent
        self.producer = ProducerAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.design.production_designer import ProductionDesignerAgent
        from holodeck.agents.directing.director import DirectorAgent
        from holodeck.agents.design.character_designer import CharacterDesignerAgent
        from holodeck.agents.design.environment_designer import EnvironmentDesignerAgent
        from holodeck.agents.directing.storyboard import StoryboardAgent
        self.production_designer = ProductionDesignerAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.director = DirectorAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.character_designer = CharacterDesignerAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.environment_designer = EnvironmentDesignerAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.storyboard = StoryboardAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.audio.composer import ComposerAgent
        from holodeck.agents.audio.sound_designer import SoundDesignerAgent
        from holodeck.agents.audio.voice_director import VoiceDirectorAgent
        self.composer = ComposerAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.sound_designer = SoundDesignerAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.voice_director = VoiceDirectorAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.production.asset_generation import AssetGenerationAgent
        from holodeck.agents.production.animation import AnimationAgent
        from holodeck.agents.production.rendering import RenderingAgent
        from holodeck.agents.review.qa import QAAgent
        self.asset_generator = AssetGenerationAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.animator = AnimationAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.renderer = RenderingAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.qa = QAAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.review.audience_simulation import AudienceSimulationAgent
        self.audience_sim = AudienceSimulationAgent(
            model=model_for_agent("critic", self.settings)
        )
        from holodeck.agents.audio.voice_synthesis import VoiceSynthesisAgent
        from holodeck.agents.video.frame_renderer import FrameRendererAgent
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent
        self.voice_synth = VoiceSynthesisAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.frame_renderer = FrameRendererAgent(
            model=model_for_agent("critic", self.settings)
        )
        self.video_assembler = VideoAssemblerAgent(
            model=model_for_agent("critic", self.settings)
        )

    def _estimate_cost(self, text: str, input_text: str = "") -> dict:
        in_tokens = max(1, len(input_text) // 4)
        out_tokens = max(1, len(text) // 4)
        cost_usd = (in_tokens * 0.0000015) + (out_tokens * 0.000006)
        return {"input_tokens": in_tokens, "output_tokens": out_tokens, "cost_usd": round(cost_usd, 6)}

    async def run(
        self,
        prompt: str,
        mode: str = "autonomous",
        bible: str | None = None,
        output: str = "./output",
        use_cache: bool = True,
        budget: float | None = None,
    ) -> PipelineResult:
        from holodeck.memory.production import ProductionMemory
        from holodeck.memory.episode import EpisodeMemory
        import time as _time

        if use_cache:
            cached = self.cache.get(prompt, bible, mode)
            if cached is not None:
                return PipelineResult(**cached)

        production_id = uuid4()
        episode_id = uuid4()
        context: dict = {"theme_prompt": prompt, "use_cache": use_cache, "mode": mode, "production_id": production_id, "episode_id": episode_id, "output_dir": output}
        if budget is not None:
            context["budget_usd"] = budget
            self.producer.set_budget(budget)

        prod_memory = ProductionMemory(production_id)
        prod_memory.set_theme_prompt(prompt)
        from holodeck.memory.production import register_production
        register_production(prod_memory)
        ep_memory = EpisodeMemory(episode_id)
        prod_memory.register_episode_memory(episode_id, ep_memory)

        await self.orchestrator.start_production(production_id, prompt, mode)

        try:
            # Stage 1: Showrunner — creative direction
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.CONCEPT, "showrunner"
            )
            t0 = _time.monotonic()
            self.showrunner.validate_input(context)
            showrunner_output = self.showrunner.process(context)
            context["creative_direction"] = showrunner_output.content
            context["outline"] = ""
            showrunner_review = self.showrunner.review_output(showrunner_output)
            cost_info = self._estimate_cost(showrunner_output.content, prompt)
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "showrunner", "stage": "concept", "approved": showrunner_review.approved, "score": showrunner_review.score, **cost_info})
            self.tracker.record_cost(production_id, "concept", "showrunner", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("showrunner", "concept", showrunner_review.score, duration)
            ep_memory.set_stage_data(StageType.CONCEPT, {"output": showrunner_output.content, "review": showrunner_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.CONCEPT, "showrunner"
            )

            # Stage 2: Head Writer — script draft
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.SCRIPT, "head_writer"
            )
            t0 = _time.monotonic()
            self.head_writer.validate_input(context)
            head_writer_output = self.head_writer.process(context)
            context["script_draft"] = head_writer_output.content
            head_writer_review = self.head_writer.review_output(head_writer_output)
            cost_info = self._estimate_cost(head_writer_output.content, context.get("creative_direction", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "head_writer", "stage": "script", "approved": head_writer_review.approved, "score": head_writer_review.score, **cost_info})
            self.tracker.record_cost(production_id, "script", "head_writer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("head_writer", "script", head_writer_review.score, duration)
            ep_memory.set_stage_data(StageType.SCRIPT, {"draft": head_writer_output.content, "review": head_writer_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.SCRIPT, "head_writer"
            )

            # Stage 3: Staff Writer — scene refinement
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.SCRIPT, "staff_writer"
            )
            t0 = _time.monotonic()
            context["scene_direction"] = head_writer_output.content
            self.staff_writer.validate_input(context)
            staff_writer_output = self.staff_writer.process(context)
            context["script"] = staff_writer_output.content
            staff_writer_review = self.staff_writer.review_output(staff_writer_output)
            cost_info = self._estimate_cost(staff_writer_output.content, context.get("script_draft", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "staff_writer", "stage": "script", "approved": staff_writer_review.approved, "score": staff_writer_review.score, **cost_info})
            self.tracker.record_cost(production_id, "script", "staff_writer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("staff_writer", "script", staff_writer_review.score, duration)
            ep_memory.set_stage_data(StageType.SCRIPT, {"refined": staff_writer_output.content, "review": staff_writer_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.SCRIPT, "staff_writer"
            )

            # Checkpoint: SCRIPT approval (emits event; supervised mode pauses via CLI)
            await self.orchestrator.checkpoint_approval(
                production_id, episode_id, stage_id, StageType.SCRIPT,
                mode=context.get("mode", "autonomous"),
                quality_score=staff_writer_review.score,
            )

            # Stage 4: Canon Historian — canon verification
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id,
                episode_id,
                stage_id,
                StageType.REVIEW,
                "canon_historian",
            )
            t0 = _time.monotonic()
            context["bible_id"] = bible
            if bible:
                from holodeck.memory.franchise_bible import get_bible
                fb = get_bible(bible)
                if fb:
                    context["bible_entries"] = fb.get_entries()
            self.canon_historian.validate_input(context)
            canon_output = self.canon_historian.process(context)
            context["canon_report"] = canon_output.content
            canon_review = self.canon_historian.review_output(canon_output)
            cost_info = self._estimate_cost(canon_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            ep_memory.add_review({"reviewer": "canon_historian", "report": canon_output.content, "approved": canon_review.approved, "score": canon_review.score})
            prod_memory.add_agent_execution({"agent_role": "canon_historian", "stage": "review", "approved": canon_review.approved, "score": canon_review.score, **cost_info})
            self.tracker.record_cost(production_id, "review", "canon_historian", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("canon_historian", "review", canon_review.score, duration)
            await self.orchestrator.complete_stage(
                production_id,
                episode_id,
                stage_id,
                StageType.REVIEW,
                "canon_historian",
            )

            # Stage 5: Critic — narrative review
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "critic"
            )
            t0 = _time.monotonic()
            context["content"] = context["script"]
            self.critic.validate_input(context)
            critic_output = self.critic.process(context)
            context["critique"] = critic_output.content
            critic_review = self.critic.review_output(critic_output)
            cost_info = self._estimate_cost(critic_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            ep_memory.add_review({"reviewer": "critic", "critique": critic_output.content, "approved": critic_review.approved, "score": critic_review.score})
            prod_memory.add_agent_execution({"agent_role": "critic", "stage": "review", "approved": critic_review.approved, "score": critic_review.score, **cost_info})
            self.tracker.record_cost(production_id, "review", "critic", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("critic", "review", critic_review.score, duration)
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "critic"
            )

            # Stage 6: Producer — budget assessment
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "producer"
            )
            t0 = _time.monotonic()
            context["agent_executions"] = prod_memory.get_agent_executions()
            context["total_cost_usd"] = prod_memory.calculate_total_cost()
            producer_output = self.producer.process(context)
            producer_review = self.producer.review_output(producer_output)
            cost_info = self._estimate_cost(producer_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "producer", "stage": "review", "approved": producer_review.approved, "score": producer_review.score, **cost_info})
            self.tracker.record_cost(production_id, "review", "producer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("producer", "review", producer_review.score, duration)
            context["budget_report"] = producer_output.content
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "producer"
            )

            if prod_memory.status == ProductionStatus.PAUSED:
                context["_paused_at"] = "review_checkpoint"

            # Stage 7: Production Designer — visual style guide
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "production_designer"
            )
            t0 = _time.monotonic()
            self.production_designer.validate_input(context)
            style_output = self.production_designer.process(context)
            context["visual_style"] = style_output.content
            style_review = self.production_designer.review_output(style_output)
            cost_info = self._estimate_cost(style_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "production_designer", "stage": "asset_generation", "approved": style_review.approved, "score": style_review.score, **cost_info})
            self.tracker.record_cost(production_id, "asset_generation", "production_designer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("production_designer", "asset_generation", style_review.score, duration)
            ep_memory.set_stage_data(StageType.ASSET_GENERATION, {"style_guide": style_output.content, "review": style_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "production_designer"
            )

            # Stage 8: Director — visual direction from script + style guide
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.STORYBOARD, "director"
            )
            t0 = _time.monotonic()
            self.director.validate_input(context)
            director_output = self.director.process(context)
            context["visual_direction"] = director_output.content
            director_review = self.director.review_output(director_output)
            cost_info = self._estimate_cost(director_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "director", "stage": "storyboard", "approved": director_review.approved, "score": director_review.score, **cost_info})
            self.tracker.record_cost(production_id, "storyboard", "director", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("director", "storyboard", director_review.score, duration)
            ep_memory.set_stage_data(StageType.STORYBOARD, {"visual_direction": director_output.content, "review": director_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.STORYBOARD, "director"
            )

            # Stage 9: Character Designer — character sheets
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "character_designer"
            )
            t0 = _time.monotonic()
            self.character_designer.validate_input(context)
            character_output = self.character_designer.process(context)
            context["character_designs"] = character_output.content
            character_review = self.character_designer.review_output(character_output)
            cost_info = self._estimate_cost(character_output.content, context.get("visual_style", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "character_designer", "stage": "asset_generation", "approved": character_review.approved, "score": character_review.score, **cost_info})
            self.tracker.record_cost(production_id, "asset_generation", "character_designer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("character_designer", "asset_generation", character_review.score, duration)
            ep_memory.set_stage_data(StageType.ASSET_GENERATION, {"character_designs": character_output.content, "review": character_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "character_designer"
            )

            # Stage 10: Environment Designer — location designs
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "environment_designer"
            )
            t0 = _time.monotonic()
            self.environment_designer.validate_input(context)
            env_output = self.environment_designer.process(context)
            context["environment_designs"] = env_output.content
            env_review = self.environment_designer.review_output(env_output)
            cost_info = self._estimate_cost(env_output.content, context.get("visual_style", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "environment_designer", "stage": "asset_generation", "approved": env_review.approved, "score": env_review.score, **cost_info})
            self.tracker.record_cost(production_id, "asset_generation", "environment_designer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("environment_designer", "asset_generation", env_review.score, duration)
            ep_memory.set_stage_data(StageType.ASSET_GENERATION, {"environment_designs": env_output.content, "review": env_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "environment_designer"
            )

            # Stage 11: Storyboard Artist — storyboard frames
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.STORYBOARD, "storyboard"
            )
            t0 = _time.monotonic()
            self.storyboard.validate_input(context)
            storyboard_output = self.storyboard.process(context)
            context["storyboard"] = storyboard_output.content
            storyboard_review = self.storyboard.review_output(storyboard_output)
            cost_info = self._estimate_cost(storyboard_output.content, context.get("visual_direction", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "storyboard", "stage": "storyboard", "approved": storyboard_review.approved, "score": storyboard_review.score, **cost_info})
            self.tracker.record_cost(production_id, "storyboard", "storyboard", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("storyboard", "storyboard", storyboard_review.score, duration)
            ep_memory.set_stage_data(StageType.STORYBOARD, {"storyboard": storyboard_output.content, "review": storyboard_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.STORYBOARD, "storyboard"
            )

            # Stage 12: Composer — musical score
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "composer"
            )
            t0 = _time.monotonic()
            self.composer.validate_input(context)
            composer_output = self.composer.process(context)
            context["musical_score"] = composer_output.content
            composer_review = self.composer.review_output(composer_output)
            cost_info = self._estimate_cost(composer_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "composer", "stage": "audio", "approved": composer_review.approved, "score": composer_review.score, **cost_info})
            self.tracker.record_cost(production_id, "audio", "composer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("composer", "audio", composer_review.score, duration)
            ep_memory.set_stage_data(StageType.AUDIO, {"musical_score": composer_output.content, "review": composer_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "composer"
            )

            # Stage 13: Sound Designer — sound effects and ambience
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "sound_designer"
            )
            t0 = _time.monotonic()
            self.sound_designer.validate_input(context)
            sd_output = self.sound_designer.process(context)
            context["sound_design"] = sd_output.content
            sd_review = self.sound_designer.review_output(sd_output)
            cost_info = self._estimate_cost(sd_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "sound_designer", "stage": "audio", "approved": sd_review.approved, "score": sd_review.score, **cost_info})
            self.tracker.record_cost(production_id, "audio", "sound_designer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("sound_designer", "audio", sd_review.score, duration)
            ep_memory.set_stage_data(StageType.AUDIO, {"sound_design": sd_output.content, "review": sd_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "sound_designer"
            )

            # Stage 14: Voice Director — voice performance direction
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "voice_director"
            )
            t0 = _time.monotonic()
            self.voice_director.validate_input(context)
            vd_output = self.voice_director.process(context)
            context["voice_direction"] = vd_output.content
            vd_review = self.voice_director.review_output(vd_output)
            cost_info = self._estimate_cost(vd_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "voice_director", "stage": "audio", "approved": vd_review.approved, "score": vd_review.score, **cost_info})
            self.tracker.record_cost(production_id, "audio", "voice_director", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("voice_director", "audio", vd_review.score, duration)
            ep_memory.set_stage_data(StageType.AUDIO, {"voice_direction": vd_output.content, "review": vd_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.AUDIO, "voice_director"
            )

            # Stage 15: Asset Generation — image asset descriptions from storyboard
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "asset_generation"
            )
            t0 = _time.monotonic()
            self.asset_generator.validate_input(context)
            asset_output = self.asset_generator.process(context)
            context["asset_descriptions"] = asset_output.content
            asset_review = self.asset_generator.review_output(asset_output)
            cost_info = self._estimate_cost(asset_output.content, context.get("storyboard", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "asset_generation", "stage": "asset_generation", "approved": asset_review.approved, "score": asset_review.score, **cost_info})
            self.tracker.record_cost(production_id, "asset_generation", "asset_generation", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("asset_generation", "asset_generation", asset_review.score, duration)
            ep_memory.set_stage_data(StageType.ASSET_GENERATION, {"asset_descriptions": asset_output.content, "review": asset_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ASSET_GENERATION, "asset_generation"
            )

            # Stage 16: Animation — scene motion descriptions
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ANIMATION, "animation"
            )
            t0 = _time.monotonic()
            self.animator.validate_input(context)
            anim_output = self.animator.process(context)
            context["animation"] = anim_output.content
            anim_review = self.animator.review_output(anim_output)
            cost_info = self._estimate_cost(anim_output.content, context.get("storyboard", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "animation", "stage": "animation", "approved": anim_review.approved, "score": anim_review.score, **cost_info})
            self.tracker.record_cost(production_id, "animation", "animation", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("animation", "animation", anim_review.score, duration)
            ep_memory.set_stage_data(StageType.ANIMATION, {"animation": anim_output.content, "review": anim_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ANIMATION, "animation"
            )

            # Stage 17: Rendering — final assembly and render plan
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.ANIMATION, "rendering"
            )
            t0 = _time.monotonic()
            self.renderer.validate_input(context)
            render_output = self.renderer.process(context)
            context["render_plan"] = render_output.content
            render_review = self.renderer.review_output(render_output)
            cost_info = self._estimate_cost(render_output.content, context.get("animation", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "rendering", "stage": "animation", "approved": render_review.approved, "score": render_review.score, **cost_info})
            self.tracker.record_cost(production_id, "animation", "rendering", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("rendering", "animation", render_review.score, duration)
            ep_memory.set_stage_data(StageType.ANIMATION, {"render_plan": render_output.content, "review": render_review})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.ANIMATION, "rendering"
            )

            # Stage 18: QA — final quality assurance review
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "qa"
            )
            t0 = _time.monotonic()
            self.qa.validate_input(context)
            qa_output = self.qa.process(context)
            context["qa_report"] = qa_output.content
            qa_review = self.qa.review_output(qa_output)
            cost_info = self._estimate_cost(qa_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "qa", "stage": "review", "approved": qa_review.approved, "score": qa_review.score, **cost_info})
            self.tracker.record_cost(production_id, "review", "qa", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("qa", "review", qa_review.score, duration)
            ep_memory.add_review({"reviewer": "qa", "report": qa_output.content, "approved": qa_review.approved, "score": qa_review.score})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "qa"
            )

            # Stage 19: Audience Simulation — projected viewer reactions
            stage_id = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "audience_simulation"
            )
            t0 = _time.monotonic()
            self.audience_sim.validate_input(context)
            audience_output = self.audience_sim.process(context)
            context["audience_report"] = audience_output.content
            audience_review = self.audience_sim.review_output(audience_output)
            cost_info = self._estimate_cost(audience_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "audience_simulation", "stage": "review", "approved": audience_review.approved, "score": audience_review.score, **cost_info})
            self.tracker.record_cost(production_id, "review", "audience_simulation", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("audience_simulation", "review", audience_review.score, duration)
            ep_memory.add_review({"reviewer": "audience_simulation", "report": audience_output.content, "approved": audience_review.approved, "score": audience_review.score})
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id, StageType.REVIEW, "audience_simulation"
            )

            # Stage 20: Voice Synthesis — gTTS dialogue audio
            stage_id_voice = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id_voice, StageType.AUDIO, "voice_synthesis"
            )
            t0 = _time.monotonic()
            self.voice_synth.validate_input(context)
            voice_output = self.voice_synth.process(context)
            voice_review = self.voice_synth.review_output(voice_output)
            cost_info = self._estimate_cost(voice_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "voice_synthesis", "stage": "audio", "approved": voice_review.approved, "score": voice_review.score, **cost_info})
            self.tracker.record_cost(production_id, "audio", "voice_synthesis", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("voice_synthesis", "audio", voice_review.score, duration)
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id_voice, StageType.AUDIO, "voice_synthesis"
            )

            # Stage 21: Frame Renderer — deterministic SVG frames
            stage_id_frames = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id_frames, StageType.RENDER, "frame_renderer"
            )
            t0 = _time.monotonic()
            self.frame_renderer.validate_input(context)
            frame_output = self.frame_renderer.process(context)
            context["frame_svgs"] = frame_output.content
            frame_review = self.frame_renderer.review_output(frame_output)
            cost_info = self._estimate_cost(frame_output.content, context.get("animation", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "frame_renderer", "stage": "render", "approved": frame_review.approved, "score": frame_review.score, **cost_info})
            self.tracker.record_cost(production_id, "render", "frame_renderer", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("frame_renderer", "render", frame_review.score, duration)
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id_frames, StageType.RENDER, "frame_renderer"
            )

            # Stage 22: Video Assembler — ImageMagick + FFmpeg
            stage_id_video = uuid4()
            await self.orchestrator.start_stage(
                production_id, episode_id, stage_id_video, StageType.RENDER, "video_assembler"
            )
            t0 = _time.monotonic()
            self.video_assembler.validate_input(context)
            video_output = self.video_assembler.process(context)
            if not context.get("video_url"):
                logger.warning(f"Video assembly failed: {video_output.content[:200]}")
            video_review = self.video_assembler.review_output(video_output)
            cost_info = self._estimate_cost(video_output.content, context.get("script", ""))
            duration = _time.monotonic() - t0
            prod_memory.add_agent_execution({"agent_role": "video_assembler", "stage": "render", "approved": video_review.approved, "score": video_review.score, **cost_info})
            self.tracker.record_cost(production_id, "render", "video_assembler", cost_info["input_tokens"], cost_info["output_tokens"], cost_info["cost_usd"])
            self.tracker.record_agent_performance("video_assembler", "render", video_review.score, duration)
            await self.orchestrator.complete_stage(
                production_id, episode_id, stage_id_video, StageType.RENDER, "video_assembler"
            )

            prod_memory.status = "completed"
            await self.orchestrator.complete_production(production_id, output)

            try:
                await prod_memory.persist_to_db()
                await ep_memory.persist_to_db(production_id)
            except Exception:
                pass

            cost = prod_memory.calculate_total_cost()
            result = PipelineResult(
                production_id=str(production_id),
                script=context["script"],
                canon_report=context["canon_report"],
                critique=context["critique"],
                budget_report=context.get("budget_report", ""),
                visual_style=context.get("visual_style", ""),
                visual_direction=context.get("visual_direction", ""),
                character_designs=context.get("character_designs", ""),
                environment_designs=context.get("environment_designs", ""),
                storyboard=context.get("storyboard", ""),
                musical_score=context.get("musical_score", ""),
                sound_design=context.get("sound_design", ""),
                voice_direction=context.get("voice_direction", ""),
                asset_descriptions=context.get("asset_descriptions", ""),
                animation=context.get("animation", ""),
                render_plan=context.get("render_plan", ""),
                qa_report=context.get("qa_report", ""),
                audience_report=context.get("audience_report", ""),
                dialogue_audio_urls=context.get("dialogue_audio_urls"),
                frame_paths=context.get("frame_paths"),
                video_url=context.get("video_url", ""),
                stage_outputs={
                    "creative_direction": context["creative_direction"],
                    "script_draft": context["script_draft"],
                    "total_cost_usd": cost,
                    "episodes": prod_memory.get_all_episodes(),
                },
            )
            if use_cache:
                self.cache.set(prompt, bible, mode, {
                    "production_id": result.production_id,
                    "script": result.script,
                    "canon_report": result.canon_report,
                    "critique": result.critique,
                    "musical_score": result.musical_score,
                    "sound_design": result.sound_design,
                    "voice_direction": result.voice_direction,
                    "asset_descriptions": result.asset_descriptions,
                    "animation": result.animation,
                    "render_plan": result.render_plan,
                    "qa_report": result.qa_report,
                    "audience_report": result.audience_report,
                    "dialogue_audio_urls": result.dialogue_audio_urls,
                    "frame_paths": result.frame_paths,
                    "video_url": result.video_url,
                    "stage_outputs": result.stage_outputs,
                })
            return result

        except Exception:
            prod_memory.status = "failed"
            await self.orchestrator.fail_production(
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                error_stage="pipeline",
                error_agent="pipeline_runner",
                error_message="Pipeline execution failed",
                recoverable=False,
            )
            raise
