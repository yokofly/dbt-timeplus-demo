# Kafka → Timeplus → ClickHouse (Streaming ETL Demo)

This repository demonstrates a runnable end-to-end streaming pipeline:

- Kafka produces events
- Timeplus (Proton) reads Kafka, aggregates/transforms with streaming SQL
- Results are continuously written into ClickHouse via a Timeplus materialized view

It includes a Docker Compose stack, a minimal dbt project for managing Timeplus resources, a data generator, and a verification script.

## Repository Layout

```
.
├── docker-compose.yml         # Kafka/Zookeeper, Timeplus (Proton), ClickHouse
├── setup.md                   # Step-by-step quickstart
├── generate_data.py           # Sends synthetic events to Kafka (JSONEachRow)
├── verify.py                  # Verifies Kafka/Timeplus/ClickHouse end-to-end
├── dbt_e2e/                   # Minimal dbt project to manage Timeplus resources
│   ├── dbt_project.yml
│   ├── profiles.yml           # Concrete dbt profile (default user/db)
│   └── models/
│       ├── 01_event_aggregations_mv.sql  # Kafka external stream + aggregation MV
│       ├── 02_to_clickhouse_mv.sql       # External table to ClickHouse + sink MV
│       └── 03_user_activity_summary.sql  # Analytics view
├── logs/                      # dbt and other logs (git-ignored)
└── .gitignore
```

## Prerequisites

- Docker + Docker Compose
- Python 3.10+ (for generator & verification scripts)
- dbt-timeplus (Python package)

## Quick Start

You can follow setup.md for detailed steps, or the summary below.

## Customization

- Change Kafka brokers/topic via `KAFKA_BROKERS`/`KAFKA_TOPIC` env vars.
- Change ClickHouse address/database/table via `CH_ADDRESS`/`CH_DATABASE`/`CH_TABLE` env vars.
- For dbt, edit `dbt_e2e/profiles.yml` (type: timeplus, host, port, user, password, schema). You can also copy it to `~/.dbt/profiles.yml`.

## Notes

- The dbt project uses pre_hook statements to create external streams/tables and MVs idempotently.
- The ClickHouse table must exist before running dbt; Timeplus writes “into” it via the sink MV.

## Learn More

- Timeplus materialized views and streaming SQL enable continuous processing and sub-second latency from Kafka to ClickHouse.
