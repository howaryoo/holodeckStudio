# Data Model: Holodeck Studio

**Feature**: 001-holodeck-studio
**Date**: 2026-06-07

## Entity Overview

```text
Production 1───* Episode 1───* Stage
    │                │            │
    │                │            └──* Asset
    │                │
    │                └──* Review
    │
    ├──1 FranchiseBible 1───* BibleEntry
    │
    ├──* AgentExecution (trace records)
    │
    └──1 ProductionConfig
```

## Entities

### Production

Represents a complete production run from theme prompt to final output.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Unique production identifier |
| theme_prompt | Text | NOT NULL, min 20 chars | Original user-provided theme prompt |
| status | Enum | NOT NULL, default 'pending' | pending, running, paused, completed, failed |
| mode | Enum | NOT NULL, default 'autonomous' | autonomous, supervised |
| created_at | Timestamp | NOT NULL, default now | Creation timestamp |
| updated_at | Timestamp | NOT NULL, auto-update | Last modification timestamp |
| completed_at | Timestamp | nullable | Completion timestamp |
| config_id | UUID | FK → ProductionConfig | Configuration for this production |

### ProductionConfig

Configurable parameters for a production run.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Config identifier |
| max_feedback_iterations | Integer | NOT NULL, default 3 | Max revision loops per stage |
| conflict_escalation_threshold | Integer | NOT NULL, default 3 | Unresolved conflicts before human escalation |
| quality_gate_threshold | Integer | NOT NULL, default 70 | Minimum quality score (0-100) to pass a stage |
| human_approval_timeout_seconds | Integer | NOT NULL, default 3600 | Timeout before auto-escalation in supervised mode |
| model_overrides | JSONB | nullable | Per-agent model provider overrides |

### FranchiseBible

The authoritative long-term memory for franchise lore.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Bible identifier |
| name | Text | NOT NULL, unique | Franchise name |
| description | Text | nullable | Franchise description |
| created_at | Timestamp | NOT NULL, default now | Creation timestamp |
| updated_at | Timestamp | NOT NULL, auto-update | Last modification timestamp |

### BibleEntry

A single entry in the franchise bible (character, location, technology, lore).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Entry identifier |
| bible_id | UUID | FK → FranchiseBible, NOT NULL | Parent bible |
| category | Enum | NOT NULL | character, location, technology, lore, event |
| name | Text | NOT NULL | Entry name |
| content | Text | NOT NULL | Full entry content |
| embedding | Vector(1536) | nullable | Semantic embedding for similarity search |
| metadata | JSONB | nullable | Structured attributes (e.g., character traits, location properties) |
| created_at | Timestamp | NOT NULL, default now | Creation timestamp |
| updated_at | Timestamp | NOT NULL, auto-update | Last modification timestamp |

### Episode

A single episode within a production.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Episode identifier |
| production_id | UUID | FK → Production, NOT NULL | Parent production |
| episode_number | Integer | NOT NULL | Episode sequence number |
| title | Text | nullable | Episode title |
| status | Enum | NOT NULL, default 'concept' | concept, outline, script, storyboard, asset_generation, audio, animation, review, release |
| current_stage | Enum | NOT NULL, default 'concept' | Current production stage |
| feedback_iterations | Integer | NOT NULL, default 0 | Revision count for current stage |
| created_at | Timestamp | NOT NULL, default now | Creation timestamp |
| updated_at | Timestamp | NOT NULL, auto-update | Last modification timestamp |

### Stage

A discrete production phase within an episode.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Stage identifier |
| episode_id | UUID | FK → Episode, NOT NULL | Parent episode |
| stage_type | Enum | NOT NULL | concept, outline, script, storyboard, asset_generation, audio, animation, review, release |
| status | Enum | NOT NULL, default 'pending' | pending, in_progress, awaiting_approval, approved, rejected, failed |
| input_data | JSONB | nullable | Stage input (references to upstream assets) |
| output_data | JSONB | nullable | Stage output summary |
| started_at | Timestamp | nullable | Stage start timestamp |
| completed_at | Timestamp | nullable | Stage completion timestamp |
| iteration_count | Integer | NOT NULL, default 0 | Number of revision cycles |
| max_iterations | Integer | NOT NULL, default 3 | Max revisions allowed (from config) |

### Asset

Any produced artifact in the production pipeline.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Asset identifier |
| episode_id | UUID | FK → Episode, NOT NULL | Parent episode |
| stage_id | UUID | FK → Stage, NOT NULL | Producing stage |
| asset_type | Enum | NOT NULL | script, storyboard, character_sheet, environment_design, music, sound_effect, voice_performance, animation_frame, rendered_video, review_report |
| name | Text | NOT NULL | Asset name/description |
| storage_path | Text | NOT NULL | Object storage key (bucket/key) |
| mime_type | Text | NOT NULL | MIME type of the asset |
| metadata | JSONB | nullable | Generation parameters, model used, review scores |
| created_at | Timestamp | NOT NULL, default now | Creation timestamp |

### Review

Quality assessment from the Review Department.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Review identifier |
| episode_id | UUID | FK → Episode, NOT NULL | Parent episode |
| stage_id | UUID | FK → Stage, NOT NULL | Stage being reviewed |
| reviewer_type | Enum | NOT NULL | critic, audience_simulation, qa |
| narrative_score | Integer | nullable, 0-100 | Narrative quality score |
| consistency_score | Integer | nullable, 0-100 | Canon consistency score |
| pacing_score | Integer | nullable, 0-100 | Pacing assessment score |
| overall_score | Integer | nullable, 0-100 | Weighted overall score |
| content | Text | nullable | Full review text |
| metadata | JSONB | nullable | Structured review details (audience reactions, specific issues) |
| created_at | Timestamp | NOT NULL, default now | Review timestamp |

### ApprovalCheckpoint

Decision gate for human or automated review.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Checkpoint identifier |
| stage_id | UUID | FK → Stage, NOT NULL | Stage being approved |
| checkpoint_type | Enum | NOT NULL | story, script, visual, final_release |
| status | Enum | NOT NULL, default 'pending' | pending, approved, rejected, escalated, timed_out |
| reviewer | Text | nullable | Human reviewer ID or 'auto' |
| feedback | Text | nullable | Approval or rejection feedback |
| created_at | Timestamp | NOT NULL, default now | Checkpoint creation timestamp |
| resolved_at | Timestamp | nullable | Resolution timestamp |
| timeout_at | Timestamp | nullable | Auto-escalation deadline |

### AgentExecution

Trace record for observability (Langfuse integration).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Execution identifier |
| production_id | UUID | FK → Production, NOT NULL | Parent production |
| episode_id | UUID | FK → Episode, nullable | Parent episode |
| stage_id | UUID | FK → Stage, nullable | Parent stage |
| agent_role | Enum | NOT NULL | showrunner, producer, head_writer, staff_writer, canon_historian, production_designer, character_designer, environment_designer, director, storyboard, composer, sound_designer, voice_director, asset_generation, animation, rendering, critic, audience_simulation, qa |
| langfuse_trace_id | Text | nullable | Langfuse trace correlation ID |
| model_provider | Text | nullable | Model provider used (Agno-abstracted) |
| model_id | Text | nullable | Specific model identifier |
| input_tokens | Integer | nullable | Token count input |
| output_tokens | Integer | nullable | Token count output |
| cost_usd | Decimal | nullable | Estimated cost in USD |
| status | Enum | NOT NULL, default 'running' | running, completed, failed |
| started_at | Timestamp | NOT NULL | Execution start |
| completed_at | Timestamp | nullable | Execution end |

## Enum Definitions

### ProductionStatus
`pending | running | paused | completed | failed`

### ProductionMode
`autonomous | supervised`

### BibleEntryCategory
`character | location | technology | lore | event`

### StageType
`concept | outline | script | storyboard | asset_generation | audio | animation | review | release`

### StageStatus
`pending | in_progress | awaiting_approval | approved | rejected | failed`

### AssetType
`script | storyboard | character_sheet | environment_design | music | sound_effect | voice_performance | animation_frame | rendered_video | review_report`

### ReviewerType
`critic | audience_simulation | qa`

### CheckpointType
`story | script | visual | final_release`

### CheckpointStatus
`pending | approved | rejected | escalated | timed_out`

### AgentRole
`showrunner | producer | head_writer | staff_writer | canon_historian | production_designer | character_designer | environment_designer | director | storyboard | composer | sound_designer | voice_director | asset_generation | animation | rendering | critic | audience_simulation | qa`

## State Transitions

### Episode Status Flow

```text
concept → outline → script → storyboard → asset_generation → audio → animation → review → release
                    ↑              │             │            │          │         │
                    └──────────────┘─────────────┘────────────┘──────────┘─────────┘
                                       (revision loops, max_iterations from config)
```

### Stage Status Flow

```text
pending → in_progress → awaiting_approval → approved → (next stage)
                │                │
                │                └── rejected → in_progress (revision)
                │
                └── failed (unrecoverable error)
```

### Approval Checkpoint Flow

```text
pending → approved (proceed to next stage)
       → rejected (feedback to agents, revision)
       → escalated (conflict threshold exceeded, human intervention)
       → timed_out (supervised mode timeout, auto-escalate or continue autonomous)
```

## Validation Rules

- BibleEntry.embedding MUST be generated from content using the configured embedding model
- Episode.feedback_iterations MUST NOT exceed Stage.max_iterations
- ApprovalCheckpoint.timeout_at MUST be set when Episode.mode is 'supervised'
- AgentExecution.cost_usd MUST be populated from Langfuse trace data
- Stage iteration_count MUST increment on each revision cycle
- Episode.current_stage MUST match the latest Stage.stage_type with status 'in_progress' or 'awaiting_approval'