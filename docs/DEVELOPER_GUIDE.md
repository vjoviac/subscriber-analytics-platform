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
| Current Milestone | MongoDB Atlas |
| Stable Pipeline | Raw JSONL → Enriched Parquet → Curated Hourly → Curated Daily → Current Subscriber Profiles |
| Next Deliverable | MongoDB Atlas integration |
| Planned Serving Layer | MongoDB Atlas → FastAPI → Dashboard |
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

## Current milestone

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
    ↓
FastAPI
    ↓
Dashboard
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
| ⏳ | MongoDB Atlas |
| ⏳ | FastAPI |
| ⏳ | Dashboard |
| ⏳ | Glue / Athena |

---

# 9. Next Milestone

Goal: **MongoDB Atlas**

Input:

- subscriber_profiles_current.parquet

Output:

- MongoDB Atlas collection

Requirements:

- connect through environment-based credentials;
- upsert by `subscriber_id`;
- use bulk operations;
- report inserted, matched, modified, and failed counts;
- preserve version and update timestamps;
- avoid deleting unobserved profiles by default;
- make full replacement explicit.

Repeated synchronization of the same snapshot must not create duplicates.

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
