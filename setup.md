setup.md

## Start infrastructure
echo "🐳 Starting Docker containers..."
docker compose down -v 2>/dev/null || true
docker compose up -d

## Wait for services
wait_for_service localhost 2181 "Zookeeper"
wait_for_service localhost 9092 "Kafka"
wait_for_service localhost 9000 "ClickHouse"
wait_for_service localhost 8463 "Timeplus"  # Assuming Timeplus is already running

echo "⏳ Waiting for services to fully initialize..."
sleep 10

## prepare env

echo "📝 Creating Kafka topic..."
docker exec e2e_kafka kafka-topics \
    --create \
    --topic e2e_events \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists


## Create ClickHouse table
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



## Create Timeplus database
echo "🏗️ Creating Timeplus database..."
docker exec e2e_timeplus proton-client \
    -u proton \
    --password proton@t+ \
    --query "CREATE DATABASE IF NOT EXISTS e2e_test"
echo "✅ Created e2e_test database in Timeplus"

## create timeplus table(shall replaced by dbt?)

```
 python3 setup_timeplus.py                                 
🔧 Setting up Timeplus objects...
   Creating database e2e_test...
   Cleaning up existing objects...
   Creating Kafka external stream...
   Creating aggregation stream...
   Creating aggregation materialized view...
   Creating ClickHouse external table...
   Creating ClickHouse sink materialized view...
   Creating analytics view...
✅ Timeplus objects created successfully!

📋 Created objects:
   Streams: clickhouse_results
event_aggregations
event_aggregations_mv
kafka_events_stream
to_clickhouse_mv
user_activity_summary
```

## ingestion testing data


```
source ~/miniconda3/bin/activate py310test  && python3 generate_data.py                                      
📤 Starting event generation...
   Rate: 10 events/second
   Duration: 60 seconds
   Batch size: 100 events

   Generated 600 events...
✅ Generated 600 events in 60 seconds
(py310test) ➜  kafka-timeplus-clickhouse 


```

## query from clickhouse

```
source ~/miniconda3/bin/activate py310test  &&  python3 verify.py 
🔬 E2E Pipeline Verification
==================================================
🔍 Checking Kafka...
   ✅ Kafka topic has events (sampled 0 recent events)

🔍 Checking Timeplus...
   ✅ Connected to Timeplus
   Available streams: <timeplus_connect.driver.summary.QuerySummary object at 0x75681a3aff40>
   Aggregation stats: ['580', '2025-10-20 22:08:40.000', '2025-10-20 22:09:40.000']
   Top 5 users by amount: ['user_0035', '6', '1560.22\nuser_0085', '11', '1476.52\nuser_0027', '8', '1434.68\nuser_0095', '8', '1358\nuser_0007', '8', '1233.06']

🔍 Checking ClickHouse...
   ✅ ClickHouse has data:
      Total records: 580
      Date range: 2025-10-20 22:08:40 to 2025-10-20 22:09:40
      Unique users: 100
      Event types: 6

   Recent aggregations:
      (datetime.datetime(2025, 10, 20, 22, 9, 30), 'user_0099', 'checkout', 'us-east', 1, 254.04)
      (datetime.datetime(2025, 10, 20, 22, 9, 30), 'user_0097', 'purchase', 'us-east', 1, 67.62)
      (datetime.datetime(2025, 10, 20, 22, 9, 30), 'user_0095', 'add_to_cart', 'us-west', 1, 133.71)
      (datetime.datetime(2025, 10, 20, 22, 9, 30), 'user_0093', 'checkout', 'us-west', 1, 218.83)
      (datetime.datetime(2025, 10, 20, 22, 9, 30), 'user_0093', 'checkout', 'ap-south', 1, 48.59)

==================================================
📊 Summary:
   Kafka: ✅ OK
   Timeplus: ✅ OK
   ClickHouse: ✅ OK

🎉 Pipeline is working correctly!
(py310test) ➜  kafka-timeplus-clickhouse 
```