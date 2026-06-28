from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://holodeck:holodeck@localhost:5432/holodeck",
        description="PostgreSQL connection string",
    )

    # Object Storage
    minio_endpoint: str = Field(
        default="localhost:9000", description="MinIO endpoint"
    )
    minio_access_key: str = Field(
        default="minioadmin", description="MinIO access key"
    )
    minio_secret_key: str = Field(
        default="minioadmin", description="MinIO secret key"
    )
    minio_bucket: str = Field(
        default="holodeck-assets", description="MinIO bucket name"
    )
    minio_secure: bool = Field(
        default=False, description="Use HTTPS for MinIO"
    )

    # Langfuse
    langfuse_public_key: str = Field(
        default="", description="Langfuse public key"
    )
    langfuse_secret_key: str = Field(
        default="", description="Langfuse secret key"
    )
    langfuse_host: str = Field(
        default="http://localhost:3000", description="Langfuse host URL"
    )

    # Model Providers
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_base_url: str = Field(
        default="",
        description="OpenAI-compatible base URL (e.g. LiteLLM proxy)",
    )
    anthropic_api_key: str = Field(
        default="", description="Anthropic API key"
    )
    google_api_key: str = Field(
        default="", description="Google Gemini API key"
    )

    # Default model for all agents
    # Format: "provider/model_id"
    # Examples: "openai/gpt-5.4-mini",
    #   "google/gemini-2.5-flash",
    #   "anthropic/claude-sonnet-4-5-20250929"
    holodeck_default_model: str = Field(
        default="openai/gpt-5.4-mini",
        description='Default model (format: "provider/model_id")',
    )

    # Per-agent model overrides (same format as holodeck_default_model)
    holodeck_model_showrunner: str = Field(
        default="", description="Model override for Showrunner agent"
    )
    holodeck_model_head_writer: str = Field(
        default="", description="Model override for Head Writer agent"
    )
    holodeck_model_staff_writer: str = Field(
        default="", description="Model override for Staff Writer agent"
    )
    holodeck_model_canon_historian: str = Field(
        default="", description="Model override for Canon Historian agent"
    )
    holodeck_model_critic: str = Field(
        default="", description="Model override for Critic agent"
    )
    holodeck_model_evaluator: str = Field(
        default="", description="Model override for Judge/Evaluator agent"
    )

    # Application
    holodeck_default_mode: str = Field(
        default="autonomous", description="Default production mode"
    )
    holodeck_max_feedback_iterations: int = Field(
        default=3,
        description="Max feedback loop iterations per stage",
    )
    holodeck_quality_gate_threshold: int = Field(
        default=70,
        description="Minimum quality score (0-100) to pass a stage",
    )
    holodeck_conflict_escalation_threshold: int = Field(
        default=3,
        description="Unresolved conflicts before human escalation",
    )
    holodeck_human_approval_timeout_seconds: int = Field(
        default=3600,
        description="Timeout before auto-escalation in supervised mode",
    )

    # ElevenLabs Voice Cloning
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key")
    elevenlabs_voice_model: str = Field(
        default="eleven_monolingual_v1",
        description="ElevenLabs TTS model identifier",
    )
    elevenlabs_voice_stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability [0.0–1.0]; higher = more consistent delivery",
    )
    elevenlabs_similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity to original voice [0.0–1.0]; higher = closer clone",
    )
    elevenlabs_use_speaker_boost: bool = Field(
        default=False,
        description="Enable ElevenLabs speaker boost for audio quality enhancement",
    )

    # Image Generation
    image_provider: str = Field(
        default="svgonly",
        description="Image provider: replicate, stability, huggingface, svgonly",
    )
    replicate_api_key: str = Field(
        default="", description="Replicate API token"
    )
    replicate_model: str = Field(
        default="black-forest-labs/flux-2-pro",
        description="Replicate model ID",
    )
    image_gen_width: int = Field(
        default=1280, ge=256, le=2048, description="Generated image width",
    )
    image_gen_height: int = Field(
        default=720, ge=256, le=2048, description="Generated image height",
    )
    image_gen_style: str = Field(
        default="illustrated",
        description="Style prompt: illustrated, cinematic, photorealistic, animated",
    )
    ai_budget_limit: int = Field(
        default=25, ge=0,
        description="Max AI API calls per production run (0 = unlimited)",
    )

    def get_model_for_agent(self, agent_name: str) -> str:
        override = getattr(self, f"holodeck_model_{agent_name}", "")
        return override if override else self.holodeck_default_model

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
