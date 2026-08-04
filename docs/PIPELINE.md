# Subscriber Analytics Platform — Pipeline

## 1. Purpose

This document defines how the batch pipeline executes, which contracts each stage satisfies, how reruns are handled, and how a successful run is validated.

The pipeline remains understandable in local development while preserving patterns that can later move to managed cloud services.

---

## 2. Pipeline overview

```text
Generate telecom events
          ↓
Write raw JSONL
          ↓
Read and enrich events
          ↓
Write enriched Parquet
          ↓
Build hourly subscriber activity
          ↓
Repeat for all requested hours
          ↓
Build daily subscriber activity
          ↓
Validate raw, hourly, and daily counts
          ↓
Build and validate current subscriber profiles
          ↓
Atomically publish the current-profile snapshot
          ↓
Write structured execution report
```

Serving extension:

```text
Current subscriber profiles
          ↓
Synchronize MongoDB Atlas — implemented
          ↓
Serve through FastAPI — lookup and bounded listing implemented
          ↓
Consumer applications — planned
```

Analytical extension:

```text
Curated Parquet in Amazon S3
          ↓
Load into Snowflake — planned
          ↓
Query and visualize with Apache Superset — planned
```

---

## 3. Orchestration entry point

Current script:

```text
scripts/run_daily_pipeline.py
```

Expected arguments:

```text
--date
--hours
--events-per-hour
```

Example:

```bash
python -m scripts.run_daily_pipeline \
  --date 2026-07-22 \
  --hours 0 1 2 3 4 5 \
  --events-per-hour 1000
```

| Argument | Meaning |
|---|---|
| `--date` | UTC processing date in `YYYY-MM-DD` format |
| `--hours` | Requested UTC hours |
| `--events-per-hour` | Synthetic events per requested hour |

The CLI documentation must remain synchronized with the implementation.

---

## 4. Processing-time injection

For each requested hour, the orchestrator creates an explicit UTC timestamp and passes it to the generator:

```python
processing_time = datetime(
    year,
    month,
    day,
    hour,
    tzinfo=timezone.utc,
)

 events = generate_events(
    total_events=events_per_hour,
    event_time=processing_time,
)
```

Benefits:

- deterministic partition placement;
- controlled backfills;
- reproducible tests;
- independence from workstation time;
- valid hourly windows.

All generated events must belong to the requested hour.

---

## 5. Stage 1 — Event generation

### Input

- processing date and hour;
- requested event count;
- subscriber and reference catalogs;
- randomization settings.

### Output

An in-memory collection or iterator of raw event dictionaries.

### Responsibilities

- create unique `event_id` values;
- generate UTC timestamps;
- create valid synthetic subscriber identifiers;
- select compatible device and network values;
- generate non-negative session metrics;
- select controlled application values.

### Validation

- generated count equals requested count;
- required sections exist;
- timestamps belong to the requested hour;
- event IDs are non-empty;
- device and technology are compatible.

### Failure behavior

No raw output is published if generation fails before a valid collection exists.

---

## 6. Stage 2 — Raw persistence

### Format

JSON Lines, one event per line.

### Path

```text
data/raw/year=YYYY/month=MM/day=DD/hour=HH/
```

### Responsibilities

- create partition directories;
- serialize valid UTF-8 JSON;
- write one object per line;
- close files before reporting success;
- return path and count metadata.

### Validation

- final file exists;
- line count equals generated count;
- every line parses as JSON;
- partition matches event time.

### Preferred atomic pattern

```text
events.temporary.jsonl
        ↓
rename or replace
        ↓
events.jsonl
```

---

## 7. Stage 3 — Enrichment

### Input

One hourly raw JSONL file and reference catalogs.

### Output

One hourly enriched Parquet file.

### Path

```text
data/enriched/year=YYYY/month=MM/day=DD/hour=HH/
```

### Responsibilities

- parse raw events;
- validate required fields;
- normalize data types;
- attach reference attributes;
- derive event date, hour, and total bytes;
- preserve event-level grain;
- write typed Parquet.

### Reconciliation

```text
raw records = enriched rows
```

If invalid records are rejected in a future release, accepted and rejected counts must be explicit. Silent dropping is prohibited.

---

## 8. Stage 4 — Hourly aggregation

### Input

One enriched hourly partition.

### Output

One `subscriber_activity_hourly` partition.

### Grain

```text
subscriber_id + hourly window
```

### Responsibilities

- group events by subscriber;
- define `window_start` and `window_end`;
- calculate event and byte totals;
- retain latest dimensional state;
- preserve metric sums and sample counts;
- calculate weighted hourly averages.

### Key validation

```text
subscriber_id, window_start, window_end
```

must be unique.

### Reconciliation

```text
sum(hourly.event_count) = enriched row count
```

Latest values must be selected by event timestamp rather than arbitrary file order.

---

## 9. Stage 5 — Daily aggregation

### Input

All requested hourly curated partitions for one UTC date.

### Output

One daily Parquet partition:

```text
data/curated/subscriber_activity_daily/
└── year=YYYY/month=MM/day=DD/
```

### Grain

```text
subscriber_id + daily window
```

### Responsibilities

- discover hourly inputs;
- verify target date;
- reject duplicate hourly subscriber windows;
- group by subscriber;
- sum events and traffic;
- sum quality components;
- recalculate weighted averages;
- select latest daily dimensions;
- write one row per active subscriber.

### Reconciliation

```text
sum(daily.event_count)
=
sum(hourly.event_count)
```

### Missing-hour semantics

A run may intentionally process fewer than 24 hours. The pipeline must distinguish an intentionally partial requested day from a missing output for a requested hour.

---

## 10. Stage 6 — Final validation

Primary invariant:

```text
raw events
=
hourly event_count total
=
daily event_count total
```

This detects missing files, duplicate processing, row loss, stale outputs, and incomplete aggregation.

Additional checks:

- outputs exist;
- row counts are non-negative;
- timestamps are valid;
- partitions match processing date;
- aggregate keys are unique;
- total bytes equal download plus upload;
- weighted averages match sums and counts.

The run succeeds only when mandatory validation passes.

---

## 11. Stage 7 — Current subscriber profiles

### Input

```text
year=*/month=*/day=*/subscriber_activity_daily.parquet
```

### Output

```text
data/curated/subscriber_profiles_current/
└── subscriber_profiles_current.parquet
```

### Processing sequence

1. Discover all daily files.
2. Validate required columns.
3. Validate timestamps.
4. Reject duplicate daily subscriber windows.
5. Concatenate records.
6. Sort deterministically.
7. Select latest dimensions per subscriber.
8. Aggregate historical sums and counts.
9. Calculate weighted lifetime averages.
10. Add `profile_version`.
11. Add `profile_updated_at`.
12. Validate unique subscriber IDs.
13. Write a temporary file.
14. Atomically replace the final snapshot.

Activity coverage uses the inclusive daily `window_start`: the first activity
is `min(window_start)` and the last activity is `max(window_start)`.
`window_end` remains the exclusive boundary of each daily interval and is not
treated as an observed activity date.

The builder works independently and is also integrated into the daily orchestrator after raw-hourly-daily reconciliation. A failed profile build prevents the run from being reported as successful and does not replace a previously valid snapshot.

Standalone rebuild:

```bash
python -m scripts.run_current_profiles
```

The standalone command uses `DAILY_ACTIVITY_DIRECTORY` and `SUBSCRIBER_PROFILES_CURRENT_DIRECTORY` from centralized configuration.

---

## 12. Stage 8 — MongoDB synchronization

### Input

Current subscriber profile Parquet.

### Output

```text
subscriber_analytics.subscriber_profiles
```

### Entry point

```bash
python -m scripts.sync_mongodb_profiles
```

### Configuration

```dotenv
MONGODB_URI=
MONGODB_DATABASE=subscriber_analytics
MONGODB_COLLECTION=subscriber_profiles
MONGODB_TIMEOUT_MS=10000
```

### Processing sequence

1. Read `subscriber_profiles_current.parquet`.
2. Reject a missing or empty snapshot.
3. Validate the complete 29-column profile contract.
4. Validate unique, non-null, and non-blank `subscriber_id` values.
5. Parse `first_activity_at`, `last_activity_at`, and `profile_updated_at` as UTC.
6. Convert each row to a nested BSON-safe document.
7. Connect to Atlas and execute an administrative ping.
8. Obtain the configured database and collection.
9. Ensure the unique `uq_subscriber_id` index.
10. Build one `UpdateOne(..., upsert=True)` operation per subscriber.
11. Execute `bulk_write(..., ordered=False)`.
12. Count the source subscriber IDs found in MongoDB.
13. Reject a post-write count mismatch.
14. Return a synchronization report.
15. Close the MongoDB client in all outcomes.

### Idempotence

The upsert filter is the top-level `subscriber_id` and the update uses `$set`
with the complete profile document. MongoDB generates `_id` only on insertion.
An unchanged second run matches existing profiles without adding documents or
changing their `_id`.

No `synced_at` value is written because a new synchronization timestamp would
modify otherwise unchanged documents and obscure idempotence.

### Report

The command prints:

- `source_profile_count`;
- `matched_count`;
- `modified_count`;
- `upserted_count`;
- `failed_count`;
- `validated_profile_count`.

### Deletion semantics

The synchronization does not delete MongoDB documents that are absent from the
source snapshot. Full replacement remains an explicit future capability.

---

## 13. Stage 9 — FastAPI service

Implemented endpoints:

```text
GET /health
GET /ready
GET /subscribers/{subscriber_id}
GET /subscribers
```

Implemented listing contract:

- typed request and response models;
- one-based pagination;
- page size bounded from 1 through 100;
- deterministic ascending `subscriber_id` ordering;
- total item and page counts;
- meaningful HTTP status codes;
- database timeout handling;
- OpenAPI documentation.

---

## 14. Execution modes

### SAFE

- fail if a final output already exists;
- preserve the existing file;
- record the conflict.

### SKIP_EXISTING

- detect a valid existing output;
- mark the stage as skipped;
- continue downstream when possible;
- record skipped paths.

### OVERWRITE

- intentionally replace outputs;
- record overwritten paths;
- rebuild downstream outputs as needed.

The selected mode must be applied consistently across stages.

---

## 15. Pipeline run report

Representative structure:

```json
{
  "run_id": "20260722T120000Z-abcdef",
  "pipeline_name": "daily_subscriber_pipeline",
  "processing_date": "2026-07-22",
  "requested_hours": [0, 1, 2, 3],
  "events_per_hour": 1000,
  "execution_mode": "SKIP_EXISTING",
  "started_at": "2026-07-23T12:00:00Z",
  "finished_at": "2026-07-23T12:01:27Z",
  "status": "SUCCESS",
  "stages": [],
  "counts": {
    "raw_events": 4000,
    "hourly_events": 4000,
    "daily_events": 4000
  },
  "validation": {
    "passed": true
  },
  "error": null
}
```

Suggested stage statuses:

```text
CREATED
SKIPPED
OVERWRITTEN
FAILED
```

Overall statuses:

```text
SUCCESS
FAILED
```

A `PARTIAL` status should be introduced only after its semantics are defined.

---

## 16. Logging contract

Recommended fields:

| Field | Description |
|---|---|
| `timestamp` | UTC log time |
| `level` | Severity |
| `logger` | Logger name |
| `message` | Human-readable event |
| `run_id` | Run identifier |
| `stage` | Pipeline stage |
| `processing_date` | Target date |
| `processing_hour` | Target hour |
| `execution_mode` | Rerun mode |
| `input_path` | Source path |
| `output_path` | Destination path |
| `record_count` | Relevant count |
| `elapsed_ms` | Duration |
| `status` | Stage outcome |

Development logs should preserve stack traces.

---

## 17. Error handling

Expected errors include:

- missing input file;
- SAFE-mode conflict;
- invalid CLI date or hour;
- missing required column;
- malformed JSON;
- duplicate subscriber window;
- invalid timestamp;
- unavailable AWS profile;
- S3 permission failure;
- database connection failure.

Expected failures should be clear and return a non-zero exit status.

Unexpected exceptions should be logged with stack traces, mark the run as failed, preserve valid outputs, and propagate to the caller.

A broad `except Exception` is acceptable only at an orchestration boundary to finalize reporting; it must not silently hide failure.

---

## 18. Atomic file writes

For a target:

```text
target.parquet
```

write first to:

```text
target.temporary.parquet
```

Then:

1. verify the temporary file;
2. optionally validate schema and row count;
3. replace the final target;
4. remove temporary artifacts after failure.

This is especially important for current-profile snapshots.

---

## 19. Testing strategy

### Unit tests

- event generation;
- technology compatibility;
- path construction;
- serialization;
- enrichment mapping;
- hourly aggregation;
- daily aggregation;
- weighted averages;
- duplicate detection;
- profile construction;
- zero-sample lifetime averages;
- daily-to-profile reconciliation;
- atomic snapshot replacement and failure preservation;
- repeated profile builds;
- report serialization.

### Integration tests

- one hour;
- multiple hours;
- partial day;
- first run;
- SAFE conflict;
- SKIP_EXISTING recovery;
- OVERWRITE rebuild;
- stage failure;
- final reconciliation failure.

Tests should use deterministic data and temporary directories. AWS or MongoDB dependencies should be explicitly marked as external integration tests.

The MongoDB unit suite mocks external connectivity and covers configuration,
connection cleanup, snapshot validation, BSON conversion, index creation,
operation construction, bulk-write reporting, failure propagation, and script
orchestration. The MongoDB milestone closed with 95 passing tests. The current
suite contains 117 passing tests after the implemented FastAPI liveness,
readiness, subscriber lookup, and bounded subscriber listing increments.
Manual validation against MongoDB Atlas confirmed deterministic pagination over
two profiles and an empty item list for a valid page beyond the available data.

---

## 20. Scheduling evolution

### Current

Manual command execution.

### Local next step

- Windows Task Scheduler; or
- cron.

### Cloud options

- Amazon EventBridge Scheduler;
- AWS Step Functions;
- Amazon MWAA;
- scheduled ECS task.

The choice should follow the execution engine and learning objective, not architectural decoration.

---

## 21. Performance considerations

As volume grows:

- process data in chunks or iterators;
- avoid repeated catalog scans;
- use efficient Parquet compression;
- control row-group sizes;
- compact small files;
- parallelize independent hours;
- consider incremental profiles;
- use bulk MongoDB writes;
- index observed query patterns only.

Correctness takes priority over premature optimization.

---

## 22. Operational checklist

Before a run:

- virtual environment active;
- dependencies installed;
- configuration valid;
- date and hours confirmed;
- execution mode intentional;
- sufficient disk space;
- AWS profile available when needed.

After a run:

- process exited successfully;
- report status is `SUCCEEDED`;
- counts reconcile;
- current-profile count matches unique subscriber count;
- current-profile snapshot exists;
- skipped stages are expected;
- partitions exist;
- tests still pass after code changes.

---

## 23. Related documentation

- [Architecture](ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Architecture decisions](DECISIONS.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
