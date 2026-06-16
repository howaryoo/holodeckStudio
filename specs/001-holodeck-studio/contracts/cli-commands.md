# CLI Commands Contract: Holodeck Studio

**Feature**: 001-holodeck-studio
**Date**: 2026-06-07

This document defines the CLI interface that Holodeck Studio exposes to users. All commands are accessed via the `holodeck` CLI entry point.

## Command Schema

### `holodeck produce`

Start a new production from a theme prompt.

```text
holodeck produce <prompt> [OPTIONS]

Arguments:
  PROMPT    Theme or story prompt (min 20 characters)

Options:
  --mode TEXT          Production mode: autonomous|supervised (default: autonomous)
  --bible TEXT         Franchise bible name or ID to use
  --config TEXT        Path to custom configuration file
  --output DIR         Output directory for production assets (default: ./output)
  --no-approve         Skip all approval checkpoints (autonomous mode)
  --dry-run            Validate prompt and show plan without executing

Exit codes:
  0  Production started successfully
  1  Invalid prompt (too vague or too short)
  2  Configuration error
  3  Storage connection error
```

### `holodeck status`

Check the status of a production or specific episode.

```text
holodeck status <production-id> [OPTIONS]

Arguments:
  PRODUCTION_ID    Production UUID

Options:
  --episode INT    Show specific episode number
  --stage TEXT     Show details for a specific stage
  --verbose        Include agent execution details and costs
  --json           Output as JSON

Exit codes:
  0  Success
  1  Production not found
```

### `holodeck approve`

Approve a production at a checkpoint.

```text
holodeck approve <production-id> [OPTIONS]

Arguments:
  PRODUCTION_ID    Production UUID

Options:
  --stage TEXT       Stage to approve (concept|outline|script|storyboard|asset_generation|audio|animation|review|release)
  --episode INT     Episode number (default: 1)
  --note TEXT       Optional approval note

Exit codes:
  0  Approved successfully
  1  No pending checkpoint for this stage
  2  Production not found or not in supervised mode
```

### `holodeck reject`

Reject a production at a checkpoint with revision feedback.

```text
holodeck reject <production-id> [OPTIONS]

Arguments:
  PRODUCTION_ID    Production UUID

Options:
  --stage TEXT       Stage to reject (required)
  --episode INT     Episode number (default: 1)
  --feedback TEXT   Required: revision feedback for agents

Exit codes:
  0  Rejected successfully, revision initiated
  1  No pending checkpoint for this stage
  2  Production not found or not in supervised mode
  3  Missing required --feedback
```

### `holodeck review`

View review reports for a production or episode.

```text
holodeck review <production-id> [OPTIONS]

Arguments:
  PRODUCTION_ID    Production UUID

Options:
  --episode INT     Review specific episode number
  --type TEXT        Filter by reviewer type: critic|audience_simulation|qa
  --verbose          Include full review content
  --json            Output as JSON

Exit codes:
  0  Success
  1  No reviews found
  2  Production not found
```

### `holodeck pause`

Pause a running production.

```text
holodeck pause <production-id>

Arguments:
  PRODUCTION_ID    Production UUID

Exit codes:
  0  Production paused
  1  Production not running
  2  Production not found
```

### `holodeck resume`

Resume a paused production.

```text
holodeck resume <production-id>

Arguments:
  PRODUCTION_ID    Production UUID

Exit codes:
  0  Production resumed
  1  Production not paused
  2  Production not found
```

### `holodeck config`

Manage configuration (show, set, reset).

```text
holodeck config show                    Show current configuration
holodeck config set <key> <value>       Set a configuration value
holodeck config reset                   Reset to defaults

Config keys:
  max_feedback_iterations          Integer (default: 3)
  conflict_escalation_threshold    Integer (default: 3)
  quality_gate_threshold           Integer (default: 70)
  human_approval_timeout_seconds   Integer (default: 3600)
  default_mode                     autonomous|supervised
  default_model_provider           String (Agno identifier)
```

### `holodeck bible`

Manage franchise bibles.

```text
holodeck bible list                          List all bibles
holodeck bible show <bible-id>               Show bible details
holodeck bible create <name> [DESCRIPTION]   Create a new bible
holodeck bible add-entry <bible-id>          Add an entry to a bible
  --category TEXT   Category: character|location|technology|lore|event
  --name TEXT       Entry name
  --content TEXT    Entry content
holodeck bible search <bible-id> <query>     Search bible entries
```

## Output Formats

### Default: Human-readable

Production status output uses Rich formatting with colored stage indicators, progress bars, and cost summaries.

### JSON Output (`--json` flag)

```json
{
  "production_id": "uuid",
  "theme_prompt": "...",
  "status": "running",
  "mode": "autonomous",
  "episodes": [
    {
      "episode_number": 1,
      "current_stage": "script",
      "stage_status": "awaiting_approval",
      "feedback_iterations": 1,
      "assets_count": 3,
      "cost_usd": 0.45
    }
  ],
  "total_cost_usd": 0.45,
  "created_at": "2026-06-07T10:00:00Z",
  "updated_at": "2026-06-07T10:15:00Z"
}
```

## Error Handling

- All commands return structured error messages to stderr
- JSON mode includes error details in a consistent format: `{"error": {"code": "INVALID_PROMPT", "message": "..."}}`
- Vague prompt rejection (FR-001) returns exit code 1 with guidance: `"Prompt is too vague. Please specify: genre, themes, characters, or story direction."`