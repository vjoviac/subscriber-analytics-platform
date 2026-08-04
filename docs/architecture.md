# Subscriber Analytics Platform — Architecture

## 1. Purpose

Subscriber Analytics Platform is a modular telecommunications data platform designed to demonstrate how subscriber events move from generation and ingestion to analytics and application consumption.

The architecture supports two goals:

1. Build a reliable pipeline that produces trustworthy data products.
2. Demonstrate solution architecture decisions across data engineering, cloud storage, serving, APIs, observability, and analytics.

The platform currently runs as a batch pipeline with MongoDB Atlas as its
operational serving store and FastAPI as its typed operational interface.
FastAPI supports subscriber lookup and bounded subscriber listing. The target
state adds a Snowflake analytical warehouse, Apache Superset dashboards,
consumer applications, and automated deployment.

---

## 2. Scope

### In scope

- Synthetic telecom event generation.
- File-based batch ingestion.
- Immutable raw storage.
- Reference-data enrichment.
- Hourly and daily subscriber aggregation.
- Current subscriber profile materialization.
- Object storage integration.
- MongoDB Atlas serving.
- FastAPI exposure.
- Operational application consumption.
- Apache Superset analytical dashboards.
- Data quality validation.
- Structured logging and execution reporting.
- Snowflake integration.
- A future streaming extension.

### Out of scope for the current phase

- Real subscriber data.
- Real-time network control.
- Production subscriber identity management.
- Regulatory reporting.
- Personally identifiable information.
- Carrier-grade availability guarantees.
- Multi-region disaster recovery.
- Full enterprise IAM federation.
- Production machine-learning models.

---

## 3. Architectural principles

### 3.1 Layered data architecture

Each layer has one responsibility:

- **Raw:** preserve the original event.
- **Enriched:** attach reference data and normalize fields.
- **Curated:** create stable analytical data products.
- **Serving:** provide low-latency, application-oriented access.
- **API:** enforce a controlled access contract.
- **Presentation:** expose operational insights.

### 3.2 Immutable raw data

Raw events are not modified after publication. This supports replay, debugging, traceability, and reprocessing after logic changes.

### 3.3 Separation of storage and compute

Transformation logic is not tied to a single execution engine. Local execution can later be replaced by managed services while preserving layer contracts.

### 3.4 Idempotent processing

A stage should create a valid output, intentionally skip it, intentionally overwrite it, or fail without leaving a misleading partial result.

### 3.5 Atomic publication

Authoritative datasets should be written to a temporary path and then moved to their final path so consumers never see incomplete files.

### 3.6 Observable execution

Every run should answer:

- What ran?
- For which date and hours?
- Which stages were created, skipped, overwritten, or failed?
- How many records entered and left each stage?
- Did validation pass?
- Why did a run fail?

### 3.7 Explicit contracts

Schemas, required fields, partitioning, grain, and output paths are contracts. Silent schema drift is not accepted.

### 3.8 Incremental evolution

Each architectural capability is implemented and validated independently before orchestration integration.

---

## 4. Current-state architecture

```text
Event Generator
      ↓
Raw Storage — JSONL
      ↓
Enrichment — Parquet
      ↓
Hourly Subscriber Activity
      ↓
Daily Subscriber Activity
      ↓
Raw / Hourly / Daily Validation
      ↓
Build and Validate Current Subscriber Profiles
      ↓
Atomic Snapshot Publication
      ↓
Validate and Transform Profiles
      ↓
Idempotent Bulk Upsert
      ↓
MongoDB Atlas
      ↓
FastAPI
      ├── GET /health
      ├── GET /ready
      └── GET /subscribers/{subscriber_id}

Cross-cutting capabilities:
- centralized configuration;
- structured logging;
- execution reports;
- rerun controls;
- unit tests;
- S3 upload support;
- atomic snapshot publication;
- environment-based MongoDB configuration;
- unique serving key and post-write validation;
- typed operational API models and deterministic error responses.
```

---

## 5. Target architecture

```text
Reference Catalogs
      │
      ▼
Event Generator
      ↓
Raw Layer — JSONL — Local / Amazon S3
      ↓
Enrichment Layer — Parquet
      ↓
Curated Layer — Hourly and Daily
      ├──────────────────────────────┐
      ▼                              ▼
Current Subscriber Profiles         Amazon S3
      ↓                              ↓
MongoDB Atlas                        Snowflake
      ↓                              ↓
FastAPI                              Apache Superset
      ↓                              ↓
Consumer Applications               Analytical Insights
```

---

## 6. Component responsibilities

### 6.1 Event generator

**Location:** `generators/`

Responsibilities:

- produce realistic telecom events;
- generate unique event identifiers;
- generate UTC timestamps;
- select valid catalog values;
- enforce device and technology compatibility;
- create session metrics;
- support injected processing time.

The generator does not persist, enrich, aggregate, or upload data.

### 6.2 Catalogs and reference data

Reference data includes:

- subscriber plans;
- TAC-based device models;
- application names and categories;
- locations and cells;
- supported network technologies.

Catalogs enrich events and should be independently maintainable.

### 6.3 Raw storage

**Format:** JSONL

**Partitioning:**

```text
data/raw/year=YYYY/month=MM/day=DD/hour=HH/
```

Responsibilities:

- preserve source events;
- enable replay;
- support line-level inspection;
- isolate hourly processing units.

Raw data is generated and excluded from Git.

### 6.4 Enrichment

**Format:** Parquet

**Partitioning:**

```text
data/enriched/year=YYYY/month=MM/day=DD/hour=HH/
```

Responsibilities:

- validate raw fields;
- join reference data;
- normalize types;
- derive analytical columns;
- preserve event-level grain;
- produce typed Parquet output.

Enrichment must not aggregate events.

### 6.5 Hourly curated data

**Dataset:** `subscriber_activity_hourly`

Responsibilities:

- aggregate by subscriber and hour;
- calculate event counts and traffic volumes;
- select latest dimensional values within the hour;
- preserve sums and sample counts for quality metrics;
- provide stable daily-aggregation input.

### 6.6 Daily curated data

**Dataset:** `subscriber_activity_daily`

Responsibilities:

- combine hourly partitions for one day;
- preserve latest daily subscriber state;
- accumulate daily usage;
- preserve weighted-average components;
- reject duplicate subscriber windows.

### 6.7 Current subscriber profiles

**Dataset:** `subscriber_profiles_current`

Path:

```text
data/curated/subscriber_profiles_current/
└── subscriber_profiles_current.parquet
```

Responsibilities:

- read all daily partitions;
- produce one row per subscriber;
- select the latest dimensional state;
- accumulate historical metrics;
- calculate weighted lifetime quality metrics;
- publish atomically;
- provide MongoDB synchronization input.

The snapshot is not date-partitioned because it represents current state.

The implementation discovers the complete daily history, validates its contract and timestamps, rejects duplicate subscriber windows, selects the latest state deterministically, calculates lifetime metrics, reconciles the result, and publishes the snapshot atomically. It can run independently or as the final data-product stage of the daily orchestrator.

### 6.8 MongoDB Atlas

MongoDB is the operational serving store.

Responsibilities:

- provide low-latency profile retrieval;
- support document-oriented profiles;
- enforce one document per top-level `subscriber_id`;
- use the unique `uq_subscriber_id` index;
- receive validated unordered bulk upserts from the Parquet snapshot;
- report and validate synchronization outcomes;
- decouple API access from Parquet scans.

MongoDB is not the historical system of record.

The implemented database and collection are:

```text
subscriber_analytics.subscriber_profiles
```

MongoDB generates each document `_id` as an `ObjectId`. The stable business key
is the top-level `subscriber_id`, which is both the upsert filter and the unique
indexed field. Synchronization does not delete documents that are absent from
the current source snapshot.

### 6.9 FastAPI

Responsibilities:

- expose profile endpoints;
- validate request parameters;
- serialize stable response models;
- isolate clients from MongoDB implementation details;
- provide health, readiness, pagination, and OpenAPI documentation.

### 6.10 Operational consumer applications

Responsibilities:

- consume the API;
- display or integrate current subscriber profiles;
- demonstrate end-to-end consumption;
- avoid direct database credentials.

### 6.11 Snowflake analytical warehouse

Responsibilities:

- consume curated Parquet history from private Amazon S3 storage;
- provide SQL access to historical and aggregated datasets;
- isolate analytical workloads from MongoDB operational serving;
- support governed schemas, transformations, and query workloads;
- preserve Parquet in S3 as the canonical analytical output.

The first Snowflake increment should use an external stage and controlled batch
loading. Snowpipe, dynamic tables, and dbt remain optional later extensions
that require explicit use cases.

### 6.12 Apache Superset

Responsibilities:

- query Snowflake through a controlled analytical connection;
- display historical trends, KPIs, and aggregated insights;
- support interactive exploration without querying MongoDB;
- avoid embedding database credentials in public client code.

---

## 7. Storage architecture

### 7.1 Local layout

```text
data/
├── raw/
├── enriched/
└── curated/
    ├── subscriber_activity_hourly/
    ├── subscriber_activity_daily/
    └── subscriber_profiles_current/
```

### 7.2 Cloud layout

```text
s3://<bucket>/
├── raw/
│   └── year=YYYY/month=MM/day=DD/hour=HH/
├── enriched/
│   └── year=YYYY/month=MM/day=DD/hour=HH/
└── curated/
    ├── subscriber_activity_hourly/
    ├── subscriber_activity_daily/
    └── subscriber_profiles_current/
```

### 7.3 File-format strategy

| Layer | Format | Rationale |
|---|---|---|
| Raw | JSONL | Human-readable, event-oriented, replay-friendly |
| Enriched | Parquet | Typed, compressed, analytical |
| Curated | Parquet | Efficient scans and cloud SQL compatibility |
| Serving | BSON documents | Low-latency document retrieval |

### 7.4 Partitioning strategy

- Raw and enriched: year, month, day, hour.
- Hourly curated: year, month, day, hour.
- Daily curated: year, month, day.
- Current profiles: no date partition.

Excessive partitioning is avoided to reduce small-file and metadata overhead.

---

## 8. Data flow and consistency

```text
Raw event
    ↓ one-to-one
Enriched event
    ↓ many-to-one by subscriber and hour
Hourly activity
    ↓ many-to-one by subscriber and day
Daily activity
    ↓ many-to-one across days
Current profile
```

Primary reconciliation invariant:

```text
raw event count
=
sum(hourly event_count)
=
sum(daily event_count)
```

The pipeline also preserves quality metric sums and sample counts so higher-level averages remain mathematically correct.

---

## 9. Execution architecture

The daily orchestrator runs:

```text
For each requested hour:
    generate
    write raw
    enrich
    aggregate hourly

After all requested hours:
    aggregate daily
    validate raw, hourly, and daily counts
    build and validate current profiles
    atomically publish the current-profile snapshot
    publish execution report
```

The orchestrator coordinates stages but does not duplicate their transformation logic.

---

## 10. Rerun model

### SAFE

Fails when an output already exists. Best for production-like protection.

### SKIP_EXISTING

Reuses completed outputs and continues with missing stages. Best for recovery and iterative development.

### OVERWRITE

Intentionally replaces outputs. Best after logic or schema changes.

Every output-producing stage must apply the selected mode consistently.

---

## 11. Observability

### Structured logging

Recommended context:

- run identifier;
- processing date and hour;
- pipeline stage;
- execution mode;
- input and output paths;
- row counts;
- elapsed time;
- outcome.

### Execution reports

A run report should contain:

- parameters;
- start and finish times;
- stage outcomes;
- created, skipped, and overwritten files;
- raw, hourly, and daily counts;
- current-profile output path and subscriber count;
- validation result;
- error details.

### Failure semantics

A failed run must:

- return a non-zero exit status;
- identify the failing stage;
- preserve exception context;
- avoid replacing a valid output with a partial file;
- never produce a misleading success report.

---

## 12. Security architecture

### Current controls

- synthetic data only;
- private S3 bucket;
- S3 public access blocking;
- project-scoped IAM permissions;
- AWS named profile instead of root access;
- `.env` excluded from Git;
- no secrets in source code;
- no generated data in Git.
- MongoDB network restrictions;
- MongoDB database-user authentication;
- environment-based MongoDB secrets;
- explicit MongoDB connection and server-selection timeouts;
- unique subscriber index.

### Planned controls

- separate application and administrative users where deployment requires them;
- managed secrets for deployed environments;
- API validation and rate limits;
- least-privilege deployment roles;
- dependency scanning;
- safe logs without credentials.

---

## 13. Scalability considerations

The current implementation favors clarity. It can evolve by:

- replacing local files with S3;
- replacing in-process transformations with a distributed execution engine;
- parallelizing independent hourly partitions;
- compacting small files;
- loading curated history into Snowflake;
- scaling Snowflake compute independently for analytical workloads;
- using bulk writes for MongoDB;
- introducing incremental profile updates when history becomes large.

Layer boundaries and data contracts should remain stable even when execution technology changes.

---

## 14. Reliability considerations

- Validate required inputs and columns.
- Reject duplicate aggregate keys.
- Validate timestamps and partitions.
- Protect existing outputs through rerun modes.
- Publish current profiles atomically.
- Test first run, skip, overwrite, and failure cases.
- Preserve raw data for replay.

---

## 15. Deployment evolution

### Stage 1 — Local batch platform

Generator, local storage, Python orchestration, tests, logs, and reports.

### Stage 2 — Cloud object storage

S3 upload, environment configuration, and least-privilege IAM.

### Stage 3 — Operational serving

MongoDB Atlas synchronization is implemented using the completed
current-profile snapshot. FastAPI liveness, readiness, and subscriber lookup
are implemented; listing and consumer applications remain planned.

### Stage 4 — Cloud analytics

Snowflake loading, analytical models, reconciled SQL examples, and Apache
Superset dashboards.

### Stage 5 — Managed execution

Containers, scheduling, centralized logs, CI/CD, infrastructure as code, and optional streaming.

---

## 16. Architectural boundaries

- Generation does not upload directly to S3.
- Storage code does not implement business aggregation.
- Analytics code does not contain credentials.
- API code does not read raw files.
- Operational consumer applications use FastAPI and do not connect directly to MongoDB.
- Apache Superset connects to Snowflake and does not use MongoDB or FastAPI as
  an analytical query engine.
- Snowflake does not replace the canonical Parquet history in Amazon S3.
- MongoDB does not replace Parquet history.
- The orchestrator coordinates but does not duplicate transformations.
- Configuration modules do not perform pipeline work.

---

## 17. Related documentation

- [Data model](DATA_MODEL.md)
- [Pipeline](PIPELINE.md)
- [Architecture decisions](DECISIONS.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
