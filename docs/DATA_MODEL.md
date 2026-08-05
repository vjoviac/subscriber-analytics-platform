# Subscriber Analytics Platform — Data Model

## 1. Purpose

This document defines the data contracts used by Subscriber Analytics Platform.

The platform has four principal grains:

1. **Raw event:** one record per generated telecom event.
2. **Enriched event:** one record per event with normalized and reference attributes.
3. **Subscriber activity:** one record per subscriber and time window.
4. **Current subscriber profile:** one record per subscriber with latest state and historical aggregates.

Schemas evolve deliberately. Fields must not be silently renamed, removed, or reinterpreted.

---

## 2. Modeling principles

- All timestamps are UTC.
- Identifiers are strings unless arithmetic is required.
- IMSI and MSISDN are never numeric measures.
- Raw events preserve nested business domains.
- Enriched and curated data may be flattened for analytical efficiency.
- Curated averages retain supporting sums and sample counts.
- Current profiles contain one unique row per subscriber.
- Synthetic data must never be represented as real customer data.

---

## 3. Raw telecom event

### Example

```json
{
  "event_id": "evt-000001",
  "timestamp": "2026-07-16T09:30:00Z",
  "subscriber": {
    "imsi": "334020123456789",
    "msisdn": "+525512345678",
    "plan": "Premium"
  },
  "device": {
    "tac": "35693803",
    "vendor": "Samsung",
    "model": "Galaxy S24",
    "os": "Android",
    "device_capability": "5G"
  },
  "network": {
    "technology": "5G",
    "cell_id": "33402056012345",
    "city": "Mexico City",
    "state": "Ciudad de Mexico",
    "country": "Mexico"
  },
  "session": {
    "bytes_dl": 5242880,
    "bytes_ul": 786432,
    "latency_ms": 42,
    "packet_loss_pct": 0.3
  },
  "application": {
    "name": "YouTube",
    "category": "Streaming"
  }
}
```

The exact location fields depend on the current catalog implementation. New fields should be additive whenever possible.

---

## 4. Raw event fields

### 4.1 Event metadata

| Field | Type | Required | Description |
|---|---|---:|---|
| `event_id` | string | Yes | Unique event identifier |
| `timestamp` | UTC timestamp string | Yes | Event occurrence time in ISO 8601 format |

Constraints:

- `event_id` must not be empty.
- `event_id` should be unique within the dataset.
- `timestamp` must be parseable and timezone-aware.
- Normalized UTC values should end with `Z` or include a UTC offset.

### 4.2 Subscriber

| Field | Type | Required | Description |
|---|---|---:|---|
| `subscriber.imsi` | string | Yes | Synthetic international mobile subscriber identity |
| `subscriber.msisdn` | string | Yes | Synthetic telephone number in E.164 form |
| `subscriber.plan` | string | Yes | Commercial plan |

Constraints:

- IMSI remains a string.
- MSISDN remains a string.
- Mexican synthetic MSISDN values begin with `+52`.
- All values are fictional.

### 4.3 Device

| Field | Type | Required | Description |
|---|---|---:|---|
| `device.tac` | string | Yes | Type Allocation Code |
| `device.vendor` | string | Yes | Device manufacturer |
| `device.model` | string | Yes | Commercial model |
| `device.os` | string | Yes | Operating system |
| `device.device_capability` | string | Recommended | Maximum supported radio generation |

`device_capability` represents the highest supported technology. A `5G` device is assumed to support earlier generations used by the project.

Compatibility rule:

```text
network.technology rank <= device.device_capability rank
```

A `4G` device must not generate a `5G` event.

### 4.4 Network and location

| Field | Type | Required | Description |
|---|---|---:|---|
| `network.technology` | string | Yes | Radio access technology used |
| `network.cell_id` | string | Yes | Synthetic cell identifier |
| `network.city` | string | Yes | City associated with the cell |
| `network.state` | string | Optional | State or administrative region |
| `network.country` | string | Optional | Country |

Controlled technology values:

```text
2G
3G
4G
5G
```

Technology ordering is semantic, not alphabetical.

### 4.5 Session metrics

| Field | Type | Required | Description |
|---|---|---:|---|
| `session.bytes_dl` | integer | Yes | Downloaded bytes |
| `session.bytes_ul` | integer | Yes | Uploaded bytes |
| `session.latency_ms` | numeric or null | Yes | Latency in milliseconds |
| `session.packet_loss_pct` | numeric or null | Yes | Packet loss percentage |

Constraints:

- byte counters are non-negative;
- latency is non-negative when present;
- packet loss is between `0` and `100` when present;
- null quality metrics are allowed when no valid measurement exists.

Derived event value:

```text
total_bytes = bytes_dl + bytes_ul
```

### 4.6 Application

| Field | Type | Required | Description |
|---|---|---:|---|
| `application.name` | string | Yes | Application name |
| `application.category` | string | Yes | Analytical category |

Example categories:

- Streaming
- Social Media
- Messaging
- Browsing
- Gaming
- Productivity
- Cloud Services

---

## 5. Enriched event model

### Grain

One row per raw event.

### Purpose

The enriched model converts nested source events into a typed, analytics-ready representation and adds stable dimensional attributes.

### Recommended columns

| Column | Type | Description |
|---|---|---|
| `event_id` | string | Unique source event |
| `event_timestamp` | timestamp UTC | Event occurrence time |
| `event_date` | date | Derived UTC date |
| `event_hour` | integer | Derived UTC hour |
| `subscriber_id` | string | Canonical subscriber identifier |
| `imsi` | string | Synthetic IMSI |
| `msisdn` | string | Synthetic MSISDN |
| `plan` | string | Subscriber plan |
| `tac` | string | Device TAC |
| `device_vendor` | string | Manufacturer |
| `device_model` | string | Device model |
| `device_os` | string | Operating system |
| `device_capability` | string | Maximum radio generation |
| `network_technology` | string | Technology used |
| `cell_id` | string | Cell identifier |
| `city` | string | City |
| `state` | string or null | State or region |
| `country` | string or null | Country |
| `application_name` | string | Application |
| `application_category` | string | Application category |
| `bytes_dl` | integer | Download bytes |
| `bytes_ul` | integer | Upload bytes |
| `total_bytes` | integer | Total traffic |
| `latency_ms` | numeric or null | Event latency |
| `packet_loss_pct` | numeric or null | Event packet loss |

The implementation may use equivalent names, but documentation and validation must match actual code.

---

## 6. Hourly subscriber activity

### Dataset

```text
subscriber_activity_hourly
```

### Grain

```text
subscriber_id + hourly window
```

### Purpose

Summarize how one subscriber used the network during one UTC hour.

### Keys and window

| Column | Type | Description |
|---|---|---|
| `subscriber_id` | string | Canonical subscriber key |
| `window_start` | timestamp UTC | Inclusive start of the hour |
| `window_end` | timestamp UTC | Exclusive end of the hour |

### Latest dimensional state

The row should retain the latest applicable values observed in the hour, including subscriber plan, device, technology, cell, and location attributes.

### Usage metrics

| Column | Type | Description |
|---|---|---|
| `event_count` | integer | Source events in the hour |
| `total_bytes_dl` | integer | Download bytes |
| `total_bytes_ul` | integer | Upload bytes |
| `total_bytes` | integer | Download plus upload bytes |

### Quality metric components

| Column | Type | Description |
|---|---|---|
| `latency_sum` | numeric | Sum of valid latency samples |
| `latency_sample_count` | integer | Number of valid latency samples |
| `avg_latency_ms` | numeric or null | Weighted hourly average |
| `packet_loss_sum` | numeric | Sum of valid packet-loss samples |
| `packet_loss_sample_count` | integer | Number of valid packet-loss samples |
| `avg_packet_loss_pct` | numeric or null | Weighted hourly average |

The unique key is:

```text
subscriber_id, window_start, window_end
```

Optional application metrics should be added only when their aggregation semantics are fully supported.

---

## 7. Daily subscriber activity

### Dataset

```text
subscriber_activity_daily
```

### Grain

```text
subscriber_id + daily window
```

### Purpose

Provide daily subscriber activity and serve as the source for current subscriber profiles.

### Schema groups

- subscriber key and daily window;
- latest daily subscriber, device, network, and location state;
- daily event and byte totals;
- latency and packet-loss sums;
- latency and packet-loss sample counts;
- weighted daily averages.

The unique key is:

```text
subscriber_id, window_start, window_end
```

### Important limitation

The current daily model does not preserve sufficient evidence to derive a historically correct `top_application`. The current-profile model must not fabricate this field.

A future application-usage dataset may add this capability explicitly.

### Snowflake physical projection

The native table is:

```text
SUBSCRIBER_ANALYTICS.CURATED.SUBSCRIBER_ACTIVITY_DAILY
```

Its grain remains `subscriber_id + window_start + window_end`. The table uses
explicit Snowflake types rather than relying on schema inference at load time.
The 35 Parquet fields are followed by four required lineage columns populated
from Snowflake metadata:

| Column | Snowflake type | Source |
|---|---|---|
| `source_filename` | `VARCHAR NOT NULL` | `METADATA$FILENAME` |
| `source_file_content_key` | `VARCHAR NOT NULL` | `METADATA$FILE_CONTENT_KEY` |
| `source_file_last_modified` | `TIMESTAMP_TZ(9) NOT NULL` | `METADATA$FILE_LAST_MODIFIED` |
| `loaded_at` | `TIMESTAMP_TZ(9) NOT NULL` | `METADATA$START_SCAN_TIME` |

Relevant explicit mappings include:

- `monthly_data_allowance_gb` → `NUMBER(10,2)`;
- `technology_access` → `ARRAY`;
- packet-loss sums → `NUMBER(18,4)`;
- stored averages → fixed-scale numeric values;
- Parquet event-window timestamps → `TIMESTAMP_TZ(6)`;
- source-lineage timestamps → `TIMESTAMP_TZ(9)`.

The physical table retains IMSI, MSISDN, TAC, and cell identifiers because it
must reproduce the canonical Parquet contract. Those fields are not exposed by
the initial analytical serving view.

#### Native table contract

| Column | Snowflake type | Nullable |
|---|---|---:|
| `subscriber_id` | `VARCHAR` | No |
| `imsi` | `VARCHAR` | Yes |
| `msisdn` | `VARCHAR` | Yes |
| `customer_segment` | `VARCHAR` | Yes |
| `subscriber_status` | `VARCHAR` | Yes |
| `plan_id` | `VARCHAR` | Yes |
| `plan_name` | `VARCHAR` | Yes |
| `plan_type` | `VARCHAR` | Yes |
| `monthly_data_allowance_gb` | `NUMBER(10,2)` | Yes |
| `max_download_mbps` | `NUMBER(38,0)` | Yes |
| `max_upload_mbps` | `NUMBER(38,0)` | Yes |
| `technology_access` | `ARRAY` | Yes |
| `latest_tac` | `VARCHAR` | Yes |
| `latest_device_vendor` | `VARCHAR` | Yes |
| `latest_device_model` | `VARCHAR` | Yes |
| `latest_device_os` | `VARCHAR` | Yes |
| `latest_device_technology` | `VARCHAR` | Yes |
| `latest_cell_id` | `VARCHAR` | Yes |
| `latest_city` | `VARCHAR` | Yes |
| `latest_state` | `VARCHAR` | Yes |
| `latest_network_technology` | `VARCHAR` | Yes |
| `event_count` | `NUMBER(38,0)` | No |
| `total_bytes_dl` | `NUMBER(38,0)` | No |
| `total_bytes_ul` | `NUMBER(38,0)` | No |
| `total_bytes` | `NUMBER(38,0)` | No |
| `latency_sum` | `NUMBER(38,0)` | No |
| `latency_sample_count` | `NUMBER(38,0)` | No |
| `packet_loss_sum` | `NUMBER(18,4)` | No |
| `packet_loss_sample_count` | `NUMBER(38,0)` | No |
| `avg_latency_ms` | `NUMBER(12,2)` | Yes |
| `avg_packet_loss_pct` | `NUMBER(12,4)` | Yes |
| `aggregation_grain` | `VARCHAR` | No |
| `window_start` | `TIMESTAMP_TZ(6)` | No |
| `window_end` | `TIMESTAMP_TZ(6)` | No |
| `curated_at` | `TIMESTAMP_TZ(6)` | No |
| `source_filename` | `VARCHAR` | No |
| `source_file_content_key` | `VARCHAR` | No |
| `source_file_last_modified` | `TIMESTAMP_TZ(9)` | No |
| `loaded_at` | `TIMESTAMP_TZ(9)` | No |

### Snowflake analytical serving view

The approved view is:

```text
SUBSCRIBER_ANALYTICS.ANALYTICS.SUBSCRIBER_ACTIVITY_DAILY
```

It derives `activity_date` from `window_start`, preserves one row per
subscriber and daily window, and excludes `imsi`, `msisdn`, `latest_tac`, and
`latest_cell_id`. It retains metric sums and sample counts so downstream
queries can calculate weighted averages instead of averaging stored averages.

The read-only role can query this view but cannot access the curated table,
external stage, file format, or storage integration.

---

## 8. Current subscriber profile

### Dataset

```text
subscriber_profiles_current
```

### Grain

Exactly one row per:

```text
subscriber_id
```

### Purpose

Combine the latest known state with historical activity and quality metrics.

### Implemented schema

The Parquet snapshot contains 29 columns organized into the groups below.

#### Identity

| Column | Type | Description |
|---|---|---|
| `subscriber_id` | string | Canonical key |
| `imsi` | string | Latest IMSI |
| `msisdn` | string | Latest MSISDN |
| `plan` | string | Latest plan |

#### Latest device state

| Column | Type | Description |
|---|---|---|
| `tac` | string | Latest device TAC |
| `device_vendor` | string | Latest vendor |
| `device_model` | string | Latest model |
| `device_os` | string | Latest OS |
| `device_capability` | string | Latest maximum capability |

#### Latest network and location state

| Column | Type | Description |
|---|---|---|
| `network_technology` | string | Latest observed technology |
| `cell_id` | string | Latest cell |
| `city` | string | Latest city |
| `state` | string or null | Latest state |
| `country` | string or null | Latest country |

`country` is currently published as null because the daily activity dataset does not yet provide that attribute. The field is retained as an explicit optional part of the profile contract.

#### Historical coverage

| Column | Type | Description |
|---|---|---|
| `first_activity_at` | timestamp UTC | Inclusive start of the earliest observed active day |
| `last_activity_at` | timestamp UTC | Inclusive start of the latest observed active day |
| `active_day_count` | integer | Number of daily activity rows |

#### Lifetime usage

| Column | Type | Description |
|---|---|---|
| `lifetime_event_count` | integer | Total source events |
| `lifetime_total_bytes_dl` | integer | Lifetime download bytes |
| `lifetime_total_bytes_ul` | integer | Lifetime upload bytes |
| `lifetime_total_bytes` | integer | Lifetime total bytes |

#### Lifetime quality components

| Column | Type | Description |
|---|---|---|
| `lifetime_latency_sum` | numeric | Sum of valid latency samples |
| `lifetime_latency_sample_count` | integer | Valid latency sample count |
| `lifetime_avg_latency_ms` | numeric or null | Weighted lifetime average |
| `lifetime_packet_loss_sum` | numeric | Sum of valid packet-loss samples |
| `lifetime_packet_loss_sample_count` | integer | Valid packet-loss sample count |
| `lifetime_avg_packet_loss_pct` | numeric or null | Weighted lifetime average |

#### Profile metadata

| Column | Type | Description |
|---|---|---|
| `profile_version` | integer | Materialization or schema version |
| `profile_updated_at` | timestamp UTC | Snapshot build time |

### Latest-state selection

Sort deterministically by at least:

```text
subscriber_id
window_end
window_start
```

When timestamps tie, use a documented tie-breaker rather than source file order.

### Weighted averages

```text
lifetime_avg_latency_ms
=
lifetime_latency_sum / lifetime_latency_sample_count
```

```text
lifetime_avg_packet_loss_pct
=
lifetime_packet_loss_sum / lifetime_packet_loss_sample_count
```

When the sample count is zero, the average is null rather than zero.

### Integrity rules

- `subscriber_id` is unique.
- Lifetime counters are non-negative.
- `first_activity_at <= last_activity_at`.
- Activity coverage uses `window_start`; daily `window_end` is exclusive and is not an observed activity date.
- `active_day_count >= 1`.
- Lifetime events equal the sum of daily event counts.
- `profile_updated_at` is timezone-aware.
- The final snapshot is published atomically.

---

## 9. MongoDB document model

Implemented representation:

```json
{
  "_id": "ObjectId generated by MongoDB",
  "subscriber_id": "SUB_000001",
  "subscriber": {
    "imsi": "334030123456789",
    "msisdn": "+525512345678",
    "plan": "Unlimited"
  },
  "device": {
    "tac": "35693803",
    "vendor": "Samsung",
    "model": "Galaxy S24",
    "os": "Android",
    "capability": "5G"
  },
  "last_network_state": {
    "technology": "5G",
    "cell_id": "33402056012345",
    "city": "Mexico City",
    "state": "Ciudad de Mexico",
    "country": "Mexico"
  },
  "activity": {
    "first_activity_at": "BSON Date",
    "last_activity_at": "BSON Date",
    "active_day_count": 4,
    "lifetime_event_count": 3222,
    "lifetime_total_bytes_dl": 61180429514,
    "lifetime_total_bytes_ul": 6307025169,
    "lifetime_total_bytes": 67487454683,
    "lifetime_latency_sum": 178205,
    "lifetime_latency_sample_count": 3222,
    "lifetime_avg_latency_ms": 55.31,
    "lifetime_packet_loss_sum": 2900.44,
    "lifetime_packet_loss_sample_count": 3222,
    "lifetime_avg_packet_loss_pct": 0.9002
  },
  "metadata": {
    "profile_version": 1,
    "profile_updated_at": "BSON Date"
  }
}
```

Identity strategy:

```text
_id            = MongoDB-generated ObjectId
subscriber_id  = stable top-level business key
```

Implemented indexes:

- `_id_`, created automatically by MongoDB;
- `uq_subscriber_id`, unique on top-level `subscriber_id`.

Additional indexes must follow actual API query patterns and are deferred until
FastAPI queries exist.

### BSON conversion rules

- pandas timestamps become timezone-aware BSON dates;
- pandas, NumPy, and floating-point missing values become BSON `null`;
- NumPy scalars become native Python numeric values;
- `_id` is not supplied by the synchronization code;
- one Parquet row becomes one nested MongoDB document.

### Synchronization contract

Each document is written with an upsert equivalent to:

```text
filter:  {"subscriber_id": <subscriber_id>}
update:  {"$set": <complete profile document>}
upsert:  true
```

The collection contains at most one document per `subscriber_id`. Repeating an
unchanged snapshot preserves the existing `_id` and does not create duplicates.
Profiles missing from a later snapshot are not deleted implicitly.

---

## 10. API resource model

Implemented endpoints:

```text
GET /health
GET /ready
GET /subscribers/{subscriber_id}
GET /subscribers
```

The subscriber lookup response follows the nested MongoDB serving document but
does not expose the database-generated `_id`. All profile timestamps are
serialized in UTC. Unknown subscribers return `404 Not Found`; database
unavailability returns `503 Service Unavailable` without exposing internal
connection details.

The listing endpoint uses one-based `page` values and a `page_size` bounded
from 1 through 100. Results are ordered by the unique top-level
`subscriber_id` in ascending order. Its response contains profile `items` and
pagination metadata with `page`, `page_size`, `total_items`, and `total_pages`.
MongoDB `_id` remains excluded. A valid page beyond the available profiles
returns an empty `items` list rather than `404 Not Found`.

---

Analytical datasets are consumed separately through Snowflake. The public
visualization product remains to be selected and must query approved analytical
views rather than MongoDB or FastAPI. Broad historical aggregations are not
added to FastAPI without a defined operational requirement.

## 11. Schema evolution

### Additive changes

Examples:

- adding `country`;
- adding a derived metric;
- adding profile metadata.

Usually backward-compatible when consumers accept optional fields.

### Breaking changes

Examples:

- renaming `subscriber_id`;
- changing bytes to megabytes without renaming fields;
- changing UTC timestamps to local time;
- changing dataset grain.

Breaking changes require documentation, tests, a rebuild or migration plan, and an appropriate version increment.

Where useful, datasets may include:

```text
schema_version
pipeline_version
profile_version
```

---

## 12. Validation summary

### Raw

- required nested objects present;
- identifiers non-empty;
- timestamp valid;
- byte counters non-negative;
- technology compatible with device capability.

### Enriched

- one accepted row per raw event;
- required columns present;
- no null keys;
- correct partition date and hour;
- event identifiers valid.

### Hourly

- unique subscriber-window key;
- positive event counts;
- total bytes consistent;
- weighted averages consistent with sums and counts.

### Daily

- unique subscriber-window key;
- inputs belong to target day;
- daily totals equal hourly totals;
- weighted averages use accumulated components.

### Snowflake analytical warehouse

- loaded row count equals the canonical Parquet row count;
- aggregate event and byte totals reconcile exactly;
- `total_bytes = total_bytes_dl + total_bytes_ul`;
- every loaded row contains all four source-lineage values;
- every window has `aggregation_grain = 'daily'`;
- every `window_end` is one day after `window_start`;
- the analytical `activity_date + subscriber_id` grain is unique;
- global weighted averages equal the canonical Parquet calculations;
- unchanged files are skipped when `FORCE = FALSE`.

### Current profiles

- one row per subscriber;
- deterministic latest state;
- valid UTC activity and profile timestamps;
- non-negative lifetime counters;
- at least one active day;
- lifetime metrics equal daily sums;
- zero-sample lifetime averages are null;
- no fabricated top application;
- atomic publication.

### MongoDB serving documents

- every required Parquet column is present before conversion;
- source `subscriber_id` values are non-null, non-blank, and unique;
- activity and profile timestamps are valid UTC values;
- document values are BSON-safe;
- `uq_subscriber_id` prevents duplicate business keys;
- post-write validation confirms that every source subscriber exists.

---

## 13. Units and naming

| Concept | Unit |
|---|---|
| Download and upload volume | bytes |
| Latency | milliseconds |
| Packet loss | percent |
| Time | UTC |
| Windows | half-open interval `[start, end)` |

Naming conventions:

- snake_case for Parquet and Python-facing schemas;
- units included in names where ambiguity exists;
- `*_count`, `*_sum`, and `avg_*` for metrics;
- `*_at` for timestamps;
- `window_start` and `window_end` for aggregates;
- avoid uncommon abbreviations.

---

## 14. Related documentation

- [Architecture](architecture.md)
- [Pipeline](PIPELINE.md)
- [Architecture decisions](DECISIONS.md)
- [Roadmap](ROADMAP.md)
