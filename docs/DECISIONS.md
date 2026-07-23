# Subscriber Analytics Platform — Architecture Decisions

## 1. Purpose

This document records the most important architectural and engineering decisions made for Subscriber Analytics Platform.

Each decision includes context, decision, rationale, consequences, and status.

Status values:

- **Accepted**
- **Proposed**
- **Superseded**
- **Deprecated**

---

## ADR-001 — Use a layered data architecture

**Status:** Accepted

### Context

The platform must support replay, enrichment, analytics, operational serving, and future cloud services without coupling every consumer to raw events.

### Decision

Use explicit layers:

```text
Raw
→ Enriched
→ Curated
→ Current Profiles
→ Serving
→ API
→ Dashboard
```

### Rationale

- clear responsibilities;
- replay and reprocessing;
- separation of current state from event history;
- workload-appropriate storage;
- easy architectural explanation.

### Consequences

- more datasets and interfaces;
- explicit contracts and reconciliation are required.

---

## ADR-002 — Store raw events as JSON Lines

**Status:** Accepted

### Decision

Store one JSON object per line in `.jsonl` files.

### Rationale

- human-readable;
- streaming-friendly;
- easy line-by-line processing;
- natural fit for event data.

### Consequences

- less efficient than Parquet for analytics;
- schema is not enforced by the format.

---

## ADR-003 — Use Parquet from the enriched layer onward

**Status:** Accepted

### Decision

Write enriched and curated datasets as Parquet.

### Rationale

- typed columnar schema;
- compression;
- efficient analytical projection;
- compatibility with pandas, Spark, Athena, and Snowflake.

### Consequences

- Parquet engine dependencies;
- stronger schema discipline.

---

## ADR-004 — Partition by UTC processing time

**Status:** Accepted

### Decision

Use:

```text
year=YYYY/month=MM/day=DD/hour=HH
```

for hourly layers and omit `hour` for daily data.

### Rationale

- unambiguous windows;
- reproducible backfills;
- cloud data-lake compatibility;
- partition pruning.

### Consequences

- dashboards may convert to local time;
- users must understand UTC semantics.

---

## ADR-005 — Keep raw data immutable

**Status:** Accepted

### Decision

Raw data is preserved as the replay source. Corrections rebuild downstream layers rather than altering history silently.

### Rationale

- auditability;
- reproducibility;
- root-cause analysis.

### Consequences

- storage grows;
- retention policies will eventually be needed.

---

## ADR-006 — Use a canonical subscriber identifier

**Status:** Accepted

### Decision

Use `subscriber_id`, initially derived from synthetic IMSI, as the aggregation and serving key.

### Rationale

- stable key;
- separates identity from presentation fields;
- supports future evolution.

### Consequences

- API consumers must distinguish subscriber ID, IMSI, and MSISDN;
- changing the key would be breaking.

---

## ADR-007 — Model device capability as the maximum supported generation

**Status:** Accepted

### Decision

Store one `device_capability` value representing the highest supported generation.

### Rationale

- simpler catalog;
- straightforward compatibility validation;
- easy maintenance.

### Consequences

- backward compatibility is assumed;
- detailed band and device exceptions are not modeled.

---

## ADR-008 — Separate generation, storage, enrichment, analytics, and orchestration

**Status:** Accepted

### Decision

Keep components in separate modules and make the orchestrator coordinate them.

### Rationale

- testability;
- reuse;
- cloud migration flexibility;
- failure isolation.

### Consequences

- more interfaces;
- public function contracts must remain stable.

---

## ADR-009 — Centralize application settings

**Status:** Accepted

### Decision

Use:

```text
config/settings.py
```

for application settings and:

```text
infrastructure/aws_config.py
```

for AWS-specific configuration.

### Rationale

- single source of truth;
- cleaner testing;
- separation of general and cloud-specific configuration.

### Consequences

- modules must not define competing settings;
- import-time side effects must be avoided.

---

## ADR-010 — Use explicit rerun modes

**Status:** Accepted

### Decision

Support:

```text
SAFE
SKIP_EXISTING
OVERWRITE
```

### Rationale

- intentional operation;
- safe recovery;
- predictable testing;
- protection against accidental data loss.

### Consequences

- every stage must honor the selected mode;
- reports must identify skipped and overwritten outputs.

---

## ADR-011 — Reconcile actual counts across layers

**Status:** Accepted

### Decision

Validate:

```text
actual raw event count
=
sum(hourly event_count)
=
sum(daily event_count)
```

### Rationale

- detects row loss and duplication;
- validates actual outputs rather than only configured expectations.

### Consequences

- stages must expose counts;
- reconciliation becomes release-critical.

---

## ADR-012 — Preserve sums and sample counts for quality metrics

**Status:** Accepted

### Decision

Persist latency and packet-loss sums and sample counts, then recalculate averages at higher grains.

### Rationale

- mathematically correct weighted averages;
- explicit null handling;
- supports lifetime metrics.

### Consequences

- additional columns;
- consumers must understand supporting measures.

---

## ADR-013 — Use one current-profile row per subscriber

**Status:** Accepted

### Decision

Build `subscriber_profiles_current` with exactly one row per subscriber.

### Rationale

- simple serving contract;
- fast MongoDB synchronization;
- no need to scan daily history for current state.

### Consequences

- latest-state selection must be deterministic;
- the snapshot must be rebuilt or maintained incrementally.

---

## ADR-014 — Do not date-partition the current-profile snapshot

**Status:** Accepted

### Decision

Publish one logical current snapshot:

```text
data/curated/subscriber_profiles_current/
└── subscriber_profiles_current.parquet
```

### Rationale

- one authoritative current file;
- simple synchronization;
- avoids scanning historical snapshots.

### Consequences

- atomic publication is mandatory;
- historical snapshots require a separate archive strategy.

---

## ADR-015 — Build current profiles from daily activity

**Status:** Accepted

### Decision

Read all daily activity partitions to build current profiles.

### Rationale

- avoids event-level historical scans;
- reuses validated curated data;
- preserves weighted-average components.

### Consequences

- full rebuild cost grows with history;
- an incremental approach may later be required.

---

## ADR-016 — Do not fabricate top application

**Status:** Accepted

### Decision

Exclude `top_application` from current profiles until a dedicated application-usage model exists.

### Rationale

- protects correctness;
- avoids unsupported insights;
- preserves lineage integrity.

### Consequences

- fewer application insights initially;
- future curated work is required.

---

## ADR-017 — Publish snapshots atomically

**Status:** Accepted

### Decision

Write to a temporary file and replace the final snapshot only after validation.

### Rationale

- protects readers;
- supports failure recovery;
- clear final-file semantics.

### Consequences

- temporary-file cleanup is required;
- object-store publication needs an equivalent safe pattern.

---

## ADR-018 — Implement MongoDB before Athena

**Status:** Accepted

### Decision

Use this order:

```text
Current Profiles
→ MongoDB Atlas
→ FastAPI
→ Dashboard
→ Glue and Athena
```

### Rationale

- demonstrates an end-to-end solution;
- creates visible user-facing value;
- distinguishes operational and analytical workloads.

### Consequences

- cloud SQL is deferred;
- MongoDB becomes the next external dependency.

---

## ADR-019 — Use MongoDB as a serving layer, not the historical system of record

**Status:** Accepted

### Decision

Store current profiles in MongoDB and preserve historical layers in file-based storage.

### Rationale

- workload-appropriate persistence;
- low-latency access;
- analytical flexibility.

### Consequences

- two persistence models;
- synchronization freshness must be monitored.

---

## ADR-020 — Require the dashboard to consume FastAPI

**Status:** Proposed

### Decision

The dashboard will use API endpoints instead of connecting directly to MongoDB.

### Rationale

- controlled contract;
- centralized validation and authorization;
- no database credentials in the client;
- replaceable persistence layer.

### Consequences

- API availability becomes a dependency;
- an additional service must be deployed.

---

## ADR-021 — Use AWS named profiles for local development

**Status:** Accepted

### Decision

Use AWS CLI named profiles and boto3 sessions rather than root or hard-coded credentials.

### Rationale

- no secrets in source code;
- enterprise-like workflow;
- profile-specific permissions.

### Consequences

- developers must configure a profile;
- CI/CD will use roles or another secretless mechanism.

---

## ADR-022 — Keep S3 private

**Status:** Accepted

### Decision

Use private buckets with public access blocking and ACLs disabled.

### Rationale

- least exposure;
- standard data-lake security;
- prevents accidental publication.

### Consequences

- access requires IAM permissions;
- public demos use the application layer instead of direct data links.

---

## ADR-023 — Use structured logs and execution reports

**Status:** Accepted

### Decision

Use structured logging plus a run-level report.

### Rationale

- traceability;
- machine-readable outcomes;
- easier troubleshooting;
- future centralized-log compatibility.

### Consequences

- logging context must be propagated;
- report schema should remain stable.

---

## ADR-024 — Keep the project locally executable

**Status:** Accepted

### Decision

Maintain a local execution path while cloud services are introduced.

### Rationale

- low-cost development;
- portability;
- visible transformation logic;
- easier demonstrations.

### Consequences

- local and cloud settings must stay aligned;
- cloud-only features need separate integration tests.

---

## ADR-025 — Adopt semantic versioning without moving tags

**Status:** Accepted

### Decision

Treat Git tags as immutable and increment patch or minor versions for later releases.

### Rationale

- trustworthy history;
- standard release practice;
- clear portfolio evolution.

### Consequences

- documentation must reflect the actual tagged commit;
- old tags are never reassigned.

---

## ADR-026 — Delay managed orchestration until the application path exists

**Status:** Proposed

### Decision

Prioritize current profiles, MongoDB, FastAPI, and dashboard before Step Functions, Airflow, or equivalent managed orchestration.

### Rationale

- maximizes visible end-to-end value;
- avoids complexity for its own sake;
- keeps focus on data products and consumers.

### Consequences

- orchestration remains script-based for the current phase;
- managed scheduling is deferred.

---

## Decision review process

Add an ADR when a change:

- alters a data contract;
- introduces a major technology;
- changes a layer responsibility;
- changes execution or deployment;
- creates a long-term trade-off;
- supersedes an earlier decision.

When superseding a decision:

1. mark the old ADR as `Superseded`;
2. reference the replacement;
3. retain the historical text.

---

## Related documentation

- [Architecture](ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Pipeline](PIPELINE.md)
- [Roadmap](ROADMAP.md)
