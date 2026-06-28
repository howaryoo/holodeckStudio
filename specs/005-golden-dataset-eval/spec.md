# Feature Specification: Golden Dataset Evaluation Framework for Sitcom Scripts

**Feature Branch**: `005-golden-dataset-eval`  
**Created**: 2026-06-21  
**Status**: Draft  
**Input**: Build a golden dataset-based evaluation system for sitcom script generation, applying "eval-first development" principles from the Tech Pioneer course to assess script quality.

## Clarifications

### Session 2026-06-21

- Q: Exact evaluation dimension count — FR-004 stated "7-10", SC-004 stated "8", but 9 were named. → A: 8 dimensions (remove pacing). Canonical list: Narrative Coherence, Character Consistency, Comedy Effectiveness, Dialogue Naturalness, Story Structure, Emotional Impact, Production Feasibility, Thematic Alignment.
- Q: Judge agent — new, repurposed, or external component? → A: New dedicated Judge agent inheriting from BaseAgent, handles all dimension scoring and reasoning for the evaluation framework.
- Q: Performance targets (2 min/script, 30 min/batch) — hard requirements or soft aspirational? → A: Soft targets. LLM inference latency is an accepted bottleneck; targets are aspirational optimizations for system efficiency, not hard SLAs.
- Q: Batch evaluation failure handling — fail-fast, resilient with partial results, or retry? → A: Resilient with partial results. Failed individual script evaluations are skipped with clear reporting in batch results; batch continues to completion. Partial results are acceptable and valuable for trend analysis.
- Q: Regression detection baseline — previous run, rolling average, first evaluation, or user-configurable? → A: Previous run only (baseline = most recent prior evaluation of same golden dataset prompt). Regression triggered when current scores drop >10% vs. previous.
- Q: Golden dataset TV show reference — which show? → A: "Friends" — golden dataset scenarios based on Friends format: ensemble apartment comedy, character-driven humor, A/B plots, established ensemble dynamics (Rachel, Monica, Phoebe, Joey, Chandler, Ross).

## User Scenarios & Testing

### User Story 1 - Load and Curate Golden Dataset (Priority: P1)

As a studio content curator, I want to build a curated golden dataset of sitcom prompts with expected quality guidelines, so that I have a standardized benchmark for evaluating script generation quality across all episodes.

**Why this priority**: The golden dataset is the foundation of the entire evaluation system. Without it, all downstream evaluation is arbitrary and uncalibrated.

**Independent Test**: Can be fully tested by loading a dataset file, validating its structure, and verifying all prompts have defined guidelines. This alone delivers the ability to document what "good" looks like.

**Acceptance Scenarios**:

1. **Given** no golden dataset exists, **When** a curator provides a JSON file with prompts and guidelines, **Then** the system accepts and validates the dataset structure
2. **Given** a valid golden dataset, **When** the system loads it, **Then** each prompt has associated quality guidelines (narrative goals, comedy elements, character notes, production constraints)
3. **Given** a golden dataset with missing or malformed guidelines, **When** validation runs, **Then** specific validation errors are reported with remediation guidance

---

### User Story 2 - Generate Scripts with Golden Dataset Prompts (Priority: P1)

As an evaluation engineer, I want the system to generate sitcom scripts using golden dataset prompts, so that I can compare real output against the expected guidelines.

**Why this priority**: Script generation against golden dataset prompts is the core evaluation workflow. Without this, there's no raw material to evaluate.

**Independent Test**: Can be fully tested by running the script generation pipeline with a golden dataset prompt and verifying script generation completes successfully with all required story elements.

**Acceptance Scenarios**:

1. **Given** a golden dataset prompt, **When** I trigger script generation, **Then** the system produces a complete script with dialogue, stage directions, and character interactions
2. **Given** script generation completes, **When** I inspect the script metadata, **Then** it includes the source golden dataset prompt ID for traceability
3. **Given** script generation fails, **When** the error is logged, **Then** I can identify which agent in the pipeline failed and why

---

### User Story 3 - Evaluate Scripts Against Quality Guidelines (Priority: P1)

As a quality reviewer, I want the evaluation system to assess generated scripts against golden dataset guidelines across multiple quality dimensions, so that I can quantify how well the generation matched expected outcomes.

**Why this priority**: Evaluation is the entire purpose of the framework. This drives the quality gates and improvement signals.

**Independent Test**: Can be fully tested by evaluating a generated script against its corresponding golden dataset guidelines and producing a structured quality report with dimension scores and reasoning.

**Acceptance Scenarios**:

1. **Given** a generated script and its golden dataset entry, **When** evaluation runs, **Then** the script is scored across 7-10 quality dimensions (narrative coherence, character consistency, comedy effectiveness, dialogue naturalness, story structure, emotional impact, production feasibility, thematic alignment, and pacing)
2. **Given** evaluation completes, **When** I review the results, **Then** I see individual dimension scores, dimension weights, overall score, and evidence/reasoning for each dimension
3. **Given** a script falls below a quality threshold, **When** I inspect the evaluation, **Then** specific red flags and failure signals are highlighted (e.g., plot holes, character contradictions, unfeasible production requirements)

---

### User Story 4 - Compare Output to Expected Guidelines (Priority: P2)

As a system validator, I want to compare generated script attributes directly against the expected result guidelines from the golden dataset, so that I can identify gaps between what was generated and what was intended.

**Why this priority**: Direct comparison provides diagnostic insight into where generation diverges from intent, enabling targeted system improvements.

**Independent Test**: Can be fully tested by generating a comparison report between golden dataset guidelines and generated script properties without requiring manual review.

**Acceptance Scenarios**:

1. **Given** a generated script and its golden dataset guidelines, **When** comparison runs, **Then** the system produces a mapping showing which guideline requirements were met, partially met, or missed
2. **Given** comparison results, **When** I review the output, **Then** I see specific example text from both the guidelines and the generated script to illustrate gaps
3. **Given** guidelines specify multiple acceptable variations (e.g., "comedy can be situational or witty or slapstick"), **When** comparison evaluates comedy approach, **Then** it recognizes which variation was used and whether it's among the acceptable options

---

### User Story 5 - Batch Evaluate and Report Trends (Priority: P2)

As a pipeline manager, I want to run batch evaluations across multiple golden dataset prompts and aggregate results, so that I can identify systemic quality trends and improvement opportunities.

**Why this priority**: Aggregate metrics reveal whether quality issues are systematic or isolated, enabling data-driven improvements to the generation pipeline.

**Independent Test**: Can be fully tested by running evaluation on a set of golden dataset prompts and producing an aggregate report without requiring interactive review.

**Acceptance Scenarios**:

1. **Given** 10+ golden dataset prompts, **When** batch evaluation completes, **Then** I receive summary statistics (average dimension scores, pass/fail rates, common failure patterns)
2. **Given** batch results, **When** I filter by dimension, **Then** I can see which dimensions consistently score low or high across the dataset
3. **Given** batch results, **When** I export the report, **Then** the format supports both human review (markdown, PDF) and programmatic analysis (JSON, CSV)

---

### User Story 6 - Track Evaluation History and Regressions (Priority: P3)

As a quality lead, I want the system to maintain historical evaluation records, so that I can track quality over time and detect regressions when the generation pipeline is modified.

**Why this priority**: Regression detection prevents silent quality degradation and provides accountability for pipeline changes.

**Independent Test**: Can be fully tested by running evaluation on the same golden dataset prompts at different points in time and comparing results.

**Acceptance Scenarios**:

1. **Given** evaluation results from two different dates, **When** I compare them, **Then** the system highlights dimension scores that improved, degraded, or stayed the same
2. **Given** a regression is detected, **When** I investigate, **Then** I can link it to specific agent or configuration changes made between evaluations
3. **Given** historical data, **When** I visualize trends, **Then** I can see quality trajectory (improving, stable, degrading) over time

---

### Edge Cases

- What happens when a golden dataset guideline conflicts with another guideline in the same entry?
- How does the system handle scripts that deviate significantly from the prompt intent but are still high-quality narratively?
- What if evaluation dimensions have conflicting signals (e.g., high production feasibility but low visual spectacle)?
- How does the system handle edge cases where the generated script is very different from the golden dataset expectation but still valid?
- **Batch failure handling**: When an individual script evaluation fails mid-batch (e.g., LLM timeout, Judge agent error), the system skips that entry with error logging and continues evaluating remaining scripts. Batch results include failure counts and details for each failed entry.

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept a golden dataset in JSON format containing prompts, expected quality guidelines, and reference acceptable outputs
- **FR-002**: System MUST validate golden dataset structure, ensuring all required fields are present and well-formed
- **FR-003**: System MUST execute sitcom script generation using golden dataset prompts as input
- **FR-004**: System MUST define exactly 8 evaluation dimensions for script quality assessment: narrative coherence, character consistency, comedy effectiveness, dialogue naturalness, story structure, emotional impact, production feasibility, and thematic alignment
- **FR-005**: System MUST score each dimension on a 0.0-1.0 scale with associated reasoning and evidence
- **FR-006**: System MUST assign weights to each dimension such that all weights sum to exactly 1.0
- **FR-007**: System MUST calculate an overall quality score as the weighted average of all dimension scores
- **FR-008**: System MUST define red flag signals for each dimension that indicate hard rejections (critical failures)
- **FR-009**: System MUST define concrete, measurable signals (with thresholds) for each dimension rather than vague criteria
- **FR-010**: System MUST compare generated script properties directly against golden dataset guidelines and report gaps
- **FR-011**: System MUST support batch evaluation across multiple golden dataset prompts
- **FR-012**: System MUST produce structured evaluation reports (JSON format) containing all dimension scores, reasoning, and evidence
- **FR-013**: System MUST persist evaluation results with metadata (timestamp, prompt ID, script ID, generator version, evaluator version)
- **FR-014**: System MUST identify and report regression when current evaluation scores are lower than historical scores for the same prompt
- **FR-015**: System MUST provide query capability to retrieve evaluation history for a given golden dataset prompt

### Key Entities

- **GoldenDatasetEntry**: Represents one test case with a prompt, expected guidelines, reference outputs, and quality criteria
  - `prompt_id`: Unique identifier
  - `user_prompt`: The sitcom concept/scenario prompt
  - `quality_guidelines`: Expected result guidelines (narrative goals, character arcs, comedy approach, production constraints)
  - `reference_outputs`: One or more example "good" scripts that meet the guidelines
  - `scope_boundaries`: What should/should not be included
  - `acceptable_variations`: Multiple valid ways to achieve the guideline

- **EvaluationDimension**: Represents one quality assessment criterion
  - `name`: Dimension name (e.g., "Narrative Coherence")
  - `description`: What this dimension measures
  - `weight`: Contribution to overall score (0.0-1.0)
  - `signals`: List of concrete, measurable indicators with thresholds
  - `red_flags`: Signals that trigger hard rejection
  - `data_sources`: Where evaluation data comes from (script text, character list, plot summary, etc.)

- **EvaluationResult**: Represents the assessment outcome for one script
  - `script_id`: Which script was evaluated
  - `golden_entry_id`: Which golden dataset entry prompted this script
  - `dimension_scores`: Dict mapping dimension name to DimensionScore
  - `overall_score`: Weighted average of all dimension scores
  - `passed_quality_gate`: Boolean indicating if overall score ≥ threshold
  - `red_flags_triggered`: List of red flags that fired
  - `evaluation_timestamp`: When evaluation ran
  - `comparison_to_guidelines`: Direct mapping of generated properties to expected guidelines

- **BatchEvaluationReport**: Aggregates multiple evaluation results
  - `golden_dataset_version`: Which golden dataset was used
  - `evaluation_results`: List of EvaluationResult objects
  - `summary_statistics`: Aggregated metrics (average scores per dimension, pass/fail counts, failure patterns)
  - `trend_data`: Changes from prior batch evaluation (regressions, improvements)
  - `generated_timestamp`: When batch completed

## Success Criteria

### Measurable Outcomes

- **SC-001**: Golden dataset loader successfully validates and accepts a dataset with 10+ prompts and guidelines without errors
- **SC-002**: Script generation runs successfully on all golden dataset prompts with 100% completion rate
- **SC-003**: Evaluation engine produces structured results for all scripts within 2 minutes per script (aspirational target; LLM inference latency is an accepted bottleneck and may extend this; system should optimize parallelization and caching where possible)
- **SC-004**: Evaluation results include all 8 canonical dimensions (narrative coherence, character consistency, comedy effectiveness, dialogue naturalness, story structure, emotional impact, production feasibility, thematic alignment) with scores, weights, reasoning, and evidence for 100% of dimension assessments
- **SC-005**: Overall quality score reflects a calibrated scale: 0.0-0.35 = rejection, 0.35-0.65 = revision needed, 0.65-1.0 = acceptable (thresholds based on golden dataset intent)
- **SC-006**: Batch evaluation of 10 golden dataset prompts completes end-to-end (generation + evaluation) in under 30 minutes (aspirational; LLM inference latency may extend actual wall-clock time; system should implement parallel batch processing and caching to approach target)
- **SC-007**: Regression detection correctly identifies when a script's dimension scores drop >10% compared to the immediately previous evaluation of the same golden dataset prompt (baseline = previous run)
- **SC-008**: Evaluation reports are human-readable (structured markdown or JSON) and machine-parseable without custom post-processing
- **SC-009**: Comparison between generated output and golden guidelines identifies >80% of substantive deviations (plot gaps, missing character arcs, etc.)
- **SC-010**: Zero regression in generation quality when using identical prompts and golden dataset (consistent output across runs)

## Assumptions

- **Scope**: The golden dataset evaluation is intended for quality assessment of internal script generation; it is not an end-user feature exposed through the CLI in Phase 1
- **Evaluation approach**: Evaluation uses a combination of LLM-based reasoning (via a new dedicated Judge agent inheriting from BaseAgent) and heuristic signal detection (e.g., character mention counts, dialogue turn counts) rather than pure rule-based scoring
- **Data sources**: Generation produces structured intermediate data (character list, plot beats, dialogue turns) that evaluation can consume; parsing raw script text is a fallback but not the primary signal source
- **Threshold calibration**: The rejection threshold (0.35 overall score) is based on the golden dataset intent; this may be adjusted after pilot evaluation run
- **Historical tracking**: Evaluation results are persisted in the same database as production episodes (PostgreSQL) for historical queries and trend analysis
- **Golden dataset format**: The golden dataset is authored by humans (content team) in JSON or YAML and version-controlled in the repository
- **Golden dataset reference universe**: Golden dataset scenarios are based on "Friends" format — ensemble apartment comedy with 6 core characters (Rachel, Monica, Ross, Chandler, Joey, Phoebe), character-driven situational humor, A/B plot structure, established character dynamics and comedic archetypes. See `friends_bible.md` for full character profiles, setting details, and canonical reference material.
- **Evaluation cost**: LLM-based dimension scoring is acceptable even if it adds computational cost, as evaluation is not latency-critical (batch operation)
- **Scope boundary**: Evaluation does NOT include video/audio quality, lip-sync, or rendering fidelity; it focuses purely on script narrative and dialogue quality
- **Iteration model**: The golden dataset is expected to evolve; evaluation results inform which guidelines need refinement
