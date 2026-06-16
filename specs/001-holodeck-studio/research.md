# Research: Holodeck Studio

**Feature**: 001-holodeck-studio
**Date**: 2026-06-07

## 1. Agno Multi-Agent Framework

### Decision: Use Agno as primary multi-agent framework

**Rationale**: Agno provides native support for agent teams with hierarchical delegation, deterministic workflow pipelines for stage-gate orchestration, and built-in session state for inter-agent context sharing. It directly supports the production pipeline pattern required by Holodeck Studio.

**Key Patterns for Holodeck Studio:**

| Pattern | Agno Construct | Usage |
|---------|---------------|-------|
| Stage-gate pipeline | `Workflow` with `Step` | Deterministic production stages (Concept → Script → Review → Release) |
| Hierarchical delegation | Nested `Team` with `TeamMode.coordinate` | Department heads coordinate specialists |
| Single-agent dispatch | `TeamMode.route` | Showrunner routes tasks to one specialist |
| Parallel review | `TeamMode.broadcast` | Critic + Audience Simulation + QA review simultaneously |
| Task decomposition | `TeamMode.tasks` | Showrunner breaks complex production goals into sub-tasks |
| Human-in-the-loop | `Agent.run()` → pause → `continue_run()` | Approval checkpoints at each stage |
| Per-agent model config | `model` on each `Agent` | Writer uses creative model, Canon Historian uses analytical model |

**Alternatives Considered:**
- **CrewAI**: Less mature workflow support; no native stage-gate pattern; weaker observability integration
- **AutoGen**: Research-oriented; no production-grade workflow routing; weaker tool ecosystem
- **LangChain agents**: Overly abstracted; poor fit for deterministic pipeline control

## 2. Langfuse Observability Integration

### Decision: Use OpenTelemetry + AgnoInstrumentor for Langfuse tracing

**Rationale**: OpenTelemetry is the production-standard approach supported by both Agno and Langfuse. It provides distributed tracing across all agent interactions, cost tracking per agent call, and evaluation scoring.

**Integration Architecture:**
- Each agent run emits spans to Langfuse via OTLP
- Trace hierarchy: Production → Stage → Agent → Tool call
- Session IDs map to Langfuse trace IDs for cross-agent correlation
- Prompt versions stored in Langfuse with automatic versioning
- Cost tracking uses Langfuse's native token counting per model

**Alternatives Considered:**
- **OpenLIT**: Simpler setup but less control over trace hierarchy; limited evaluation features
- **Direct Langfuse SDK**: More manual instrumentation; would violate DRY across 17 agents

## 3. Event-Driven Architecture

### Decision: Use asyncio queue-based event bus for local execution; pluggable message bus abstraction for cloud

**Rationale**: MVP runs locally in Docker containers where asyncio queues provide zero-dependency inter-process messaging within a single Python process. The message bus interface abstracts this so cloud deployments can swap in Redis Streams, RabbitMQ, or Kafka without changing agent code.

**Key Design:**
- `EventBus` protocol defines `publish()` and `subscribe()` methods
- `AsyncioEventBus` implementation for single-process local execution
- `RedisEventBus` implementation for multi-process cloud execution
- Events are typed Pydantic models (stage completion, revision request, approval, etc.)
- Agents subscribe to event types they care about; orchestrator subscribes to all for state tracking

**Alternatives Considered:**
- **Pure Celery**: Overkill for single-process MVP; adds Redis dependency even for development
- **ZeroMQ**: Low-level; would require building reliability features ourselves
- **No event bus (direct function calls)**: Violates Open/Closed principle; agents cannot be independently extended

## 4. PostgreSQL + pgvector for Franchise Bible

### Decision: Use PostgreSQL with pgvector extension for franchise bible semantic search

**Rationale**: The franchise bible requires both structured queries (find character by name) and semantic similarity search (find lore related to a narrative theme). pgvector provides vector similarity search within PostgreSQL, avoiding a separate vector database dependency. SQLAlchemy supports pgvector natively.

**Schema Design:**
- `franchise_bible` table: id, category (character/location/technology/lore), name, content, embedding, metadata JSONB
- `embed()` function generates embeddings via the model provider's embedding API
- Cosine similarity search for canon verification queries
- Full-text search via PostgreSQL tsvector for structured lookups

**Alternatives Considered:**
- **Pinecone/Weaviate**: Separate vector DB adds operational complexity; no need for separate service when PostgreSQL handles both structured and vector queries
- **ChromaDB**: Python-native but lacks production durability guarantees; not suitable for canonical data store
- **SQLite + faiss**: Insufficient for production workload; no concurrent access

## 5. Object Storage for Assets

### Decision: Use MinIO (S3-compatible) for local development; S3-compatible API for cloud

**Rationale**: MinIO provides an S3-compatible API that works identically in local Docker and cloud deployments. The `ObjectStore` protocol abstracts storage operations so agent code never references MinIO/S3 directly — it calls `store.put()`, `store.get()`, `store.list()`.

**Asset Organization:**
- Bucket per production: `production-{id}`
- Key hierarchy: `{episode_id}/{stage}/{asset_type}/{asset_id}.{ext}`
- Metadata (description, generation params, review status) in PostgreSQL; binary data in object storage

## 6. CLI Framework

### Decision: Use Typer for CLI interface

**Rationale**: Typer provides type-annotated CLI commands with automatic help generation, which aligns with the constitution's Python-first approach and type hint requirements. It builds on Click, is well-maintained, and produces clean CLI output.

**Key Commands:**
- `holodeck produce <prompt>` — start a production
- `holodeck status <production-id>` — check production status
- `holodeck approve <production-id> [--stage <stage>]` — approve a checkpoint
- `holodeck reject <production-id> --stage <stage> --feedback <text>` — reject and request revisions
- `holodeck review <production-id>` — view review reports
- `holodeck pause <production-id>` — pause a running production
- `holodeck config` — manage configuration (thresholds, model settings)

**Alternatives Considered:**
- **Click**: Lower-level; more boilerplate for type-annotated commands
- **Argparse**: Standard library but verbose; no automatic help from type hints
- **Rich CLI**: Adds presentation layer but not a CLI framework

## 7. Agent Base Architecture

### Decision: Use Agno Agent as the base with a HolodeckAgentProtocol for production-specific behavior

**Rationale**: Agno's Agent class provides model configuration, tools, memory, and instructions out of the box. We add a `HolodeckAgentProtocol` (Python Protocol class) that defines production-specific methods: `validate_input()`, `process()`, `review_output()`, `can_proceed()`. This satisfies Dependency Inversion (depend on Protocol, not implementation) and Interface Segregation (agents only implement methods they need).

**Key Design:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class HolodeckAgentProtocol(Protocol):
    @property
    def stage(self) -> Stage: ...
    def validate_input(self, context: ProductionContext) -> ValidationResult: ...
    def process(self, context: ProductionContext) -> AgentOutput: ...
    def review_output(self, output: AgentOutput) -> ReviewResult: ...
```

Each concrete agent extends `Agent` from Agno and implements `HolodeckAgentProtocol`. The pipeline orchestrator calls methods from the protocol, never the Agno Agent directly, ensuring substitutability (Liskov Substitution).

## 8. Configuration Management

### Decision: Use Pydantic BaseSettings with YAML/toml config files + environment variables

**Rationale**: Pydantic BaseSettings provides type-safe configuration with environment variable overrides, which is essential for Docker deployments. Config files define defaults; environment variables override for different environments.

**Key Configuration:**
- `max_feedback_iterations` per stage (default: 3)
- `conflict_escalation_threshold` for Showrunner (default: 3 unresolved conflicts)
- `quality_gate_threshold` per stage (0-100 scale)
- `human_approval_timeout_seconds` (default: 3600)
- Model provider per agent (Agno-abstracted)
- Langfuse credentials
- PostgreSQL and object storage connection strings