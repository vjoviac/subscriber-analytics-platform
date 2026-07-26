# Subscriber Analytics Platform

A portfolio-grade telecommunications data platform that simulates subscriber network events, enriches them with reference data, produces analytics-ready datasets, and prepares those datasets for operational and analytical consumption.

The project demonstrates practical skills in data engineering, solution architecture, cloud integration, observability, API design, and analytics delivery.

> **Current release:** `v0.2.3`  
> **Current focus:** a reliable batch pipeline through the atomic current subscriber profile snapshot.  
> **Next platform milestone:** MongoDB Atlas synchronization.

---

## Why this project exists

Telecommunications platforms generate large volumes of events that describe subscriber activity, devices, applications, network conditions, and usage patterns. These events create value only after they are transformed into reliable and understandable data products.

Subscriber Analytics Platform models that lifecycle:

1. Generate realistic telecom events.
2. Preserve immutable raw records.
3. Enrich events with subscriber, device, application, location, and network context.
4. Build hourly and daily analytical datasets.
5. Validate processing outcomes and record reconciliation.
6. Materialize current subscriber profiles.
7. Publish profiles to an operational serving database.
8. Expose data through APIs and dashboards.
9. Extend the platform with cloud-native analytics services.

The project evolves in stages so that each architectural capability can be implemented, tested, and explained independently.

---

## Key capabilities

### Implemented

- Synthetic telecom event generation in Python.
- JSON Lines raw storage.
- Reference-data enrichment.
- Parquet-based enriched storage.
- Hourly subscriber activity aggregation.
- Daily subscriber activity aggregation.
- Date- and hour-partitioned datasets.
- Daily pipeline orchestration.
- `SAFE`, `SKIP_EXISTING`, and `OVERWRITE` execution modes.
- Centralized configuration.
- Structured logging.
- JSON execution reports.
- Pipeline reconciliation and validation.
- Unit tests.
- Amazon S3 upload support using an AWS CLI named profile.
- Current subscriber profile snapshot.
- Deterministic latest-state and lifetime-metric construction.
- Atomic current-profile publication.
- Current-profile integration with the daily pipeline and execution report.

### Planned

- MongoDB Atlas serving layer.
- FastAPI service.
- Dashboard consuming the API.
- AWS Glue Data Catalog.
- Amazon Athena analytical queries.
- Containerization and deployment automation.
- Optional streaming ingestion path.
- Advanced analytical and AI-assisted use cases.

---

## High-level architecture

```text
Event Generator
      ↓
Raw Layer — JSONL
      ↓
Enrichment Layer — Parquet
      ↓
Hourly Curated Dataset
      ↓
Daily Curated Dataset
      ↓
Current Subscriber Profiles
      ↓
MongoDB Atlas
      ↓
FastAPI
      ↓
Dashboard

Analytical extension:
Curated Parquet → Amazon S3 → AWS Glue → Amazon Athena
```

For the complete design, see [Architecture](docs/ARCHITECTURE.md).

---

## Data layers

| Layer | Format | Purpose |
|---|---|---|
| Raw | JSONL | Immutable source events and replay capability |
| Enriched | Parquet | Event-level records with normalized and reference attributes |
| Curated hourly | Parquet | Subscriber activity by hourly window |
| Curated daily | Parquet | Subscriber activity by daily window |
| Current profiles | Parquet / MongoDB | Latest subscriber state plus historical metrics |
| Serving | MongoDB Atlas | Low-latency application access |
| API | JSON over HTTP | Controlled access for dashboards and clients |

---

## Repository structure

```text
subscriber-analytics-platform/
├── analytics/
│   └── subscriber_profiles.py
├── api/
│   └── app.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── dashboards/
│   └── dashboard.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   ├── DATA_MODEL.md
│   ├── DECISIONS.md
│   ├── PIPELINE.md
│   └── ROADMAP.md
├── generators/
│   └── event_generator.py
├── infrastructure/
│   ├── aws_config.py
│   └── logging_config.py
├── ingestion/
│   └── s3_loader.py
├── scripts/
│   ├── run_current_profiles.py
│   └── run_daily_pipeline.py
├── storage/
│   └── storage_manager.py
├── tests/
├── .env.example
├── .gitignore
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

Some directories contain placeholders for later milestones.

---

## Prerequisites

- Python 3.11 or later.
- Git.
- A Python virtual environment.
- AWS CLI only for S3 integration.
- An AWS named profile with access to the development bucket when cloud upload is enabled.

---

## Local setup

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

Create local configuration:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`.

---

## Running the daily pipeline

The main orchestration entry point is:

```text
scripts/run_daily_pipeline.py
```

Example:

```bash
python scripts/run_daily_pipeline.py \
  --date 2026-07-22 \
  --hours 0,1,2,3 \
  --events-per-hour 1000
```

The command:

1. Generates events for each requested hour.
2. Writes raw JSONL files.
3. Enriches the events.
4. Builds hourly subscriber activity.
5. Builds the daily subscriber activity dataset.
6. Validates record reconciliation.
7. Produces structured logs and an execution report.

Execution behavior depends on the selected rerun mode:

- `SAFE`: fail when an output already exists.
- `SKIP_EXISTING`: preserve existing outputs and skip completed stages.
- `OVERWRITE`: rebuild outputs intentionally.

See [Pipeline](docs/PIPELINE.md) for detailed processing and rerun semantics.

---

## Running tests

```bash
pytest
```

Tests should run before every commit that changes pipeline behavior, schemas, storage paths, validation rules, or orchestration.

---

## Configuration

General application configuration is centralized in:

```text
config/settings.py
```

AWS-specific configuration remains in:

```text
infrastructure/aws_config.py
```

Sensitive or environment-specific values belong in `.env` and must never be committed.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — components, boundaries, layers, and target architecture.
- [Data model](docs/DATA_MODEL.md) — raw event contract and curated datasets.
- [Pipeline](docs/PIPELINE.md) — stage-by-stage processing, validation, and rerun behavior.
- [Architecture decisions](docs/DECISIONS.md) — rationale behind major design choices.
- [Roadmap](docs/ROADMAP.md) — versions, milestones, and planned capabilities.
- [Contributing](docs/CONTRIBUTING.md) — development workflow and engineering standards.

---

## Versioning

The project follows semantic versioning:

```text
MAJOR.MINOR.PATCH
```

- `MAJOR`: incompatible platform-level changes or the first stable release.
- `MINOR`: a new architectural capability or end-to-end feature.
- `PATCH`: reliability improvements, fixes, tests, documentation, and non-breaking refinements.

Existing Git tags are immutable and are never reused.

---

## Security principles

- No credentials are stored in the repository.
- AWS access uses named profiles or role-based authentication.
- S3 buckets remain private.
- Public access blocking is enabled.
- The generated telecom data is fictional.
- Logs and reports must not contain secrets.
- MongoDB credentials will be supplied through environment variables or a secret manager.

---

## Project status

Release `v0.2.3` represents the reliable batch pipeline foundation:

```text
Raw JSONL
    ↓
Enriched Parquet
    ↓
Hourly Curated Parquet
    ↓
Daily Curated Parquet
    ↓
Current Subscriber Profiles
```

The next architectural milestone extends the platform into a serving system:

```text
Current Subscriber Profiles
    ↓
MongoDB Atlas
    ↓
FastAPI
    ↓
Dashboard
```

See [Roadmap](docs/ROADMAP.md) for the delivery sequence.

---

## License

A license has not yet been selected. Before external reuse or contributions are encouraged, the repository should include an explicit license such as MIT or Apache 2.0.
