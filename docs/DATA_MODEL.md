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

### Proposed schema

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

#### Historical coverage

| Column | Type | Description |
|---|---|---|
| `first_activity_at` | timestamp UTC | Earliest observed daily window |
| `last_activity_at` | timestamp UTC | Latest observed daily window |
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
- `active_day_count >= 1`.
- Lifetime events equal the sum of daily event counts.
- `profile_updated_at` is timezone-aware.
- The final snapshot is published atomically.

---

## 9. MongoDB document model

Recommended representation:

```json
{
  "_id": "334020123456789",
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
    "first_activity_at": "2026-07-01T00:00:00Z",
    "last_activity_at": "2026-07-22T23:00:00Z",
    "active_day_count": 22,
    "lifetime_event_count": 1480,
    "total_bytes_dl": 9000000000,
    "total_bytes_ul": 1200000000,
    "total_bytes": 10200000000,
    "avg_latency_ms": 41.7,
    "avg_packet_loss_pct": 0.24
  },
  "metadata": {
    "profile_version": 1,
    "profile_updated_at": "2026-07-23T12:00:00Z"
  }
}
```

Recommended `_id`:

```text
subscriber_id
```

Candidate indexes:

- unique `_id`;
- `subscriber.msisdn`;
- `subscriber.plan`;
- `device.vendor`;
- `device.capability`;
- `last_network_state.technology`;
- `last_network_state.city`;
- `activity.last_activity_at`.

Indexes should follow actual API query patterns.

---

## 10. API resource model

Potential endpoints:

```text
GET /health
GET /ready
GET /subscribers/{subscriber_id}
GET /subscribers
GET /analytics/overview
```

The API contract should not expose database-specific implementation details unless they are intentionally part of the public model.

---

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

### Current profiles

- one row per subscriber;
- deterministic latest state;
- lifetime metrics equal daily sums;
- no fabricated top application;
- atomic publication.

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

- [Architecture](ARCHITECTURE.md)
- [Pipeline](PIPELINE.md)
- [Architecture decisions](DECISIONS.md)
- [Roadmap](ROADMAP.md)
