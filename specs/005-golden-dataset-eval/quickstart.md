# Quickstart: Golden Dataset Evaluation

## Run a Single Evaluation

```bash
# Run evaluation on one golden dataset entry
uv run python tests/evals/script_eval.py --entry rival-chef-s01

# Run against all entries in the golden dataset
uv run python tests/evals/script_eval.py --all

# Dry-run: validate golden dataset structure without calling LLM
uv run python tests/evals/script_eval.py --validate-only
```

## Run Unit Tests

```bash
# Unit tests only (no cluster, no LLM calls)
uv run pytest tests/unit/evaluation/ -xvs

# All tests
uv run pytest tests/unit/ -xvs
```

## Golden Dataset

The golden dataset lives at `tests/evals/fixtures/friends_golden.json`.

To add a new entry, add an object to the `entries` array following the schema in
`specs/005-golden-dataset-eval/contracts/golden-dataset-schema.json`.

## Package Layout

```
src/holodeck/
├── evaluation/
│   ├── __init__.py
│   ├── schemas.py       # GoldenDatasetEntry, DimensionScore, EvaluationResult, BatchEvaluationReport
│   ├── loader.py        # load_golden_dataset(), validate_entry()
│   ├── runner.py        # EvaluationRunner: evaluate_single(), run_batch()
│   └── reporter.py      # BatchReporter: aggregate(), detect_regressions(), export_report()
├── agents/
│   └── evaluation/
│       ├── __init__.py
│       └── judge.py     # JudgeAgent: process() → DimensionScore list

tests/
├── evals/
│   ├── fixtures/
│   │   └── friends_golden.json   # Seed dataset (5 Friends entries)
│   └── script_eval.py            # CLI entrypoint for eval runs
└── unit/
    └── evaluation/
        ├── test_schemas.py        # Pydantic model validation tests
        ├── test_loader.py         # Golden dataset load/validate tests
        └── test_runner.py         # EvaluationRunner unit tests (no LLM)
```

## Adding a New Evaluation Dimension

1. Add to `EvaluationDimension.DIMENSIONS` in `src/holodeck/evaluation/schemas.py`
2. Ensure weights still sum to 1.0 (adjust other weights if needed)
3. Update `contracts/evaluation-result-schema.json` enum to include the new dimension name
4. Add signal tests in `tests/unit/evaluation/test_schemas.py`

## Viewing Results

Evaluation results are persisted to PostgreSQL table `evaluation_results`.
Query via psql or any SQLAlchemy session:

```python
from holodeck.evaluation.runner import EvaluationRunner
results = await EvaluationRunner.get_history("rival-chef-s01")
```
