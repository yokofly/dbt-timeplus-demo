#!/usr/bin/env python3
"""
Setup Timeplus-specific objects (external streams, external tables) for E2E test
Uses docker exec to run DDL commands as they require proton user privileges
"""

import subprocess
import sys

def run_sql(sql, database='default'):
    """Run SQL command via docker exec with proton user"""
    cmd = [
        'docker', 'exec', 'e2e_timeplus',
        'proton-client',
        '-u', 'proton',
        '--password', 'proton@t+',
        '--database', database,
        '--query', sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"SQL failed: {result.stderr}")
    return result.stdout

def main():
    print("🔧 Setting up Timeplus objects...")

    try:
        # Create database
        print("   Creating database e2e_test...")
        run_sql("CREATE DATABASE IF NOT EXISTS e2e_test")

        # Drop existing objects for clean state (in reverse dependency order)
        print("   Cleaning up existing objects...")
        # Drop views first (they depend on streams)
        run_sql("DROP VIEW IF EXISTS user_activity_summary", "e2e_test")
        run_sql("DROP VIEW IF EXISTS to_clickhouse_mv", "e2e_test")
        run_sql("DROP VIEW IF EXISTS event_aggregations_mv", "e2e_test")
        # Then drop external tables/streams
        run_sql("DROP STREAM IF EXISTS clickhouse_results", "e2e_test")
        # Then drop regular streams
        run_sql("DROP STREAM IF EXISTS event_aggregations", "e2e_test")
        run_sql("DROP STREAM IF EXISTS kafka_events_stream", "e2e_test")

        # 1. Create Kafka external stream
        print("   Creating Kafka external stream...")
        run_sql("""
            CREATE EXTERNAL STREAM IF NOT EXISTS kafka_events_stream
            (
                event_id string,
                user_id string,
                event_type string,
                amount float64,
                timestamp datetime64(3),
                metadata__source string,
                metadata__region string
            )
            SETTINGS
                type = 'kafka',
                brokers = 'kafka:29092',
                topic = 'e2e_events',
                data_format = 'JSONEachRow'
        """, "e2e_test")

        # 2. Create aggregation stream
        print("   Creating aggregation stream...")
        run_sql("""
            CREATE STREAM IF NOT EXISTS event_aggregations
            (
                win_start datetime64(3),
                win_end datetime64(3),
                user_id string,
                event_type string,
                region string,
                event_count uint64,
                total_amount float64,
                avg_amount float64,
                min_amount float64,
                max_amount float64,
                _tp_time datetime64(3) DEFAULT now64(3) CODEC(DoubleDelta, LZ4)
            )
        """, "e2e_test")

        # 3. Create materialized view for aggregation
        print("   Creating aggregation materialized view...")
        run_sql("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS event_aggregations_mv
            INTO event_aggregations AS
            SELECT
                window_start AS win_start,
                window_end AS win_end,
                user_id,
                event_type,
                metadata__region AS region,
                count() AS event_count,
                sum(amount) AS total_amount,
                avg(amount) AS avg_amount,
                min(amount) AS min_amount,
                max(amount) AS max_amount,
                now64(3) AS _tp_time
            FROM tumble(kafka_events_stream, timestamp, interval 10 second)
            GROUP BY
                window_start,
                window_end,
                user_id,
                event_type,
                metadata__region
        """, "e2e_test")

        # 4. Create ClickHouse external table
        print("   Creating ClickHouse external table...")
        run_sql("""
            CREATE EXTERNAL TABLE IF NOT EXISTS clickhouse_results
            SETTINGS
                type = 'clickhouse',
                address = 'clickhouse:9000',
                database = 'default',
                table = 'e2e_aggregation_results'
        """, "e2e_test")

        # 5. Create materialized view to ClickHouse
        print("   Creating ClickHouse sink materialized view...")
        run_sql("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS to_clickhouse_mv
            INTO clickhouse_results AS
            SELECT
                win_start,
                win_end,
                user_id,
                event_type,
                region,
                event_count,
                total_amount,
                avg_amount,
                min_amount,
                max_amount,
                now64(3) AS inserted_at
            FROM event_aggregations
            WHERE event_count > 0
        """, "e2e_test")

        # 6. Create analytics view
        print("   Creating analytics view...")
        run_sql("""
            CREATE VIEW IF NOT EXISTS user_activity_summary AS
            SELECT
                user_id,
                count(DISTINCT event_type) AS unique_event_types,
                sum(event_count) AS total_events,
                sum(total_amount) AS total_spent,
                avg(avg_amount) AS avg_transaction_amount,
                max(max_amount) AS highest_transaction,
                count(DISTINCT region) AS active_regions,
                max(win_end) AS last_activity
            FROM event_aggregations
            WHERE win_end >= now() - interval 1 hour
            GROUP BY user_id
            ORDER BY total_spent DESC
        """, "e2e_test")

        print("✅ Timeplus objects created successfully!")

        # List created objects
        print("\n📋 Created objects:")
        streams = run_sql("SHOW STREAMS", "e2e_test")
        print(f"   Streams: {streams}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())