# DEVELOPER_GUIDE.md

# Subscriber Analytics Platform
**Developer Guide (Operational Edition)**

> **Purpose:** This document is the authoritative engineering reference for continuing the development of the Subscriber Analytics Platform. It captures the project's current state, architectural decisions, engineering conventions, and development roadmap. Read this document before implementing new features or continuing development.

# Project Snapshot

| Item | Value |
|------|-------|
| Current Version | v0.2.3 |
| Current Git Tag | v0.2.3 |
| Primary Branch | main |
| Completed Milestone | MongoDB Atlas profile synchronization |
| Stable Pipeline | Raw JSONL → Enriched Parquet → Curated Hourly → Curated Daily → Current Subscriber Profiles → MongoDB Atlas |
| Next Deliverable | FastAPI subscriber profile service |
| Serving Path | MongoDB Atlas implemented; FastAPI and Dashboard planned |
| Primary Language | Python |
| Storage Formats | JSONL, Parquet |
| Architectural Style | Layered Batch Pipeline |
| Time Standard | UTC |
| Configuration | config/settings.py |
| Logging | Structured logging + execution reports |

# 1. Project Overview

The Subscriber Analytics Platform is a portfolio project that simulates a production-grade telecommunications analytics platform. The objective is to demonstrate sound engineering and architectural practices rather than simply producing code.

Current version: **v0.2.3**

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

## Completed milestone

**MongoDB Atlas**

## Planned milestones

1. FastAPI
2. Dashboard
3. AWS Glue / Athena

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
Curated Daily
    ↓
Current Subscriber Profiles
    ↓
MongoDB Atlas
    ↓ planned
FastAPI → Dashboard
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

- FastAPI is the only public interface.
- MongoDB is the serving database.
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
| ⏳ | FastAPI |
| ⏳ | Dashboard |
| ⏳ | Glue / Athena |

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

## 9.2 Next milestone

The next milestone is FastAPI. It will consume MongoDB Atlas; it must not read
Raw files or expose database credentials. Dashboard work remains deferred until
the API contract is implemented and tested.

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
