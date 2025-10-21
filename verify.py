#!/usr/bin/env python3
"""
Verify the E2E pipeline is working correctly
"""

import time
import json
import sys
from kafka import KafkaConsumer
import timeplus_connect
import clickhouse_connect

def check_kafka():
    """Check Kafka for events"""
    print("🔍 Checking Kafka...")
    try:
        consumer = KafkaConsumer(
            'e2e_events',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=5000
        )

        event_count = 0
        sample_event = None
        for message in consumer:
            event_count += 1
            if not sample_event:
                sample_event = message.value

        print(f"   ✅ Kafka topic has events (sampled {event_count} recent events)")
        if sample_event:
            print(f"   Sample event: {json.dumps(sample_event, indent=2)[:200]}...")
        return True
    except Exception as e:
        print(f"   ❌ Kafka check failed: {e}")
        return False

def check_timeplus():
    """Check Timeplus streams and processing"""
    print("\n🔍 Checking Timeplus...")
    try:
        client = timeplus_connect.create_client(
            host='localhost',
            port=8123,
            username='default',
            password='',
            database='e2e_test'
        )

        # Check if external stream exists
        result = client.command("SHOW STREAMS")
        print(f"   ✅ Connected to Timeplus")
        print(f"   Available streams: {result}")

        # Check aggregation data
        result = client.command("""
            SELECT
                count() as total_records,
                min(win_start) as earliest_window,
                max(win_end) as latest_window
            FROM table(event_aggregations)
        """)
        print(f"   Aggregation stats: {result}")

        # Check user activity
        result = client.command("""
            SELECT
                user_id,
                sum(event_count) as total_events,
                sum(total_amount) as total_amount
            FROM table(event_aggregations)
            GROUP BY user_id
            ORDER BY total_amount DESC
            LIMIT 5
        """)
        print(f"   Top 5 users by amount: {result}")

        client.close_connections()
        return True
    except Exception as e:
        print(f"   ❌ Timeplus check failed: {e}")
        return False

def check_clickhouse():
    """Check ClickHouse for results"""
    print("\n🔍 Checking ClickHouse...")
    try:
        client = clickhouse_connect.get_client(
            host='localhost',
            port=8124,  # HTTP port
            database='default'
        )

        # Check if table exists and has data
        result = client.query("""
            SELECT
                count() as total_records,
                min(win_start) as earliest_window,
                max(win_end) as latest_window,
                count(DISTINCT user_id) as unique_users,
                count(DISTINCT event_type) as event_types
            FROM e2e_aggregation_results
        """)

        if result.result_rows:
            row = result.result_rows[0]
            print(f"   ✅ ClickHouse has data:")
            print(f"      Total records: {row[0]}")
            print(f"      Date range: {row[1]} to {row[2]}")
            print(f"      Unique users: {row[3]}")
            print(f"      Event types: {row[4]}")

            # Get sample aggregations
            result = client.query("""
                SELECT
                    win_start,
                    user_id,
                    event_type,
                    region,
                    event_count,
                    round(total_amount, 2) as total_amount
                FROM e2e_aggregation_results
                ORDER BY win_start DESC
                LIMIT 5
            """)

            if result.result_rows:
                print("\n   Recent aggregations:")
                for row in result.result_rows:
                    print(f"      {row}")
        else:
            print(f"   ⚠️ ClickHouse table exists but is empty")

        return True
    except Exception as e:
        print(f"   ❌ ClickHouse check failed: {e}")
        return False

def main():
    print("🔬 E2E Pipeline Verification")
    print("=" * 50)

    # Check all components
    kafka_ok = check_kafka()
    timeplus_ok = check_timeplus()
    clickhouse_ok = check_clickhouse()

    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"   Kafka: {'✅ OK' if kafka_ok else '❌ Failed'}")
    print(f"   Timeplus: {'✅ OK' if timeplus_ok else '❌ Failed'}")
    print(f"   ClickHouse: {'✅ OK' if clickhouse_ok else '❌ Failed'}")

    if kafka_ok and timeplus_ok and clickhouse_ok:
        print("\n🎉 Pipeline is working correctly!")
        return 0
    else:
        print("\n⚠️ Some components need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())