# Subscriber Analytics Platform

A portfolio-grade telecommunications data platform that simulates subscriber network events, enriches them with reference data, produces analytics-ready datasets, and prepares those datasets for operational and analytical consumption.

The project demonstrates practical skills in data engineering, solution architecture, cloud integration, observability, API design, and analytics delivery.

> **Current release:** `v0.2.3`<br>
> **Current focus:** FastAPI serving release checkpoint preparation.<br>
> **Current API increment:** bounded subscriber listing completed and validated against MongoDB Atlas.

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
- Secure MongoDB Atlas configuration through `.env`.
- Validated conversion of the 29-column current-profile snapshot to BSON documents.
- Unique `subscriber_id` serving index.
- Unordered idempotent bulk upserts.
- Post-write synchronization validation and reporting.
- FastAPI application foundation.
- Typed `GET /health` liveness endpoint with OpenAPI documentation.
- Application-managed MongoDB client lifecycle.
- Typed `GET /ready` endpoint with Atlas connectivity validation.
- Deterministic `503 Service Unavailable` readiness response.
- MongoDB-independent API tests using mocked clients.
- Stable nested subscriber profile response model.
- `GET /subscribers/{subscriber_id}` lookup endpoint.
- Deterministic `404 Not Found` and `503 Service Unavailable` responses.
- MongoDB `_id` exclusion from the public API contract.
- UTC-aware MongoDB reads and API timestamps.
- `GET /subscribers` listing endpoint.
- Bounded page size and deterministic `subscriber_id` ordering.
- Pagination metadata for operational consumers.
- Successful manual pagination validation against MongoDB Atlas with two profiles.

### Planned

- Selected operational filters after concrete consumer requirements are defined.
- Snowflake analytical warehouse consuming curated Parquet history from Amazon S3.
- Apache Superset dashboards querying Snowflake.
- Consumer applications using the operational FastAPI contract.
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
Daily Curated Dataset ──────────────→ Amazon S3
      ↓                                  ↓
Current Subscriber Profiles           Snowflake
      ↓                                  ↓
MongoDB Atlas                        Apache Superset
      ↓                                  ↓
FastAPI                           Analytical Insights
      ↓
Consumer Applications
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
| API | JSON over HTTP | Controlled access for operational applications |
| Analytical warehouse | Snowflake | Historical and aggregated SQL analytics |
| Presentation | Apache Superset | Dashboards, KPIs, and data exploration |

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
│   ├── mongodb_config.py
│   └── logging_config.py
├── ingestion/
│   └── s3_loader.py
├── scripts/
│   ├── run_current_profiles.py
│   ├── run_daily_pipeline.py
│   └── sync_mongodb_profiles.py
├── serving/
│   └── mongodb_profiles.py
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
- A MongoDB Atlas cluster and database user for serving synchronization.
- A network access rule that allows the development client to reach Atlas.

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

For MongoDB synchronization, configure:

```dotenv
MONGODB_URI=
MONGODB_DATABASE=subscriber_analytics
MONGODB_COLLECTION=subscriber_profiles
MONGODB_TIMEOUT_MS=10000
```

Keep the connection string only in the local `.env` file.

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

The MongoDB milestone closed with:

```text
95 passed
```

The current development suite extends to:

```text
117 passed
```

---

## Running the FastAPI service

Start the local development server from the repository root:

```bash
python -m uvicorn api.app:app --reload
```

Retrieve a subscriber profile:

```powershell
Invoke-RestMethod `
    http://127.0.0.1:8000/subscribers/SUB_000001
```

The response contains the nested current subscriber profile, uses UTC
timestamps, and does not expose MongoDB `_id`.

List subscriber profiles with bounded pagination:

```powershell
Invoke-RestMethod `
    "http://127.0.0.1:8000/subscribers?page=1&page_size=20"
```

The listing is ordered by `subscriber_id`, accepts page sizes from 1 through
100, and includes the current page, page size, total profile count, and total
page count.

Check API liveness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected JSON response:

```json
{
  "status": "healthy"
}
```

Check MongoDB readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Expected response when MongoDB is available:

```json
{
  "status": "ready"
}
```

When MongoDB is not configured or unavailable, the endpoint returns
`503 Service Unavailable`:

```json
{
  "status": "not_ready",
  "detail": "MongoDB is unavailable."
}
```

Interactive OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

`GET /health` checks only whether the API process is running. `GET /ready`
checks MongoDB connectivity using the application-managed shared client.
A MongoDB failure does not prevent the liveness endpoint from responding.

---

## Synchronizing current profiles to MongoDB Atlas

Build or refresh the current snapshot first:

```bash
python -m scripts.run_current_profiles
```

Then synchronize it:

```bash
python -m scripts.sync_mongodb_profiles
```

The command:

1. validates `subscriber_profiles_current.parquet`;
2. verifies the Atlas connection;
3. obtains `subscriber_analytics.subscriber_profiles`;
4. ensures the unique `uq_subscriber_id` index;
5. converts profile rows to nested BSON-safe documents;
6. performs unordered bulk upserts by `subscriber_id`;
7. validates that every source subscriber exists in the collection;
8. prints source, matched, modified, upserted, failed, and validated counts.

Running the command again with an unchanged snapshot does not create duplicate
documents and should produce zero modifications and zero upserts.

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
- MongoDB credentials are supplied through environment variables and are never committed.
- Atlas network access is restricted to explicitly authorized client addresses.

---

## Project status

Release `v0.2.3` remains the latest immutable tag. Current development adds the
MongoDB Atlas serving synchronization and the initial operational FastAPI
contract to that reliable batch foundation:

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
    ↓
MongoDB Atlas
    ↓
FastAPI
```

FastAPI now supports bounded subscriber listing for future operational
consumer applications. Selected filters remain deferred until their access
patterns are defined. The listing was validated against MongoDB Atlas with
deterministic ordering across two pages and an empty result beyond the final
page. The target consumption architecture separates two workloads:

```text
Operational: MongoDB Atlas → FastAPI → Consumer Applications
Analytical:  Amazon S3 → Snowflake → Apache Superset
```

See [Roadmap](docs/ROADMAP.md) for the delivery sequence.

---

## License

A license has not yet been selected. Before external reuse or contributions are encouraged, the repository should include an explicit license such as MIT or Apache 2.0.
