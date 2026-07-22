# Subscriber Analytics Platform -- Technical Architecture

## Current architecture

``` text
generators/
        │
        ▼
Raw layer (JSONL)
data/raw/year=YYYY/month=MM/day=DD/hour=HH/
        │
        ▼
Enrichment layer (Parquet)
data/enriched/year=YYYY/month=MM/day=DD/hour=HH/
        │
        ▼
Curated layer (Parquet)
data/curated/
```

## Storage strategy

-   Raw → JSONL
-   Enriched → Parquet
-   Curated → Parquet

## Planned services

-   Amazon S3
-   Athena
-   MongoDB Atlas
-   Snowflake
-   FastAPI
-   Dashboards
-   AI-powered insights

## Version roadmap

-   v0.1.0 → Raw ingestion
-   v0.2.0 → Enrichment layer
-   v0.3.0 → Curated datasets
-   v0.4.0 → MongoDB integration
-   v0.5.0 → Pipeline orchestration
-   v1.0.0 → End-to-end platform
