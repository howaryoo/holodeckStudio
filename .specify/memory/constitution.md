<!--
Sync Impact Report:
- Version change: (new) → 1.0.0
- Added principles:
  - I. Python-First Development
  - II. Zen of Python Philosophy
  - III. Single Responsibility
  - IV. Open/Closed & Liskov Substitution
  - V. Dependency Inversion & Interface Segregation
- Added sections: Technology Standards, Development Workflow, Governance
- Removed sections: (none — initial ratification)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (no changes needed — Constitution Check already references constitution file)
  - .specify/templates/spec-template.md ✅ (no changes needed — requirements align with SOLID principles)
  - .specify/templates/tasks-template.md ✅ (no changes needed — task structure compatible)
  - .specify/templates/commands/*.md ⚠ (no command files found in templates/commands/)
- Follow-up TODOs: (none)
-->

# HolodeckStudio Constitution

## Core Principles

### I. Python-First Development

Python is the primary implementation language for all project code. All
code MUST use Python idioms, type hints, and follow PEP 8 style
guidelines. No other language may be introduced without explicit
justification and approval documented in a spec or plan.

### II. Zen of Python Philosophy

Code MUST follow the design philosophy of the Zen of Python: explicit
is better than implicit, simple is better than complex, readability
counts, errors MUST never pass silently unless explicitly silenced,
and there SHOULD be one — and preferably only one — obvious way to
do it. Practicality beats purity, but practicality MUST be justified,
not assumed.

### III. Single Responsibility

Each module, class, and function MUST have exactly one reason to
change. No god objects or catch-all modules are permitted. If a class
has more than one responsibility, it MUST be split into focused
components.

### IV. Open/Closed & Liskov Substitution

Software entities MUST be open for extension but closed for
modification. New behavior MUST be added through new code, not by
modifying existing working code. Subtypes MUST be fully substitutable
for their base types; violations of the substitution principle
indicate a design flaw that MUST be corrected.

### V. Dependency Inversion & Interface Segregation

High-level modules MUST NOT depend on low-level modules; both MUST
depend on abstractions. Abstractions MUST NOT depend on details;
details MUST depend on abstractions. Clients MUST NOT be forced to
depend on interfaces they do not use. Prefer Python protocol classes
and composition over inheritance.

## Technology Standards

Python 3.11+ as primary language. Type hints REQUIRED on all function
signatures. PEP 8 compliance enforced via automated linting (ruff,
mypy). Dependencies managed through pyproject.toml. No vendored code
without explicit approval. Virtual environments REQUIRED for local
development.

## Development Workflow

Test-First Development: tests MUST be written before implementation.
Red-Green-Refactor cycle enforced. Code review REQUIRED for all merge
requests; reviewers MUST verify constitution compliance. Complexity
MUST be justified; simpler alternatives MUST be documented when
rejected.

## Governance

This constitution supersedes all other practices and conventions.
Amendments require documentation, team approval, and a migration plan.
All merge requests and code reviews MUST verify compliance with these
principles. Any deviation MUST be explicitly justified with a
documented rationale in the relevant spec or plan document.

**Version**: 1.0.0 | **Ratified**: 2026-06-07 | **Last Amended**: 2026-06-07