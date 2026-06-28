# Tasks: Holodeck Studio

**Input**: Design documents from `/specs/001-holodeck-studio/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested in the feature specification. Test tasks are generated only where required to validate acceptance criteria.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [SYNC/ASYNC] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[SYNC]**: Requires human review (complex logic, architecture decisions, security-critical)
- **[ASYNC]**: Can be delegated to async agents (well-defined, clear specs)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Path Conventions

- Single project: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [ASYNC] Create project structure per implementation plan: src/holodeck/ with cli/, agents/, pipeline/, memory/, storage/, observability/, config/ subdirectories and tests/ with contract/, integration/, unit/ subdirectories
- [x] T002 [ASYNC] Initialize Python project with pyproject.toml including dependencies: agno, langfuse, typer, sqlalchemy, asyncpg, pgvector, pydantic, minio, ruff, mypy, pytest, pytest-asyncio, pytest-cov
- [x] T003 [P] [ASYNC] Create Docker Compose configuration in docker-compose.yml for PostgreSQL (with pgvector), MinIO, and Langfuse services
- [x] T004 [P] [ASYNC] Create environment configuration template in .env.example with all required environment variables from quickstart.md
- [x] T005 [P] [ASYNC] Create Alembic configuration and initial migration setup in alembic/ and alembic.ini

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 [SYNC] Define HolodeckAgentProtocol in src/holodeck/agents/base.py with stage property, validate_input(), process(), and review_output() methods using Python Protocol class per Dependency Inversion principle
- [x] T007 [SYNC] Define Stage enum and transition rules in src/holodeck/pipeline/stages.py implementing the state machine: concept → outline → script → storyboard → asset_generation → audio → animation → review → release with revision loop transitions per data-model.md
- [x] T008 [SYNC] Define event types in src/holodeck/pipeline/events.py implementing all Pydantic event models from contracts/events.md (BaseEvent, ProductionStarted, StageCompleted, RevisionRequested, ConflictDetected, PromptRejected, etc.)
- [x] T009 [SYNC] Define EventBus protocol and AsyncioEventBus implementation in src/holodeck/pipeline/events.py with publish() and subscribe() async methods per Interface Segregation principle
- [x] T010 [P] [ASYNC] Create SQLAlchemy models in src/holodeck/storage/postgres.py for all entities from data-model.md: Production, ProductionConfig, FranchiseBible, BibleEntry, Episode, Stage, Asset, Review, ApprovalCheckpoint, AgentExecution with all fields, constraints, and enums
- [x] T011 [P] [ASYNC] Create ObjectStore protocol and MinIO implementation in src/holodeck/storage/object_store.py with put(), get(), list(), and delete() async methods per Dependency Inversion principle
- [x] T012 [SYNC] Create Pydantic settings module in src/holodeck/config/settings.py with ProductionConfig settings: max_feedback_iterations, conflict_escalation_threshold, quality_gate_threshold, human_approval_timeout_seconds, model_overrides, environment variable overrides
- [x] T013 [SYNC] Create Langfuse tracing setup in src/holodeck/observability/tracing.py with OpenTelemetry + AgnoInstrumentor integration per research.md: trace hierarchy (Production → Stage → Agent → Tool), session ID to trace ID mapping, cost tracking
- [x] T014 [ASYNC] Create Alembic initial migration for all database tables from data-model.md with pgvector extension and all indexes

**Checkpoint**: Foundation ready — protocol, events, storage, settings, and observability are in place

---

## Phase 3: User Story 1 - Autonomous Episode Production (Priority: P1) 🎯 MVP

**Goal**: User submits a theme prompt via CLI and the system produces a complete, coherent script through its multi-agent pipeline

**Independent Test**: Provide a theme prompt via CLI and verify the system produces a coherent multi-scene script with consistent characters, reviewed by Canon Historian and Critic agents

### Implementation for User Story 1

- [x] T015 [SYNC] [US1] Implement CLI entry point and produce command in src/holodeck/cli/main.py using Typer: holodeck produce with prompt validation (min 20 chars, genre/theme/character specificity check), mode selection (autonomous/supervised), and bible/config options per contracts/cli-commands.md
- [x] T016 [SYNC] [US1] Implement prompt validation logic in src/holodeck/cli/main.py: reject vague prompts (FR-001) with guidance on required specificity (genre, themes, characters, story direction), return exit code 1 with descriptive error
- [x] T017 [P] [SYNC] [US1] Implement Showrunner agent in src/holodeck/agents/showrunner.py extending Agent with HolodeckAgentProtocol: creative authority over production, auto-resolve agent conflicts with logged rationale (FR-014), escalate to human when conflict threshold exceeded, manage production state transitions
- [x] T018 [P] [SYNC] [US1] Implement Canon Historian agent in src/holodeck/agents/writers/canon_historian.py extending Agent with HolodeckAgentProtocol: validate continuity against franchise bible (FR-004), detect contradictions with ≥90% accuracy (SC-002), recency-weighted resolution for conflicting bible entries, flag contradictions for human review
- [x] T019 [P] [SYNC] [US1] Implement Head Writer agent in src/holodeck/agents/writers/head_writer.py extending Agent with HolodeckAgentProtocol: generate season arcs and episode concepts, approve and revise script drafts for narrative quality, pacing, and thematic alignment
- [x] T020 [P] [ASYNC] [US1] Implement Staff Writer agent in src/holodeck/agents/writers/staff_writer.py extending Agent with HolodeckAgentProtocol: draft scenes and dialogue, propose story ideas, receive revision feedback from Head Writer
- [x] T021 [P] [ASYNC] [US1] Implement Critic agent in src/holodeck/agents/review/critic.py extending Agent with HolodeckAgentProtocol: narrative critique, structural assessment, review scoring (narrative_score, consistency_score, pacing_score, overall_score)
- [x] T022 [SYNC] [US1] Implement franchise bible module in src/holodeck/memory/franchise_bible.py: PostgreSQL storage with pgvector semantic search, BibleEntry CRUD operations, embedding generation, similarity search for canon verification, recency-weighted conflict resolution
- [x] T023 [SYNC] [US1] Implement episode memory module in src/holodeck/memory/episode.py: track current episode state across stages, store script drafts and revisions, manage feedback iteration counts with configurable max per stage (default 3)
- [x] T024 [SYNC] [US1] Implement pipeline orchestrator in src/holodeck/pipeline/orchestrator.py: coordinate agent execution through stage-gate workflow (concept → outline → script → review), manage feedback loops with iteration counting, emit events for each stage transition, handle Showrunner conflict resolution and escalation
- [x] T025 [SYNC] [US1] Implement production memory module in src/holodeck/memory/production.py: track production state across all stages, persist Production and Episode records, recover full state from database after interruption (SC-004), link AgentExecution trace records
- [x] T026 [ASYNC] [US1] Implement CLI status command in src/holodeck/cli/main.py: holodeck status with production progress, current stage, agent execution details, cost summary, and --json output per contracts/cli-commands.md
- [x] T027 [ASYNC] [US1] Implement CLI bible commands in src/holodeck/cli/main.py: holodeck bible list/show/create/add-entry/search per contracts/cli-commands.md with Typer subcommands
- [x] T028 [ASYNC] [US1] Implement CLI config command in src/holodeck/cli/main.py: holodeck config show/set/reset per contracts/cli-commands.md with Pydantic settings integration
- [x] T029 [SYNC] [US1] Implement LLM invocation in all 5 agent process() methods: call _get_agent().run() with stage-appropriate prompts (theme prompt for Showrunner, creative direction for HeadWriter, script draft for StaffWriter, script+bible for CanonHistorian, script for Critic) to generate real content instead of template strings; preserve @observe decorators for Langfuse tracing
- [x] T030 [SYNC] [US1] Implement ProductionPipeline runner in src/holodeck/pipeline/runner.py: sequence agents (Showrunner → HeadWriter → StaffWriter → CanonHistorian → Critic), pass context between stages, invoke orchestrator StageStarted/StageCompleted events, collect and return PipelineResult with script, canon_report, and critique
- [x] T031 [SYNC] [US1] Wire CLI produce command to ProductionPipeline: instantiate pipeline from command handler, call pipeline.run() via asyncio.run(), display script output and review reports via Rich console, handle errors with exit code 1
- [x] T032 [SYNC] [US1] Wire CLI bible commands to FranchiseBible in-memory store: implement bible create/show/list/add-entry/search to call FranchiseBible methods, return bible UUID on create, display entries on show/show, handle errors with exit code 1
- [x] T033 [SYNC] [US1] Wire pipeline runner to load bible entries into CanonHistorian context: lookup bible_id via FranchiseBible.get_entries() before Stage 4, pass loaded entries as bible_entries context key, handle missing bible gracefully with warning
- [x] T034 [SYNC] [US1] Wire pipeline runner to ProductionMemory/EpisodeMemory for state persistence: create ProductionMemory on pipeline start, update status/stage data as pipeline progresses, persist agent execution records, link to orchestrator events
- [x] T035 [SYNC] [US1] Implement LLM invocation in all 5 agent review_output() methods: call _get_agent().run() with review prompts (content quality check, canon consistency assessment, narrative critique scoring), extract structured scores from response, return accurate ReviewResult instead of hardcoded values
- [x] T036 [ASYNC] [US1] Wire CLI status command to ProductionMemory: read production state, current stage, agent execution history, and cost summary from ProductionMemory; display formatted table via Rich with --json flag for machine output
- [x] T037 [ASYNC] [US1] Wire CLI config set/reset to persist settings: save/load settings to JSON file at ~/.holodeck/config.json, merge with env vars, display updated configuration after set/reset

**Checkpoint**: User Story 1 is fully functional — user can submit a theme prompt via CLI and receive a script through the multi-agent pipeline with canon verification

---

## Phase 4: User Story 2 - Storyboard & Visual Design (Priority: P2)

**Goal**: System generates storyboards, character sheets, and environment designs from approved scripts

**Independent Test**: Feed an approved script and verify storyboards, character sheets, and environment designs are produced with visual consistency

### Implementation for User Story 2

- [x] T038 [SYNC] [US2] Implement Director agent in src/holodeck/agents/directing/director.py extending Agent with HolodeckAgentProtocol: scene composition, camera planning, emotional pacing, translate script scene descriptions into visual direction
- [x] T039 [P] [ASYNC] [US2] Implement Storyboard agent in src/holodeck/agents/directing/storyboard.py extending Agent with HolodeckAgentProtocol: create shot plans from Director's visual direction, generate storyboard frame descriptions
- [x] T040 [P] [SYNC] [US2] Implement Production Designer agent in src/holodeck/agents/design/production_designer.py extending Agent with HolodeckAgentProtocol: define visual style, coordinate artistic consistency across all visual outputs
- [x] T041 [P] [ASYNC] [US2] Implement Character Designer agent in src/holodeck/agents/design/character_designer.py extending Agent with HolodeckAgentProtocol: generate character sheets with appearance, costumes, expression ranges consistent with established visual style
- [x] T042 [P] [ASYNC] [US2] Implement Environment Designer agent in src/holodeck/agents/design/environment_designer.py extending Agent with HolodeckAgentProtocol: generate location designs, architectural concept art matching story setting and tone
- [x] T043 [SYNC] [US2] Extend pipeline orchestrator in src/holodeck/pipeline/orchestrator.py to add storyboard, asset_generation, and visual review stages after script approval, with visual approval checkpoint

**Checkpoint**: User Stories 1 AND 2 both work independently — script + visual design pipeline

**Checkpoint**: User Stories 1 AND 2 both work independently — script + visual design pipeline

---

## Phase 5: User Story 3 - Audio Production (Priority: P3)

**Goal**: System generates musical scores, sound effects, and voice performances aligned with emotional requirements

**Independent Test**: Provide an approved script with storyboards and verify a complete audio package matching emotional tone and pacing

### Implementation for User Story 3

- [x] T044 [SYNC] [US3] Implement Composer agent in src/holodeck/agents/audio/composer.py extending Agent with HolodeckAgentProtocol: create musical themes and background scores matching emotional arc markers from scripts
- [x] T045 [P] [ASYNC] [US3] Implement Sound Designer agent in src/holodeck/agents/audio/sound_designer.py extending Agent with HolodeckAgentProtocol: generate sound effects and atmospheric audio from scene descriptions
- [x] T046 [P] [ASYNC] [US3] Implement Voice Director agent in src/holodeck/agents/audio/voice_director.py extending Agent with HolodeckAgentProtocol: cast and direct voice performances with consistent character voices and emotional delivery
- [x] T047 [SYNC] [US3] Extend pipeline orchestator in src/holodeck/pipeline/runner.py to add audio stages (Composer → Sound Designer → Voice Director) after storyboard/visual stages, with audio-specific review, PipelineResult fields, and CLI display

**Checkpoint**: User Stories 1, 2, AND 3 all work independently — script + visual + audio pipeline

**Checkpoint**: User Stories 1, 2, AND 3 all work independently — script + visual + audio pipeline

---

## Phase 6: User Story 4 - Animation & Full Episode Rendering (Priority: P4)

**Goal**: System animates scenes and renders final video episodes

**Independent Test**: Provide approved storyboards, assets, and audio; verify rendered video output

### Implementation for User Story 4

- [x] T048 [P] [ASYNC] [US4] Implement Asset Generation agent in src/holodeck/agents/production/asset_generation.py extending Agent with HolodeckAgentProtocol: generate image assets, character art, background art from storyboard descriptions
- [x] T049 [P] [ASYNC] [US4] Implement Animation agent in src/holodeck/agents/production/animation.py extending Agent with HolodeckAgentProtocol: create scene animations from storyboards and visual direction with motion planning
- [x] T050 [P] [ASYNC] [US4] Implement Rendering agent in src/holodeck/agents/production/rendering.py extending Agent with HolodeckAgentProtocol: assemble animated scenes with synchronized audio into final video output
- [x] T051 [SYNC] [US4] Implement QA agent in src/holodeck/agents/review/qa.py extending Agent with HolodeckAgentProtocol: detect continuity issues, visual inconsistencies, and pacing problems; produce review reports with scoring per data-model.md Review entity
- [x] T052 [SYNC] [US4] Extend pipeline runner in src/holodeck/pipeline/runner.py to add asset generation, animation, rendering, and QA review stages after audio, with PipelineResult fields and CLI display

**Checkpoint**: All user stories 1-4 work independently — full production pipeline operational

**Checkpoint**: All user stories 1-4 work independently — full production pipeline operational

---

## Phase 7: User Story 5 - Human-in-the-Loop Review & Approval (Priority: P5)

**Goal**: Human producer reviews and approves/rejects at checkpoints in supervised mode; autonomous mode auto-approves with quality gates

**Independent Test**: Run pipeline in supervised mode; verify system pauses at checkpoints, accepts approval/rejection CLI commands, and routes feedback

### Implementation for User Story 5

- [x] T053 [SYNC] [US5] Implement ApprovalCheckpoint model and workflow in src/holodeck/pipeline/orchestrator.py: pause pipeline at story/script/visual/final_release checkpoints in supervised mode, auto-approve based on quality_gate_threshold in autonomous mode, configurable timeout with escalation per data-model.md ApprovalCheckpoint entity; wired into pipeline runner as event emission
- [x] T054 [SYNC] [US5] Implement CLI approve command in src/holodeck/cli/main.py: holodeck approve with --stage, --episode, --note options per contracts/cli-commands.md, resolve ApprovalCheckpoint in database
- [x] T055 [SYNC] [US5] Implement CLI reject command in src/holodeck/cli/main.py: holodeck reject with --stage, --episode, --feedback options per contracts/cli-commands.md, trigger revision loop with feedback routing to relevant agents
- [x] T056 [ASYNC] [US5] Implement CLI pause/resume commands in src/holodeck/cli/main.py: holodeck pause and holodeck resume per contracts/cli-commands.md, set Production status to paused/running
- [x] T057 [SYNC] [US5] Implement audience simulation agent in src/holodeck/agents/review/audience_simulation.py extending Agent with HolodeckAgentProtocol: simulate reactions of science-fiction fans, casual viewers, critics, and franchise fans; produce audience simulation review scores per data-model.md Review entity; wired into pipeline runner as Stage 19

**Checkpoint**: All 5 user stories fully functional — complete production pipeline with human-in-the-loop approval (pipeline emits checkpoint events; CLI approve/reject/pause/resume commands update ProductionMemory; full async pause/resume is a future enhancement)

---

## Phase 8: Producer Agent & Cross-Cutting Concerns

**Purpose**: Producer agent for budget/cost tracking, observability integration, and production-level features

- [x] T058 [SYNC] Implement Producer agent in src/holodeck/agents/producer.py extending Agent with HolodeckAgentProtocol: estimate resource costs per stage, enforce budget constraints (FR-013), pause production when budget exceeded with cost options
- [x] T059 [SYNC] Implement evaluation module in src/holodeck/observability/evaluation.py: prompt version management via Langfuse, cost tracking per production stage, agent performance metrics collection, trace correlation across agent runs
- [x] T060 [ASYNC] Implement CLI review command in src/holodeck/cli/main.py: holodeck review with --episode, --type, --verbose, --json options per contracts/cli-commands.md, display review reports from Critic, AudienceSimulation, QA agents
- [x] T061 [ASYNC] Implement RedisEventBus in src/holodeck/pipeline/events.py: multi-process event bus using Redis Streams for cloud deployment, implementing EventBus protocol from Phase 2
- [x] T062 [ASYNC] Create unit tests for event models in tests/unit/pipeline/test_events.py validating all Pydantic event types, serialization/deserialization, and EventBus protocol contract
- [x] T063 [ASYNC] Create unit tests for stage transitions in tests/unit/pipeline/test_stages.py validating state machine: valid transitions, rejection loops, iteration counting, failure handling
- [x] T064 [ASYNC] Create unit tests for data models in tests/unit/test_models.py validating all SQLAlchemy models, constraints, enum values, and relationships
- [x] T065 [ASYNC] Create contract tests for CLI commands in tests/contract/test_cli_contract.py validating all command schemas, exit codes, and error handling per contracts/cli-commands.md
- [x] T066 [ASYNC] Create integration test for pipeline flow in tests/integration/test_pipeline_flow.py: end-to-end script generation flow from prompt to script output, stage transitions, event emission, and state persistence
- [x] T067 [SYNC] Create async SQLAlchemy session factory and CRUD repository classes in src/holodeck/storage/postgres.py: async_sessionmaker with ScopedSession for thread safety, repository classes per model (ProductionRepository, BibleRepository, EpisodeRepository, StageRepository, ReviewRepository) with create/read/update/delete methods, context manager for transaction lifecycle
- [x] T068 [SYNC] Wire memory modules to DB repositories: replace in-memory dict storage in ProductionMemory, EpisodeMemory, and FranchiseBible with DB-backed CRUD via repositories; implement full state recovery from DB on startup (SC-004); add pgvector semantic search to FranchiseBible.search()

---

## Phase 9: Cost Optimization — LLM Cache Layer

**Purpose**: Cache pipeline results to avoid wasting tokens on repeated or similar prompts

- [x] T069 [ASYNC] Implement cache module in src/holodeck/cache.py: CacheBackend protocol (InMemoryBackend, FileBackend), generate_cache_key() with prompt normalization, PipelineCache class with get/set/clear methods, TTL support
- [x] T070 [ASYNC] Wire PipelineCache into ProductionPipeline runner: check cache before agent execution, store result on completion, use_cache parameter to bypass
- [x] T071 [ASYNC] Add CLI cache commands in src/holodeck/cli/main.py: holodeck cache clear, holodeck cache status, produce --no-cache flag
- [x] T072 [ASYNC] Add agent-level caching via cached_agent_run() utility in cache.py: cache per-agent LLM response keyed by role+prompt hash; integrated into Showrunner as pattern; bypass with use_cache context flag

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 Script Generation (Phase 3)**: Depends on Foundational
- **US2 Visual Design (Phase 4)**: Depends on US1 (needs script output as input)
- **US3 Audio (Phase 5)**: Depends on US1 (needs script); can run parallel with US2
- **US4 Animation (Phase 3)**: Depends on US2 and US3 (needs visuals and audio)
- **US5 Human-in-the-Loop (Phase 7)**: Depends on US1 at minimum; fully exercised with all stages
- **Polish (Phase 8)**: Depends on US1; enhances all stories

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P2)**: Depends on US1 (script output feeds storyboards)
- **US3 (P3)**: Depends on US1 (script feeds audio); independent of US2
- **US4 (P4)**: Depends on US2 and US3 (visuals + audio needed for render)
- **US5 (P5)**: Depends on US1 at minimum; cross-cutting approval workflow

### Within Each User Story

- Agent implementations [P] can run in parallel within each story
- Pipeline orchestrator extensions must wait for the agents they coordinate
- CLI commands depend on their underlying agent/infrastructure implementations
- Memory modules must complete before agents that use them

### Parallel Opportunities

- T003, T004, T005 can run in parallel (Phase 1)
- T010, T011 can run in parallel (Phase 2)
- T017, T018, T019 can run in parallel (US1 agents)
- T029, T030, T031, T032, T033, T034 sequential (US1 integration — each depends on prior)
- T035, T036, T037 sequential (US1 wiring — depends on T034)
- T039, T040, T041, T042 can run in parallel (US2 agents)
- T044, T045, T046 can run in parallel (US3 agents)
- T048, T049, T050 can run in parallel (US4 agents)
- T054, T055, T056 can run in parallel (US5 CLI commands)
- T062, T063, T064, T065 can run in parallel (tests)
- T067, T068 sequential (Phase 8 persistence — each depends on prior)

---

## Parallel Example: User Story 1

```text
# Launch scaffolding + Docker + Alembic in parallel:
Task T003: "Docker Compose configuration"
Task T004: "Environment configuration template"
Task T005: "Alembic setup"

# Launch core agents in parallel (after foundational):
Task T017: "Showrunner agent"
Task T018: "Canon Historian agent"
Task T019: "Head Writer agent"

# Then sequentially:
Task T020: "Staff Writer agent" (follows Head Writer pattern)
Task T021: "Critic agent" (follows agent protocol)
Task T024: "Pipeline orchestrator" (coordinates all agents)

# Integration (wires everything together):
Task T029: "LLM invocation in all agents" (calls _get_agent().run())
Task T030: "ProductionPipeline runner" (sequences agent calls)
Task T031: "Wire CLI to pipeline" (connects produce command)

# Persistence & wiring (completes US1):
Task T032: "Wire CLI bible to FranchiseBible"
Task T033: "Wire pipeline runner to bible entries"
Task T034: "Wire pipeline runner to ProductionMemory/EpisodeMemory"
Task T035: "LLM invocation in review_output()"
Task T036: "Wire CLI status to ProductionMemory"
Task T037: "Wire CLI config set/reset persistence"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Script generation pipeline)
4. **STOP and VALIDATE**: Test US1 independently via CLI
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → MVP demo!
3. Add US2 → Test independently → Visual design pipeline
4. Add US3 → Test independently → Audio pipeline
5. Add US4 → Test independently → Full production pipeline
6. Add US5 → Test independently → Human-in-the-loop approval
7. Polish → Producer agent, tests, observability

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD is not enforced; test tasks are included only for cross-cutting infrastructure validation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Agno-abstracted model providers mean each agent can use a different LLM without code changes
