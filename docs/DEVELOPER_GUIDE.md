# DEVELOPER_GUIDE.md

# Subscriber Analytics Platform
**Developer Guide (Superset Visualization Edition)**

> **Purpose:** This document is the authoritative engineering reference for continuing the development of the Subscriber Analytics Platform. It captures the project's current state, architectural decisions, engineering conventions, and development roadmap. Read this document before implementing new features or continuing development.

# Project Snapshot

| Item | Value |
|------|-------|
| Current Version | v0.4.0 |
| Current Git Tag | v0.4.0 |
| Primary Branch | main |
| Completed Milestone | Snowflake analytical warehouse foundation released as `v0.4.0` |
| Current Development | Local Apache Superset foundation, Snowflake service identity, semantic metrics, and validation chart |
| Stable Pipeline | Raw JSONL → Enriched Parquet → Curated Hourly → Curated Daily → Current Subscriber Profiles → MongoDB Atlas → FastAPI |
| Next Deliverable | First analytical dashboard design and validation |
| Serving Path | MongoDB Atlas with FastAPI liveness, readiness, subscriber lookup, and bounded listing implemented |
| Analytical Path | Curated Parquet → Amazon S3 → Snowflake native table → analytical view implemented |
| Primary Language | Python |
| Storage Formats | JSONL, Parquet |
| Architectural Style | Layered Batch Pipeline |
| Time Standard | UTC |
| Configuration | config/settings.py |
| Logging | Structured logging + execution reports |

# 1. Project Overview

The Subscriber Analytics Platform is a portfolio project that simulates a production-grade telecommunications analytics platform. The objective is to demonstrate sound engineering and architectural practices rather than simply producing code.

Current version: **v0.4.0**

---

# 2. Current Status

## Implemented

- Event Generator
- Raw JSONL layer
- Enriched Parquet layer
- Curated Hourly aggregation
- Curated Daily aggregation
- Pipeline orchestration
- Validation and reconciliation
- Structured logging
- Execution reports
- Centralized configuration
- Unit tests
- Current subscriber profile snapshot
- Deterministic latest-state selection
- Lifetime usage and weighted quality metrics
- Atomic snapshot publication
- Current-profile orchestration integration
- Secure MongoDB Atlas configuration through environment variables
- PyMongo connection verification with explicit timeouts
- `subscriber_analytics.subscriber_profiles` serving collection
- Unique `uq_subscriber_id` index
- Validated Parquet-to-BSON profile transformation
- Unordered bulk upserts keyed by `subscriber_id`
- Post-write subscriber-count validation
- Idempotent synchronization reporting
- 95 passing automated tests at milestone completion
- FastAPI application foundation
- Typed `GET /health` liveness endpoint
- OpenAPI-documented health response
- 97 passing automated tests in current development
- Application-managed MongoDB client lifecycle
- Shared client cleanup during API shutdown
- Typed `GET /ready` readiness endpoint
- Deterministic readiness failure without credential exposure
- Mocked readiness and lifecycle tests without Atlas dependency
- 101 passing automated tests in current development
- Stable nested subscriber profile response model
- MongoDB lookup by canonical `subscriber_id`
- MongoDB `_id` exclusion through query projection and response modeling
- Deterministic subscriber `404` and service `503` responses
- UTC-aware MongoDB reads
- 107 passing automated tests in current development
- Bounded `GET /subscribers` listing endpoint
- Deterministic ascending `subscriber_id` ordering
- Page and page-size validation
- Typed pagination metadata
- Mocked subscriber-listing tests without Atlas dependency
- Successful manual subscriber-listing validation against MongoDB Atlas
- 117 passing automated tests in the v0.3.0 release
- Secure Snowflake storage integration with a dedicated AWS IAM role and External ID
- Curated daily S3 prefix restricted through allowed locations and least-privilege IAM
- External stage and logical-type-aware Parquet file format
- Native 39-column daily activity table with four required lineage fields
- Idempotent `COPY INTO` loading with `FORCE = FALSE`
- Four daily Parquet files loaded with two rows each and zero load errors
- Unchanged-file reruns processing zero files
- Dedicated `X-Small` warehouse with 60-second auto-suspend
- Monthly 10-credit resource monitor with 50%, 80%, and 100% actions
- Seven-privilege loader role without integration access or warehouse operation
- Four-privilege reader role restricted to an approved analytical view
- Secondary roles disabled during RBAC validation
- Exact local-Parquet-to-Snowflake reconciliation across 8 rows and 6,300 events
- Validated daily, geographic, technology, and plan-level SQL examples
- Versioned Snowflake setup, load, access-control, and validation scripts
- Apache Superset 6.0.0 custom lean image
- PostgreSQL 17.10 metadata service with persistent storage
- Local Docker Compose topology with health checks
- Pinned `psycopg2-binary` and `snowflake-sqlalchemy` drivers
- Passwordless Snowflake `SUPERSET_SERVICE_USER`
- Encrypted RSA key-pair authentication
- Read-only private-key mount and per-service environment isolation
- Positive analytical-view and negative curated-object RBAC validation
- Superset dataset over `ANALYTICS.SUBSCRIBER_ACTIVITY_DAILY`
- Five reusable semantic metrics with weighted quality formulas
- `Daily Subscriber KPI Validation` chart reconciled across four days

## Completed milestone

**Snowflake analytical warehouse foundation**

## Planned milestones

1. Design and validate the first analytical dashboard
2. Define the public presentation and hosting model
3. Containerization and deployment automation beyond the local Superset stack
3. Formal data quality and governance

---

# 3. Repository Structure

| Directory | Responsibility |
|-----------|----------------|
| analytics | Transformations and aggregations |
| config | Global configuration |
| generators | Event generation |
| ingestion | Data ingestion |
| storage | Persistence |
| scripts | Pipeline orchestration |
| sql/snowflake | Reproducible Snowflake setup, loading, RBAC, and validation |
| docker/superset | Local Superset image, PostgreSQL metadata service, configuration, and health checks |
| tests | Automated tests |
| docs | Documentation |

Each module owns one responsibility.

---

# 4. Architecture Overview

```text
Raw JSONL
    ↓
Enriched Parquet
    ↓
Curated Hourly
    ↓
Curated Daily ───────────────→ Amazon S3
    ↓                              ↓
Current Subscriber Profiles     Snowflake
    ↓                              ↓
MongoDB Atlas               Analytical Views
    ↓                              ↓
FastAPI                    Apache Superset
    ↓ planned                    ↓ planned
Consumer Applications      Public Dashboard
```

Design principles:

- Layered architecture
- Deterministic processing
- Incremental evolution
- Production mindset

---

# 5. Engineering Rules

## Coding

- Use type hints.
- Prefer small functions.
- No hardcoded configuration.
- Centralize settings.
- Favor readability.

## Data Engineering

- Raw is immutable.
- JSONL only in Raw.
- Parquet from Enriched onward.
- Analytical datasets are partitioned by date.
- Snapshot datasets are not partitioned.
- Every stage validates schema and reconciliation.

## Architecture

- FastAPI is the controlled interface for operational subscriber access.
- MongoDB is the serving database.
- Apache Superset queries approved Snowflake views, not MongoDB or FastAPI.
- Snowflake will serve historical and aggregated analytics without replacing
  canonical Parquet datasets in S3.
- UTC everywhere.
- One subscriber profile per subscriber.
- Atomic snapshot writes.
- Parquet remains the canonical analytical output.
- MongoDB synchronization never deletes profiles implicitly.
- `window_end` is exclusive; profile activity dates use daily `window_start`.

---

# 6. Development Workflow

Every feature follows:

1. Review architecture.
2. Implement.
3. Validate.
4. Test.
5. Update documentation.
6. Commit.
7. Tag release when appropriate.

Definition of Done:

- Code complete
- Tests pass
- Validation succeeds
- Documentation updated
- Repository clean

---

# 7. Versioning

Semantic Versioning:

- PATCH → fixes
- MINOR → compatible features
- MAJOR → breaking architecture

---

# 8. Current Roadmap

| Status | Milestone |
|--------|-----------|
| ✅ | Event Generator |
| ✅ | Raw Layer |
| ✅ | Enrichment |
| ✅ | Hourly Aggregation |
| ✅ | Daily Aggregation |
| ✅ | subscriber_profiles_current |
| ✅ | MongoDB Atlas profile synchronization |
| ✅ | FastAPI — liveness, readiness, lookup, and bounded listing implemented |
| ✅ | Snowflake analytical warehouse foundation |
| 🚧 | Apache Superset analytical visualization layer |
| ⏳ | First analytical dashboard and public delivery |
| ⏳ | Containerization and deployment automation |

---

# 9. Completed MongoDB Atlas Milestone

Goal: synchronize the current profile snapshot to MongoDB Atlas as an operational serving layer.

Input:

- subscriber_profiles_current.parquet

Output:

- `subscriber_analytics.subscriber_profiles`

Implemented behavior:

- connect through `MONGODB_URI` without committing credentials;
- use configurable database, collection, and timeout settings;
- create the unique `uq_subscriber_id` index;
- validate the 29-column Parquet snapshot before synchronization;
- convert pandas and NumPy values to BSON-safe values;
- use unordered bulk upserts filtered by `subscriber_id`;
- report source, matched, modified, upserted, failed, and validated counts;
- preserve `profile_version` and `profile_updated_at`;
- avoid deleting profiles that are absent from the source snapshot;
- close the MongoDB client on success and failure.

Repeated synchronization of the same snapshot must not create duplicates.

The implementation uses MongoDB-generated `ObjectId` values for `_id` and a
separate unique top-level `subscriber_id` business key.

## 9.1 MongoDB configuration

Copy `.env.example` to `.env` and configure:

```dotenv
MONGODB_URI=
MONGODB_DATABASE=subscriber_analytics
MONGODB_COLLECTION=subscriber_profiles
MONGODB_TIMEOUT_MS=10000
```

Never commit a populated `MONGODB_URI`.

Verify connectivity:

```bash
python -c "from infrastructure.mongodb_config import verify_mongodb_connection; verify_mongodb_connection(); print('MongoDB Atlas connection successful')"
```

Synchronize the current snapshot:

```bash
python -m scripts.sync_mongodb_profiles
```

A second synchronization of an unchanged snapshot should report matched
profiles with zero modifications and zero upserts.

## 9.2 FastAPI milestone

The FastAPI operational serving scope is complete. The implemented increments provide:

- a typed `GET /health` liveness endpoint independent of MongoDB;
- an application-managed shared MongoDB client;
- client cleanup during application shutdown;
- a typed `GET /ready` endpoint backed by a MongoDB ping;
- deterministic `503 Service Unavailable` behavior when MongoDB is unavailable.

The subscriber lookup increment adds a stable nested public response model and
`GET /subscribers/{subscriber_id}` backed by MongoDB Atlas. The endpoint
excludes MongoDB `_id`, preserves UTC timestamps, returns `404 Not Found` for
unknown subscribers, and returns `503 Service Unavailable` without exposing
internal database details.

The subscriber listing increment adds `GET /subscribers` with one-based page
numbers, page sizes bounded from 1 through 100, deterministic ascending
`subscriber_id` ordering, and typed pagination metadata. It returns an empty
item list for a valid page beyond the available profiles and preserves the
existing deterministic `503 Service Unavailable` contract.

Manual validation against MongoDB Atlas confirmed two profiles across two
one-item pages in ascending `subscriber_id` order. A third valid page returned
an empty item list with stable pagination metadata.

Selected filters remain deferred until concrete operational consumer
requirements define the access patterns and required indexes. The existing
unique `uq_subscriber_id` index supports the listing order, so this increment
does not add another index.

The analytical path loads curated Parquet history from Amazon S3 into
Snowflake. It remains separate from MongoDB Atlas and FastAPI, which serve
current subscriber profiles and operational consumers.

## 9.3 Snowflake analytical warehouse

Canonical input:

```text
s3://subscriber-analytics-platform-dev/
└── curated/subscriber_activity_daily/
    └── year=YYYY/month=MM/day=DD/subscriber_activity_daily.parquet
```

Implemented Snowflake objects:

```text
SUBSCRIBER_ANALYTICS
├── CURATED
│   ├── PARQUET_FORMAT
│   ├── SUBSCRIBER_ACTIVITY_DAILY_STAGE
│   └── SUBSCRIBER_ACTIVITY_DAILY
└── ANALYTICS
    └── SUBSCRIBER_ACTIVITY_DAILY
```

Account-level objects:

- `S3_SUBSCRIBER_ACTIVITY_DAILY_INT`;
- `SUBSCRIBER_ANALYTICS_WH`;
- `SUBSCRIBER_ANALYTICS_MONITOR`;
- `SUBSCRIBER_ANALYTICS_LOADER`;
- `SUBSCRIBER_ANALYTICS_READER`.

The native table contains the 35 Parquet fields plus:

- `source_filename`;
- `source_file_content_key`;
- `source_file_last_modified`;
- `loaded_at`.

The analytical view preserves one row per subscriber and daily window, derives
`activity_date`, and excludes IMSI, MSISDN, TAC, and cell ID. Metric sums and
sample counts remain available for correct weighted aggregation.

Execute setup scripts in order:

```text
sql/snowflake/01_foundation.sql
sql/snowflake/02_storage.sql
sql/snowflake/03_analytics.sql
sql/snowflake/04_access_control.sql
sql/snowflake/05_validation_queries.sql
```

Before `02_storage.sql`, define the AWS role ARN only as a Snowflake session
variable. Never commit the real ARN, AWS account ID, or Snowflake External ID.
Use `load_subscriber_activity_daily.sql` for controlled subsequent loads.

RBAC validation must begin with:

```sql
USE SECONDARY ROLES NONE;
```

Otherwise roles such as `ACCOUNTADMIN` or `ORGADMIN` can remain active as
secondary roles and conceal missing grants.

Validated reconciliation for four daily files:

| Metric | Value |
|---|---:|
| Files | 4 |
| Rows | 8 |
| Daily windows | 4 |
| Subscribers | 2 |
| Events | 6,300 |
| Download bytes | 117,759,989,294 |
| Upload bytes | 12,387,206,208 |
| Total bytes | 130,147,195,502 |
| Weighted average latency | 55.34 ms |
| Weighted average packet loss | 0.9031% |

Local Parquet and Snowflake results match exactly. Unchanged reruns process
zero files. Automation remains deferred; no Snowpipe, task, dynamic table, or
scheduled trigger is implemented.

Apache Superset is selected and validated locally. Public deployment remains a
separate decision under `analytics.joviac.cloud`.

## 9.4 Apache Superset analytical visualization

Implemented local topology:

```text
Browser → Apache Superset 6.0.0
              ├── PostgreSQL 17.10 metadata
              └── Snowflake ANALYTICS view
```

The custom image derives from `apache/superset:6.0.0` and installs only:

- `psycopg2-binary==2.9.12`;
- `snowflake-sqlalchemy==1.11.0`.

Docker Compose persists PostgreSQL metadata in a named volume, keeps its port
private, binds Superset only to `127.0.0.1:8088`, and validates both services
with health checks. Redis, Celery, alerts, and reports are intentionally absent.
On a new metadata volume, run `superset db upgrade`, create the local
administrator interactively with `superset fab create-admin`, and run
`superset init`. The administrator password belongs in a password manager, not
in `.env` or the repository.

Snowflake access uses `SUPERSET_SERVICE_USER`, `TYPE = SERVICE`, and encrypted
RSA key-pair authentication. The private key remains under the ignored
`docker/superset/secrets/` directory and is mounted read-only. The identity has
only `SUBSCRIBER_ANALYTICS_READER`. Tests with secondary roles disabled proved
that it can query the approved analytical view and cannot access the curated
table or external stage.

The registered Superset dataset is
`ANALYTICS.SUBSCRIBER_ACTIVITY_DAILY`. Implemented metric keys are:

- `active_subscribers`;
- `total_events`;
- `total_traffic_gib`;
- `weighted_avg_latency_ms`;
- `weighted_avg_packet_loss_pct`.

The quality metrics recompute averages from sums and sample counts. The saved
`Daily Subscriber KPI Validation` table groups by activity date and reconciles
the four implemented daily windows. The first dashboard, exports, public access,
and production hosting remain deferred to the next increment.

---

# 10. Architectural Decisions

These decisions are considered stable unless explicitly revised.

- Raw data is immutable.
- JSONL exists only in Raw.
- Enriched and Curated use Parquet.
- Pipeline stages remain isolated.
- Configuration is centralized.
- Logging is mandatory.
- Validation blocks invalid outputs.
- Generated artifacts are never committed.

---

# 11. How to Continue Development

Before writing code:

1. Read this document.
2. Check ROADMAP.md.
3. Verify the current milestone.
4. Preserve existing architecture.
5. Prefer incremental changes over redesigns.
6. Update documentation together with implementation.

---

# 12. AI Development Context

This project is intentionally documented so that an AI coding assistant can continue development with minimal onboarding.

Assume:

• Existing architecture is stable.
• Continue from the current milestone.
• Preserve documented architectural decisions.
• Prefer incremental improvements.
• Update documentation together with implementation.
• Avoid unnecessary refactoring.

This document is intentionally concise and should be updated after each completed milestone.
