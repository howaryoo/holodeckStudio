# Quickstart: Holodeck Studio

**Feature**: 001-holodeck-studio
**Date**: 2026-06-07

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 16+ with pgvector extension
- MinIO (or S3-compatible object storage)

## Local Development Setup

```bash
# 1. Clone and enter the project
git clone <repo-url> holodeck-studio
cd holodeck-studio

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Start infrastructure services
docker compose up -d postgres minio

# 5. Run database migrations
alembic upgrade head

# 6. Configure environment
cp .env.example .env
# Edit .env with your model provider API keys and Langfuse credentials

# 7. Verify setup
holodeck config show
```

## First Production (MVP — Script Generation)

```bash
# Start a script-only production
holodeck produce "Create a 20-minute science-fiction episode about a crew exploring a derelict space station, with themes of isolation, discovery, and sacrifice"

# Check production status
holodeck status <production-id>

# In supervised mode, approve the script when prompted
holodeck approve <production-id> --stage script --note "Script looks good, proceed"

# Or reject with feedback
holodeck reject <production-id> --stage script --feedback "The antagonist's motivation is unclear. Add more backstory about their connection to the station."

# View the final script
holodeck status <production-id> --verbose
```

## Franchise Bible

```bash
# Create a franchise bible
holodeck bible create "Star Trek Voyager Universe" "The ongoing story of a starship crew lost in the Delta Quadrant"

# Add characters
holodeck bible add-entry <bible-id> \
  --category character \
  --name "Captain Janeway" \
  --content "Starfleet captain commanding the USS Voyager. Pragmatic leader with strong ethical principles."

# Search the bible
holodeck bible search <bible-id> "leadership style of the captain"
```

## Configuration

```bash
# View current configuration
holodeck config show

# Adjust feedback loop limits
holodeck config set max_feedback_iterations 5

# Set quality gate threshold
holodeck config set quality_gate_threshold 80

# Switch to supervised mode by default
holodeck config set default_mode supervised
```

## Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests (requires Docker)
pytest tests/integration/

# Run contract tests
pytest tests/contract/

# Run with coverage
pytest --cov=holodeck --cov-report=html
```

## Project Structure

```text
holodeck-studio/
├── src/holodeck/          # Source code
│   ├── cli/               # CLI entry points
│   ├── agents/            # Agent implementations by department
│   ├── pipeline/          # Stage orchestration and event bus
│   ├── memory/            # Franchise bible, episode, production memory
│   ├── storage/           # PostgreSQL and object storage adapters
│   ├── observability/     # Langfuse tracing integration
│   └── config/            # Pydantic settings
├── tests/                 # Test suite
├── specs/001-holodeck-studio/  # Specification documents
├── docker-compose.yml     # Local infrastructure
├── pyproject.toml         # Project configuration
└── alembic/               # Database migrations
```

## Key Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://holodeck:holodeck@localhost:5432/holodeck

# Object Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=holodeck-assets

# Langfuse (Observability)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Model Providers (Agno-abstracted)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# Application
HODELDECK_DEFAULT_MODE=autonomous
HOLODECK_MAX_FEEDBACK_ITERATIONS=3
HOLODECK_QUALITY_GATE_THRESHOLD=70
```