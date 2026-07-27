# Subscriber Analytics Platform — Roadmap

## 1. Purpose

This roadmap describes the evolution of Subscriber Analytics Platform from a local synthetic-event pipeline into an end-to-end data platform with operational serving, APIs, dashboards, and cloud analytics.

The roadmap is directional. Scope may move between patch and minor releases when implementation reveals new dependencies. Existing Git tags remain immutable.

---

## 2. Release strategy

The project uses semantic versioning:

```text
MAJOR.MINOR.PATCH
```

### Patch release

Used for non-breaking improvements:

- fixes;
- tests;
- validation;
- logging;
- reports;
- documentation;
- non-breaking refactoring.

### Minor release

Used for a meaningful new architectural capability:

- a new curated data product;
- serving database integration;
- public API;
- dashboard;
- cloud analytical query layer.

### Major release

`v1.0.0` will represent the first stable, reproducible, end-to-end platform release.

---

## 3. Current state

The current platform supports:

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
```

Operational capabilities:

- daily orchestration;
- centralized settings;
- structured logging;
- execution reports;
- validation;
- safe rerun modes;
- unit tests;
- S3 upload integration;
- current-profile validation and reconciliation;
- atomic current-profile publication.
- secure MongoDB Atlas configuration;
- validated Parquet-to-BSON conversion;
- unique subscriber serving index;
- idempotent bulk upserts;
- post-write validation and synchronization reports.

The latest immutable release tag remains `v0.2.3`. MongoDB Atlas synchronization
is complete and the FastAPI milestone is in progress. Its first increment adds
a typed liveness endpoint without introducing a MongoDB runtime dependency.

---

## 4. Completed milestones

### v0.1.x — Event generation and raw ingestion

**Status:** Completed

Capabilities:

- initial repository structure;
- synthetic event generator;
- subscriber, device, application, location, and network catalogs;
- E.164-style synthetic MSISDN generation;
- TAC-based device modeling;
- raw JSONL output;
- partitioned local storage;
- initial unit tests;
- Git hygiene and generated-data exclusions.

### v0.2.0 — Enrichment and curated pipeline foundation

**Status:** Existing tag

Capabilities associated with the release line include:

- event enrichment;
- Parquet output;
- S3 integration;
- hourly subscriber activity;
- daily subscriber activity;
- modular analytics functions.

The exact scope of `v0.2.0` is the commit referenced by that tag. The tag must not be moved.

### v0.2.2 — Reliability, orchestration, and observability

**Status:** Existing tag

Capabilities:

- daily orchestration;
- injected processing time;
- SAFE, SKIP_EXISTING, and OVERWRITE modes;
- centralized configuration;
- structured logs;
- execution reports;
- raw-hourly-daily reconciliation;
- improved error handling;
- expanded tests.

Exit criteria:

- all tests pass;
- documentation reflects actual behavior;
- work is committed;
- a patch tag may be created at a stable checkpoint.

### v0.2.3 — Current subscriber profiles

**Status:** Existing tag

Capabilities:

- discovery and validation of all daily activity files;
- required-column and timestamp contracts;
- duplicate daily-window rejection;
- deterministic latest-state selection;
- historical coverage and lifetime usage metrics;
- weighted lifetime quality metrics with null zero-sample averages;
- `profile_version` and UTC `profile_updated_at`;
- one row per subscriber;
- daily-to-profile reconciliation;
- independent command-line rebuild;
- atomic Parquet publication;
- daily-pipeline orchestration and execution-report integration.

Exit criteria:

- all automated tests pass;
- standalone and orchestrated builds succeed;
- repeated builds replace the snapshot safely;
- documentation reflects actual behavior;
- release is tagged as `v0.2.3`.

---

## 5. Completed milestone — MongoDB Atlas

**Status:** Completed after `v0.2.3`.

### Objective

Synchronize the current subscriber profile snapshot to MongoDB Atlas as the operational serving store.

### Input

```text
data/curated/subscriber_profiles_current/
└── subscriber_profiles_current.parquet
```

### Deliverables

- secure environment-based connection and explicit timeouts;
- `subscriber_analytics.subscriber_profiles`;
- MongoDB-generated `_id` and top-level `subscriber_id`;
- unique `uq_subscriber_id` index;
- validation of the 29-column current snapshot;
- BSON-safe nested document conversion;
- unordered bulk upserts by `subscriber_id`;
- source, matched, modified, upserted, failed, and validated counts;
- preservation of profile version and update timestamps;
- no implicit deletion of unobserved profiles.

Repeated synchronization of the same snapshot must not create duplicates.

### Output

```text
MongoDB Atlas
└── subscriber_analytics
    └── subscriber_profiles
```

### Non-goals

- FastAPI;
- dashboard;
- top application;
- historical Parquet replacement;
- incremental profile computation.

### Exit criteria

- secure environment-based connectivity;
- a unique subscriber key prevents duplicates;
- bulk upserts are idempotent;
- repeated synchronization does not create additional documents;
- synchronization reports inserted, matched, modified, and failed counts;
- existing profiles are not deleted implicitly;
- the full automated suite passes;
- the deployed Atlas collection is validated manually.

The milestone closed with 95 passing automated tests and an end-to-end
verification using two subscriber documents. A second unchanged synchronization
produced no duplicates.

The profile activity-date contract was also corrected so
`last_activity_at = max(window_start)`. Daily `window_end` remains exclusive.

---

## 5.1 Next milestone — FastAPI

**Status:** In progress.

### Objective

Expose MongoDB-backed subscriber profiles through a typed and tested HTTP API.

### Initial scope

- MongoDB client lifecycle;
- health and readiness;
- subscriber lookup by `subscriber_id`;
- stable response model;
- error handling;
- automated tests.

### Completed first increment

- FastAPI application foundation;
- typed `GET /health` response model;
- liveness behavior independent of MongoDB;
- OpenAPI endpoint documentation;
- automated endpoint and schema tests;
- local development-server instructions;
- 97 passing automated tests.

### Next increment

- application-managed MongoDB client lifecycle;
- `GET /ready` dependency readiness check;
- deterministic readiness failure response;
- automated tests without requiring Atlas connectivity.

### Non-goals for the first increment

- dashboard implementation;
- direct Parquet reads from the API;
- broad analytical endpoints without defined requirements.

---

## 6. v0.3.0 — Serving layer and application path

### Objective

Transform the project from a batch pipeline into an end-to-end platform that exposes subscriber insights to an application.

### Required capabilities

#### Current subscriber profiles

- finalized snapshot;
- documented schema;
- reliable rebuild process.

#### MongoDB Atlas

- ✅ secure cluster configuration;
- ✅ connection string through environment variables;
- ✅ database and collection design;
- ✅ unique subscriber key;
- ✅ bulk upsert synchronization;
- ✅ synchronization report and post-write validation;
- ✅ automated tests;
- ⏳ additional query-driven indexes after FastAPI access patterns are defined.

#### FastAPI

- configuration;
- database connection lifecycle;
- typed Pydantic models;
- health and readiness endpoints;
- subscriber lookup;
- subscriber listing with pagination;
- selected filters;
- error handling;
- OpenAPI documentation;
- tests.

#### Dashboard

- API-based data access;
- platform overview;
- subscriber profile lookup;
- usage and quality metrics;
- filters;
- loading and error states;
- demonstration instructions or screenshots.

### Exit criteria

An evaluator can:

1. inspect or run the batch pipeline;
2. build current profiles;
3. load MongoDB;
4. start FastAPI;
5. open the dashboard;
6. retrieve and visualize a subscriber profile.

### Release narrative

```text
Subscriber Analytics Platform v0.3.0 adds an operational serving
layer and exposes curated subscriber insights through MongoDB Atlas,
FastAPI, and a dashboard.
```

---

## 7. v0.4.0 — AWS analytical query layer

### Objective

Provide serverless SQL access to curated datasets in S3.

### Deliverables

- standardized S3 prefixes;
- curated dataset uploads;
- Glue database;
- Glue tables or crawlers;
- verified Parquet schemas;
- partition registration;
- Athena workgroup;
- cost controls;
- example SQL;
- security documentation;
- analytical use cases.

### Candidate queries

- active subscribers by day;
- traffic by city;
- technology adoption;
- device vendor distribution;
- latency by technology;
- packet loss by location;
- heavy-usage subscribers;
- plan-level comparisons.

### Exit criteria

- Athena queries curated data;
- partition pruning is demonstrated;
- results reconcile with local outputs;
- no raw public access;
- SQL examples are committed.

---

## 8. v0.5.0 — Deployment, automation, and CI/CD

### Objective

Make the platform reproducible beyond the developer workstation.

### Candidate deliverables

- Dockerfiles;
- Docker Compose where appropriate;
- dependency locking;
- GitHub Actions for lint, tests, build, and security checks;
- environment-specific configuration;
- API and dashboard deployment;
- scheduled pipeline execution;
- centralized logs;
- release workflow;
- infrastructure as code.

Infrastructure-as-code candidates:

- Terraform;
- AWS CDK;
- CloudFormation.

Select one based on the learning objective.

---

## 9. v0.6.0 — Data quality and governance

### Objective

Introduce formal quality checks and metadata practices.

### Candidate deliverables

- schema versioning;
- freshness checks;
- completeness checks;
- uniqueness checks;
- accepted-value checks;
- lineage documentation;
- ownership;
- retention rules;
- rejected-record handling;
- catalog descriptions;
- quality results in reports.

A framework such as Great Expectations or Soda should be adopted only when requirements justify it.

---

## 10. v0.7.0 — Streaming extension

### Objective

Add near-real-time ingestion without replacing the batch architecture.

### Candidate architecture

```text
Event Generator
    ↓
Kafka or Amazon Kinesis
    ↓
Streaming Processor
    ↓
Raw Object Storage
    ↓
Near-real-time Aggregates
    ↓
MongoDB / API / Dashboard
```

### Candidate deliverables

- streaming event schema;
- producer;
- topic or stream design;
- partition key strategy;
- consumer;
- checkpointing;
- replay behavior;
- dead-letter handling;
- latency metrics;
- batch-versus-streaming comparison.

The streaming path must demonstrate a real use case rather than merely adding a technology name.

---

## 11. v0.8.0 — Advanced analytics

Candidate use cases:

- subscriber segmentation;
- anomaly detection;
- quality-of-experience scoring;
- churn-risk feature preparation;
- heavy-usage pattern detection;
- network hot-spot identification;
- recommendation-ready features.

Principles:

- analytical claims must be supported by data;
- models must not be presented as production-grade without validation;
- AI-generated narratives must cite the metrics used;
- synthetic-data limitations must remain explicit.

---

## 12. v1.0.0 — Stable end-to-end platform

### Objective

Deliver a stable, documented, reproducible release suitable for portfolio demonstrations and technical walkthroughs.

### Required characteristics

- complete architecture documentation;
- stable schemas;
- end-to-end setup;
- automated tests;
- CI/CD;
- secure configuration;
- local and deployed demonstration paths;
- operational serving;
- API;
- dashboard;
- cloud analytics;
- versioned releases;
- screenshots;
- known limitations;
- explicit license.

### Suggested demonstration story

1. Explain the telecom business problem.
2. Generate events.
3. Show raw and enriched records.
4. Explain hourly and daily aggregation.
5. Show validation and reports.
6. Build current profiles.
7. Retrieve a profile through the API.
8. Show dashboard insights.
9. Run an Athena query.
10. Explain the scale-out path.

---

## 13. Backlog

Potential future items:

- profile history snapshots;
- slowly changing dimensions;
- multiple subscriber products;
- fixed-network events;
- network topology;
- geospatial analytics;
- file compaction;
- lifecycle policies;
- multi-environment accounts;
- service authentication;
- rate limiting;
- caching;
- OpenTelemetry;
- disaster recovery;
- Snowflake ingestion;
- dbt transformations;
- Airflow orchestration;
- converged mobile and fixed analytics.

Backlog items are not commitments.

---

## 14. Documentation maintenance

Update the roadmap when:

- a milestone begins;
- a deliverable changes;
- a release is tagged;
- a dependency changes;
- scope is deferred;
- a decision is superseded.

The roadmap must describe reality, not planned work presented as completed.

---

## 15. Related documentation

- [Architecture](ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Pipeline](PIPELINE.md)
- [Architecture decisions](DECISIONS.md)
- [Contributing](CONTRIBUTING.md)
