# Subscriber Analytics Platform

Cloud-native platform designed to simulate, ingest, process and analyze telecommunications subscriber events.

## Architecture

┌─────────────────────┐
│ Event Generator     │
│ Python              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Raw Layer           │
│ JSONL               │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Enrichment Layer    │
│ Parquet             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Curated Layer       │
│ Analytics datasets  │
└──────────┬──────────┘
           │
           ├───────────────┐
           ▼               ▼
┌─────────────────┐  ┌─────────────────┐
│ MongoDB Atlas   │  │ Snowflake       │
│ Serving Layer   │  │ Analytics       │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └─────────┬──────────┘
                   ▼
      ┌────────────────────────┐
      │ APIs / Dashboards / AI │
      └────────────────────────┘

## Objectives

- Build a modern telecom analytics architecture.
- Learn and apply AWS services.
- Explore data platforms such as Snowflake and MongoDB.
- Design scalable data pipelines.
- Demonstrate cloud and solution architecture skills.

## Planned Architecture

- Event Generator (Python)
- Data ingestion layer
- AWS S3 storage
- APIs with FastAPI
- Analytics and dashboards
- Snowflake and MongoDB integration
- AI-powered insights

## Technologies

- Python
- AWS
- GitHub
- FastAPI
- Snowflake
- MongoDB
- Docker