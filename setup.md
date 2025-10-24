setup.md

## Start infrastructure

```sh
echo "🐳 Starting Docker containers..."
docker compose down -v 2>/dev/null || true
docker compose up -d
```

## Wait for services

```sh

echo "⏳ Sleeping 5 seconds to let services start..."
sleep 5

echo "⏳ Checking Zookeeper on localhost:2181..."
nc -zv localhost 2181

echo "⏳ Checking Kafka on localhost:9092..."
nc -zv localhost 9092

echo "⏳ Checking ClickHouse on localhost:9000..."
nc -zv localhost 9000

echo "⏳ Checking Timeplus on localhost:8463..."
nc -zv localhost 8463
```


## Prepare environment

```sh

echo "📝 Creating Kafka topic..."
docker exec e2e_kafka kafka-topics \
  --create \
  --topic e2e_events \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --if-not-exists

```


## Create ClickHouse table (sink)

```sh

echo "📊 Creating ClickHouse table..."
docker exec e2e_clickhouse clickhouse-client -mn --query "
DROP TABLE IF EXISTS e2e_aggregation_results;

CREATE TABLE e2e_aggregation_results (
    win_start DateTime64(3),
    win_end DateTime64(3),
    user_id String,
    event_type String,
    region String,
    event_count UInt64,
    total_amount Float64,
    avg_amount Float64,
    min_amount Float64,
    max_amount Float64,
    inserted_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (win_start, user_id)
PARTITION BY toYYYYMM(win_start);
"

```

## Install Python packages for generator and verification

Install the client libraries used by `generate_data.py` and `verify.py` in the same venv:

```
source ~/miniconda3/bin/activate
conda create -n py310_oct23 -y   python=3.10 
conda activate py310_oct23
pip install kafka-python timeplus-connect clickhouse-connect dbt-timeplus
```

## Initialize Timeplus resources with dbt

Use standard dbt commands with the included project under `dbt_e2e/`.

```
# Point dbt to the bundled profiles.yml (or copy it to ~/.dbt/profiles.yml)
export DBT_PROFILES_DIR=$(pwd)/dbt_e2e

# Create/refresh resources in Timeplus
dbt run --project-dir dbt_e2e

# (Optional) run tests if you add them later
dbt test --project-dir dbt_e2e
```

Models in `dbt_e2e/models`:
- `01_event_aggregations_mv.sql`: creates `kafka_events_stream`, `event_aggregations`, and MV `event_aggregations_mv`.
- `02_to_clickhouse_mv.sql`: creates external table `clickhouse_results` and MV `to_clickhouse_mv`.
- `03_user_activity_summary.sql`: a view for analytics on `event_aggregations`.


## Ingest testing data

```
source .venv/bin/activate
python3 generate_data.py
```

Example output:

```
📤 Starting event generation...
   Rate: 10 events/second
   Duration: 60 seconds
   Batch size: 100 events

   Generated 600 events...
✅ Generated 600 events in 60 seconds
```


## Verify from ClickHouse and Timeplus

```
source .venv/bin/activate
# If you deployed into the default database via dbt_e2e/profiles.yml
TP_DB=default python3 verify.py
```

Example output:

```
🔬 E2E Pipeline Verification
==================================================
🔍 Checking Kafka...
   ✅ Kafka topic has events (sampled 0 recent events)

🔍 Checking Timeplus...
   ✅ Connected to Timeplus
   Available streams: <...>
   Aggregation stats: [...]
   Top 5 users by amount: [...]

🔍 Checking ClickHouse...
   ✅ ClickHouse has data:
      Total records: 580
      Date range: ...
      Unique users: 100
      Event types: 6

   Recent aggregations:
      (...)

==================================================
📊 Summary:
   Kafka: ✅ OK
   Timeplus: ✅ OK
   ClickHouse: ✅ OK

🎉 Pipeline is working correctly!
```
