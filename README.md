# Holodeck Studio

> As a Star Trek fan disappointed by the newest productions, I created a multi-agent system for video series production. If you're not a Star Trek fan, no worries — this works on any subject :-)

Created via [opencode](https://opencode.ai) × [Spec Kit](https://github.com/tikal/spec-kit) — spec-driven AI software engineering.  
Codebase built iteratively from specs (`specs/` → plans → research → tasks → impl), all within opencode CLI.  
[RTK (Rust Token Killer)](https://github.com/khunkin/rtk) for lean context management. [Caveman](https://opencode.ai) mode for ultra-terse agent communication.

## Kubernetes Deployment (Colima)

## Prerequisites

- Python 3.11+
- [Colima](https://github.com/abiosoft/colima) with Kubernetes enabled
- `kubectl` CLI
- `uv` for Python package management
- **Media generation** (stage 20–22): `ffmpeg`, `convert` (ImageMagick) binaries
  ```bash
  # Ubuntu/Debian
  sudo apt install ffmpeg imagemagick
  # macOS
  brew install ffmpeg imagemagick
  ```

## Quick Start (Make)

```bash
# Full cluster up — colima → k8s → infra → port-forwards → migrations
make start

# Stop services (keep cluster running)
make stop

# Full teardown including volumes (destroys data)
make delete

# Cluster status + k8s pods
make status
```

## Manual Steps

## 5. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## 6. Configure Environment

```bash
cp .env.example .env
# Add your model provider API keys:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-...
# Langfuse keys (if using):
# LANGFUSE_PUBLIC_KEY=pk-...
# LANGFUSE_SECRET_KEY=sk-...
```

## 7. Run Database Migrations

```bash
alembic upgrade head
```

## 8. User Guide — Bible & Produce

### Franchise Bibles

```bash
# Create a bible
holodeck bible create "Star Trek: Voyager" "A Star Trek fan series set in the 25th century"

# List bibles
holodeck bible list

# Show bible details + entries
holodeck bible show <bible-id>

# Add lore entries (categories: character, location, technology, lore, event)
holodeck bible add-entry <bible-id> \
  --category technology \
  --name "Alien Relay Network" \
  --content "Ancient network of subspace relay stations that fold spacetime. \
Activating a relay emits a energy signature that attracts predatory species."

holodeck bible add-entry <bible-id> \
  --category character \
  --name "Captain Mira Kessler" \
  --content "Human, late 30s, pragmatic but compassionate. Former Starfleet tactical officer."

holodeck bible add-entry <bible-id> \
  --category lore \
  --name "The Fold Predators" \
  --content "Unknown species that hunts by sensing fold-space energy. \
They can track ships across sectors once a relay is activated."

# Search bible entries
holodeck bible search <bible-id> "relay"
```

Bibles are stored in memory (process lifetime). Use `--bible <id>` with `produce` to inject entries as context for canon verification.

### Producing a Script

```bash
# Dry-run: validate prompt without LLM calls
holodeck produce "A stranded crew discovers an ancient alien relay network" --dry-run

# Full production: runs all 5 agents with LLM calls
holodeck produce "A stranded crew discovers an ancient relay network that can fold space, \
but using it attracts a predator species" --bible <bible-id>

# With a specific production mode
holodeck produce "A stranded crew..." --mode supervised --bible <bible-id>

# Skip approval checkpoints (autonomous mode)
holodeck produce "A stranded crew..." --no-approve
```

The pipeline runs: **Showrunner** → **Head Writer** → **Staff Writer** → **Canon Historian** → **Critic**. Each agent calls the configured LLM model, reviews its own output, and results are tracked in memory.

### Production Status

```bash
# Basic status
holodeck status <production-id>

# With agent execution table (scores, approvals)
holodeck status <production-id> --verbose

# Raw JSON output
holodeck status <production-id> --json
```

### Configuration

```bash
# View all settings
holodeck config show

# Override a setting (persisted to ~/.holodeck/config.json)
holodeck config set holodeck_default_model "openai/gpt-5.4-mini"

# Reset to defaults
holodeck config reset
```

Override precedence: CLI flags > `~/.holodeck/config.json` > `.env` > defaults.

## Running Tests

```bash
# All tests
pytest

# Unit tests only (no cluster required)
pytest tests/unit/

# Integration tests (requires cluster + port-forwards)
pytest tests/integration/

# With coverage
pytest --cov=holodeck --cov-report=html
```

## Infrastructure Access

| Service | Cluster Service | Port-Forward | Local URL |
|---------|----------------|--------------|-----------|
| PostgreSQL | `postgres:5432` | `5432` | `localhost:5432` |
| MinIO API | `minio:9000` | `9000` | `localhost:9000` |
| MinIO Console | `minio:9001` | `9001` | http://localhost:9001 |
| Langfuse | `langfuse:3000` | `3000` | http://localhost:3000 |

MinIO Console login: `minioadmin` / `minioadmin`

## Useful Commands

```bash
# Quick teardown (volumes preserved)
make stop

# Full reset (volumes deleted — data lost)
make delete

# View all Holodeck resources
kubectl get all -l app=holodeck

# View pod logs
kubectl logs -l app=holodeck,component=postgres --tail=50
kubectl logs -l app=holodeck,component=minio --tail=50

# Connect to PostgreSQL
kubectl exec -it deployment/postgres -- psql -U holodeck -d holodeck

# Stop Colima only
colima stop
```

## Project Structure

```text
k8s/
├── config.yaml          # Secrets + ConfigMap
├── postgres.yaml        # PostgreSQL + pgvector Deployment/Service/PVC
├── minio.yaml           # MinIO Deployment/Service/PVC
├── langfuse.yaml        # Langfuse Deployment/Service (optional)
└── init-jobs.yaml       # Database + bucket initialization Jobs
src/holodeck/
├── cli/                 # CLI entry points (Typer)
├── agents/              # Agent implementations by department
├── pipeline/            # Stage orchestration, events, orchestrator
├── memory/              # Franchise Bible, Episode, Production memory
├── storage/             # PostgreSQL and object storage adapters
├── observability/       # Langfuse tracing, evaluation
└── config/              # Pydantic settings
```

## MVP Scope (Phase 1)

Script generation pipeline only (Concept → Outline → Script → Review → Release). Visual, audio, and animation are future phases.