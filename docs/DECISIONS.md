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
→ Operational Consumers

Curated
→ Analytical Warehouse
→ Analytical Presentation
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
- compatibility with pandas, Spark, and Snowflake.

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

**Implementation:** Completed in `v0.2.3`.

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

**Implementation:** Completed in `v0.2.3`.

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

**Implementation:** Completed in `v0.2.3`.

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

**Implementation:** Completed in `v0.2.3`.

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

**Implementation:** Completed in `v0.2.3`.

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

**Status:** Superseded by ADR-031

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

**Implementation:** Completed after `v0.2.3`.

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

**Status:** Superseded by ADR-031

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

Prioritize current profiles, MongoDB, FastAPI, Snowflake, and the selected
analytical visualization layer before Step Functions, Airflow, or equivalent
managed orchestration.

### Rationale

- maximizes visible end-to-end value;
- avoids complexity for its own sake;
- keeps focus on data products and consumers.

### Consequences

- orchestration remains script-based for the current phase;
- managed scheduling is deferred.

---

## ADR-027 — Use a separate unique subscriber business key in MongoDB

**Status:** Accepted

**Implementation:** Completed after `v0.2.3`.

### Context

MongoDB requires `_id`, while the platform already defines `subscriber_id` as
its stable aggregation and serving key.

### Decision

Allow MongoDB to generate `_id` as an `ObjectId`. Store `subscriber_id` at the
document root and enforce uniqueness with `uq_subscriber_id`.

### Rationale

- keeps MongoDB identity separate from the domain identifier;
- supports direct lookup and upsert by the canonical key;
- prevents duplicate subscriber documents;
- matches the implemented document contract.

### Consequences

- consumers query by `subscriber_id`, not `_id`;
- every environment must create or verify the unique index;
- existing documents preserve their `_id` across upserts.

---

## ADR-028 — Synchronize profiles with unordered idempotent bulk upserts

**Status:** Accepted

**Implementation:** Completed after `v0.2.3`.

### Decision

Convert the validated Parquet snapshot to BSON-safe nested documents and submit
`UpdateOne` operations using a `subscriber_id` filter, `$set`, `upsert=True`,
and `ordered=False`.

Do not add a synchronization timestamp that changes on every identical run.

### Rationale

- supports efficient batch synchronization;
- retries do not create duplicates;
- an unchanged second run produces no document modifications;
- independent operations can still be attempted when one operation fails.

### Consequences

- the unique subscriber index is mandatory;
- bulk-write failures must be surfaced;
- reports include source, matched, modified, upserted, failed, and validated counts.

---

## ADR-029 — Do not delete profiles implicitly during synchronization

**Status:** Accepted

**Implementation:** Completed after `v0.2.3`.

### Decision

Upsert every profile in the current snapshot but do not delete MongoDB
documents that are absent from that snapshot.

### Rationale

- avoids destructive behavior from an incomplete or partial snapshot;
- keeps replacement semantics explicit;
- provides a safer first serving implementation.

### Consequences

- MongoDB may retain a profile no longer present in a later source;
- explicit deletion or full replacement requires a future contract.

---

## ADR-030 — Define profile activity dates from inclusive daily window starts

**Status:** Accepted

**Implementation:** Completed after `v0.2.3`.

### Context

Daily windows use half-open intervals `[window_start, window_end)`. Therefore,
`window_end` identifies the start of the following day, not a day on which
activity was observed.

### Decision

Calculate:

```text
first_activity_at = min(window_start)
last_activity_at  = max(window_start)
```

### Rationale

- profile fields represent actual observed active days;
- standard half-open window semantics remain intact;
- the final day no longer appears one day later than its source partition.

### Consequences

- tests and documentation treat `window_end` as exclusive;
- existing snapshots and MongoDB documents must be rebuilt and synchronized.

---

## ADR-031 — Separate operational and analytical consumption paths

**Status:** Accepted; visualization-product selection superseded by ADR-033

### Context

Current subscriber profile lookup and historical analytical exploration have
different access patterns. Forcing both through FastAPI or MongoDB would blur
the serving boundary, while adding Snowflake alongside Glue and Athena would
duplicate analytical responsibilities without a defined requirement.

### Decision

Use two purpose-built consumption paths:

```text
Operational:
Current Profiles → MongoDB Atlas → FastAPI → Consumer Applications

Analytical:
Curated Parquet in Amazon S3 → Snowflake → Analytical Visualization
```

Snowflake replaces the previously planned Glue/Athena query layer. The selected
visualization product queries Snowflake directly for historical trends, KPIs,
and exploration. FastAPI remains the controlled interface for operational
subscriber access. Parquet in Amazon S3 remains the canonical analytical
output.

### Rationale

- assigns each technology to a clear workload;
- prevents analytical scans from affecting operational profile serving;
- uses Snowflake for governed SQL analytics and independent compute;
- keeps analytical visualization independent from the operational API;
- preserves MongoDB and FastAPI for low-latency operational access;
- avoids adding overlapping cloud query engines for architectural decoration.

### Consequences

- Snowflake loading and reconciliation become a separate milestone;
- the visualization layer depends on the Snowflake analytical contract;
- operational consumer applications depend on FastAPI;
- two access paths require separate credentials and deployment controls;
- Glue and Athena are removed from the committed target architecture.

---

## ADR-032 — Load canonical Parquet into a native Snowflake table

**Status:** Accepted

### Context

The analytical warehouse needs predictable SQL types, file-level traceability,
controlled reruns, and independent compute without replacing the canonical
Parquet history in Amazon S3. Querying files alone would not provide the same
native-table contract or load-history behavior.

### Decision

Use a Snowflake storage integration and external stage to load curated daily
Parquet into `CURATED.SUBSCRIBER_ACTIVITY_DAILY` with `COPY INTO`. Keep
`FORCE = FALSE`, populate four non-null source-metadata columns, and expose a
separate view in the `ANALYTICS` schema.

Use two dedicated roles:

- `SUBSCRIBER_ANALYTICS_LOADER` for stage use, insertion, and physical-table
  validation;
- `SUBSCRIBER_ANALYTICS_READER` for approved analytical views only.

Disable secondary roles when validating either role. Use a dedicated
`X-Small` warehouse with 60-second auto-suspend and a monthly resource monitor.

### Rationale

- preserves S3 Parquet as the canonical product;
- provides explicit Snowflake types and stable SQL access;
- records source filename, content key, modification time, and load time;
- makes unchanged-file reruns idempotent through load history;
- separates loading from analytical consumption;
- prevents administrative roles from hiding missing grants during testing;
- constrains trial and demonstration cost.

### Consequences

- storage-integration setup still requires an AWS trust relationship and
  account-level Snowflake administration;
- the real AWS role ARN must be supplied as a session variable and not
  committed;
- changed files require an explicit reload decision rather than implicit
  replacement;
- orchestration remains manual until an automation requirement is approved;
- schema changes must update Parquet, the native table, analytical views,
  validation SQL, and documentation together.

---

## ADR-033 — Defer visualization-product selection

**Status:** Superseded by ADR-034

### Context

Apache Superset was originally planned as the visualization layer. The public
portfolio requirement now includes professional relevance, low-cost public
embedding, and delivery under `analytics.joviac.cloud`. Power BI and Tableau
are also viable candidates, while Superset offers greater hosting control at
the cost of operating an application and metadata database.

### Decision

Do not couple the completed Snowflake milestone to a visualization product.
Evaluate Power BI, Tableau, and Apache Superset in a separate milestone against:

- public embedding behavior;
- licensing and recurring cost;
- custom-domain presentation;
- authentication and exposure model;
- operational responsibility;
- professional and portfolio value.

The selected product must consume approved Snowflake analytical views. It must
not query MongoDB or FastAPI for historical analytics. Public presentation is
expected under `analytics.joviac.cloud`, using the existing Route 53,
CloudFront, and private-S3 website pattern where appropriate.

### Rationale

- preserves the validated Snowflake boundary regardless of presentation tool;
- avoids deploying Superset only because it appeared in an earlier diagram;
- allows the public-sharing model to influence the decision explicitly;
- prevents visualization licensing from blocking the warehouse milestone;
- keeps Grafana available for a future observability use case rather than
  treating it as the default BI layer.

### Consequences

- ADR-031 remains valid for workload separation but no longer fixes Superset;
- the architecture diagrams use a generic visualization layer;
- no dashboard product is presented as implemented in the Snowflake release;
- visualization-specific credentials, roles, hosting, and automation are
  deferred.

---

## ADR-034 — Use Apache Superset as the analytical visualization layer

**Status:** Accepted

### Context

The visualization decision evaluated Power BI, Tableau Public, Grafana, and
Apache Superset. Power BI Service could not be used with the available personal
account, Tableau Public would publish dashboards and underlying data, and the
direct Snowflake connector for Grafana requires Grafana Cloud or Enterprise.
Grafana also remains better aligned with the platform's future observability
scope. Superset provides Snowflake connectivity, local container learning, and
control over future hosting under `analytics.joviac.cloud`.

### Decision

Use Apache Superset 6.0.0 as the analytical visualization layer. Extend the
official lean image with only `psycopg2-binary` and `snowflake-sqlalchemy`. Run
Superset with PostgreSQL 17.10 as its metadata store through Docker Compose.

Keep the initial topology intentionally small:

```text
Browser
  → Apache Superset
      → PostgreSQL metadata
      → approved Snowflake analytical view
```

Do not add Redis, Celery, alerts, or reports until a requirement justifies
them. Local Superset binds only to `127.0.0.1:8088`; public deployment is a
separate increment.

### Rationale

- preserves direct use of the governed Snowflake analytical contract;
- demonstrates containerization and BI administration without changing data
  products;
- supports reusable metrics and interactive dashboards;
- avoids public-data requirements during development;
- retains control over future custom-domain deployment;
- minimizes operational components in the first increment.

### Consequences

- PostgreSQL metadata must be persisted, backed up, and migrated with Superset;
- a custom image is required because the lean image omits database drivers;
- Superset configuration and local secrets must remain separate from the Python
  pipeline environment;
- dashboard exports and public-hosting controls remain future work;
- `v0.5.0` remains incomplete until the first analytical dashboard and its
  delivery scope are validated.

---

## ADR-035 — Authenticate Superset to Snowflake with a service user and RSA key pair

**Status:** Accepted

### Context

Superset is a non-human analytical client. Snowflake is deprecating single-factor
password authentication for service identities, and the visualization layer
must not use `ACCOUNTADMIN`, the loader role, or a human login. The existing
reader role already defines the approved analytical boundary.

### Decision

Create `SUPERSET_SERVICE_USER` with `TYPE = SERVICE`, no password, and an RSA
public key supplied through a Snowflake session variable. Assign only
`SUBSCRIBER_ANALYTICS_READER` and set deterministic reader, warehouse, database,
and schema defaults.

Store the encrypted private key only under the ignored local Superset secrets
directory. Mount it read-only into the Superset container and keep its
passphrase outside Git. Disable secondary roles during validation and prove
both allowed view access and denied curated-table and stage access.

### Rationale

- uses strong authentication suitable for a non-human identity;
- separates visualization from human and administrative credentials;
- reuses the established view-only RBAC boundary;
- keeps private-key material out of the image and repository;
- makes positive and negative authorization tests explicit.

### Consequences

- operators must protect the private-key passphrase and rotate key pairs;
- deployed environments require managed secret and key storage;
- PostgreSQL must not receive Snowflake key material through shared environment
  configuration;
- Superset connection metadata is encrypted using `SUPERSET_SECRET_KEY`;
- losing both the encrypted private key and its passphrase requires registering
  a new key before the service can reconnect.

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

- [Architecture](architecture.md)
- [Data model](DATA_MODEL.md)
- [Pipeline](PIPELINE.md)
- [Roadmap](ROADMAP.md)
