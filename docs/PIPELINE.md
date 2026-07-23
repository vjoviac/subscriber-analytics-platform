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
Write structured execution report
```

Planned extension:

```text
Daily subscriber activity
          ↓
Build current subscriber profiles
          ↓
Synchronize MongoDB Atlas
          ↓
Serve through FastAPI
          ↓
Consume from dashboard
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
python scripts/run_daily_pipeline.py \
  --date 2026-07-22 \
  --hours 0,1,2,3,4,5 \
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

## 11. Planned stage — Current subscriber profiles

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

The builder should work independently before orchestration integration.

---

## 12. Planned stage — MongoDB synchronization

### Input

Current subscriber profile Parquet.

### Output

MongoDB Atlas collection.

### Recommended behavior

- connect through environment-based credentials;
- upsert by `subscriber_id`;
- use bulk operations;
- report inserted, matched, modified, and failed counts;
- preserve version and update timestamps;
- avoid deleting unobserved profiles by default;
- make full replacement explicit.

Repeated synchronization of the same snapshot must not create duplicates.

---

## 13. Planned stage — FastAPI

Recommended endpoints:

```text
GET /health
GET /ready
GET /subscribers/{subscriber_id}
GET /subscribers
GET /analytics/overview
```

Requirements:

- typed request and response models;
- pagination;
- bounded page size;
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
- AWS Glue Workflows;
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
- report status is `SUCCESS`;
- counts reconcile;
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
