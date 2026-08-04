# Contributing to Subscriber Analytics Platform

## 1. Purpose

Subscriber Analytics Platform is currently maintained as a portfolio and learning project, but contributions should follow professional engineering practices.

This guide defines the local workflow, code organization, testing, documentation, and Git conventions.

---

## 2. Development principles

Contributions should favor:

- correctness over cleverness;
- explicit contracts over hidden assumptions;
- small, reviewable changes;
- deterministic behavior where practical;
- separation of concerns;
- meaningful tests;
- secure configuration;
- documentation that matches implementation.

Avoid adding a technology unless it solves a defined problem.

---

## 3. Prerequisites

Recommended:

- Python 3.11 or later;
- Git;
- Visual Studio Code or another Python-capable editor;
- PowerShell, Bash, or equivalent shell;
- AWS CLI for S3 integration;
- a MongoDB Atlas project only when running the serving synchronization;
- Docker only for containerized milestones.

---

## 4. Local environment

```bash
git clone <repository-url>
cd subscriber-analytics-platform
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

When a lock file is adopted, use the documented lock-based command.

---

## 5. Environment configuration

Create `.env` from `.env.example`.

Rules:

- never commit `.env`;
- never commit passwords, tokens, connection strings, or private keys;
- never place AWS keys in source code;
- use an AWS named profile locally;
- keep `MONGODB_URI` only in `.env` or an approved secret manager;
- never commit a populated MongoDB connection string;
- sanitize logs and screenshots.

---

## 6. Generated files

The following should remain outside Git:

```text
data/
logs/
reports/
.env
__pycache__/
.pytest_cache/
.venv/
```

Sample data may be committed only when it is small, synthetic, intentional, documented, and stored in a dedicated fixture or sample directory.

---

## 7. Repository boundaries

### `generators/`

Synthetic event generation only.

### `storage/`

Local persistence utilities and path behavior.

### `ingestion/`

Transfer adapters such as S3 upload.

### `analytics/`

Business transformations and curated datasets.

### `scripts/`

Command-line orchestration and standalone data-product rebuilds.

### `config/`

General application settings.

### `infrastructure/`

External-platform configuration and helpers.

### `api/`

FastAPI application and API models.

### `dashboards/`

Apache Superset assets, dashboard exports, or supporting analytical
presentation configuration. Superset queries Snowflake; operational consumer
applications use FastAPI.

### `tests/`

Unit and integration tests.

Do not duplicate business logic across modules.

---

## 8. Coding standards

### Style

- follow PEP 8;
- use four spaces;
- use descriptive names;
- prefer small functions with one responsibility;
- use type hints for public functions;
- document non-obvious behavior;
- avoid deeply nested control flow;
- avoid global mutable state;
- avoid expensive work at import time.

### Function contracts

Public transformation functions should document:

- input type;
- expected fields or columns;
- output type;
- output grain;
- exceptions;
- overwrite behavior;
- side effects.

### Paths

Use `pathlib.Path` rather than manual path concatenation.

### Time

- use timezone-aware UTC timestamps;
- do not use naive datetimes for event or run metadata;
- make processing time injectable.

### Exceptions

- raise specific exceptions;
- include actionable context;
- do not suppress errors silently;
- preserve causes with `raise ... from ...` where useful.

---

## 9. Data engineering standards

### Schema validation

Validate required fields or columns before transformation.

### Grain

Every curated function must state its output grain.

### Uniqueness

Explicitly validate keys for aggregate datasets.

### Numeric integrity

- counters are non-negative;
- bytes remain bytes unless field names state another unit;
- weighted averages use sums and sample counts;
- division by zero produces null, not a fabricated zero.

### Determinism

Latest-record selection uses explicit ordering and a tie-breaker when required.

### Atomic writes

Use temporary files and final replacement for authoritative snapshots.

---

## 10. Logging

Use the project logging configuration rather than `print()` for pipeline operations.

Logs should identify:

- run;
- stage;
- processing date and hour;
- input and output;
- count;
- status.

Never log credentials, tokens, or connection strings.

---

## 11. Testing

Run before committing:

```bash
pytest
```

### Unit tests

For pure functions and isolated modules.

### File integration tests

For local stage-to-stage behavior using temporary directories.

### External integration tests

For AWS or MongoDB. Mark them so they are excluded from the default fast suite unless the required environment is available.

### Expected scenarios

A new feature should test:

- normal path;
- empty input;
- invalid input;
- duplicates;
- rerun behavior;
- output schema;
- key uniqueness;
- reconciliation.

Tests must not depend on developer-specific data, existing outputs, a particular AWS account, test order, or internet access unless explicitly marked.

### Manual current-profile validation

After automated tests pass, rebuild the current-profile snapshot with:

```bash
python -m scripts.run_current_profiles
```

Confirm that the output contains exactly one row per `subscriber_id`, no duplicate subscriber keys, valid UTC metadata, and no temporary publication artifact.

### Manual MongoDB synchronization validation

After the current profile is valid and Atlas connectivity is configured:

```bash
python -m scripts.sync_mongodb_profiles
```

Run the command twice. The second unchanged run should report zero modified and
zero upserted documents. Confirm that:

- the document count equals the source profile count;
- distinct `subscriber_id` count equals the document count;
- `_id_` and `uq_subscriber_id` exist;
- `uq_subscriber_id` is unique;
- existing `_id` values are preserved;
- dates are BSON dates and missing values are BSON nulls.

---

## 12. Documentation standards

Documentation is written in English for an international audience.

Update documentation when a change affects:

- architecture;
- CLI usage;
- data schema;
- output paths;
- rerun behavior;
- roadmap;
- configuration;
- external services.

Primary documents:

- `README.md`;
- `docs/ARCHITECTURE.md`;
- `docs/DATA_MODEL.md`;
- `docs/PIPELINE.md`;
- `docs/DECISIONS.md`;
- `docs/ROADMAP.md`;
- `docs/CONTRIBUTING.md`.

Avoid duplicating the same detailed content in multiple files. Link to the authoritative document.

---

## 13. Git workflow

Before changing code:

```bash
git status
```

Suggested branch names:

```text
feature/current-subscriber-profiles
feature/mongodb-serving
feature/fastapi-service
fix/daily-reconciliation
docs/architecture-refresh
test/profile-builder
```

A branch is recommended for larger milestones. Small, controlled changes may follow the maintainer's direct-to-main workflow.

### Focused commits

Good examples:

```text
Add current subscriber profile builder
Add tests for weighted lifetime metrics
Document MongoDB serving model
```

Avoid vague messages such as `Updates` or `Fix stuff`.

---

## 14. Commit messages

Use imperative English:

```text
<verb> <scope or result>
```

Examples:

```text
Add structured pipeline execution reports
Centralize application directory settings
Validate duplicate daily subscriber windows
Build weighted lifetime quality metrics
Document current profile data contract
```

A commit body may explain motivation, trade-offs, migration, or breaking impact.

---

## 15. Version tags

Tags are immutable.

Before tagging:

1. run all tests;
2. review documentation;
3. confirm `git status` is clean;
4. verify the version does not already exist;
5. create an annotated tag;
6. push the tag.

Example:

```bash
git tag -a v0.2.1 -m "Add pipeline observability and reliability improvements"
git push origin v0.2.1
```

Never move an existing public tag.

---

## 16. Pull request guidance

Include:

### Summary

What changed?

### Motivation

Why is it needed?

### Validation

Which tests ran?

### Data impact

Did schemas, paths, partitions, or counts change?

### Security impact

Were credentials, permissions, or external services affected?

### Documentation

Which documents changed?

---

## 17. Definition of done

A change is complete when applicable criteria are met:

- implementation finished;
- type hints added;
- errors handled;
- tests pass;
- new behavior tested;
- no secrets committed;
- generated files excluded;
- logs are useful;
- documentation updated;
- Git status clean;
- commit message meaningful.

---

## 18. Feature-specific checklist

### New curated dataset

- grain documented;
- source documented;
- required columns validated;
- output path centralized;
- uniqueness checked;
- metric formulas tested;
- rerun behavior defined;
- atomic publication considered;
- documentation updated.

### New cloud integration

- least-privilege permissions;
- no hard-coded credentials;
- timeout and error handling;
- retries only where safe;
- local setup documented;
- cost implications considered;
- integration-test strategy defined.

### New API endpoint

- request validation;
- response model;
- pagination where needed;
- error codes;
- database timeout handling;
- tests;
- OpenAPI description;
- no database credentials exposed.

---

## 19. Security reporting

Do not open a public issue containing credentials or exploitable sensitive details.

If a credential is exposed:

1. revoke or rotate it immediately;
2. remove it from current files;
3. inspect Git history;
4. clean history when necessary;
5. document remediation without publishing the secret.

---

## 20. Related documentation

- [Architecture](ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Pipeline](PIPELINE.md)
- [Architecture decisions](DECISIONS.md)
- [Roadmap](ROADMAP.md)
