{{ config(
    materialized='materialized_view',
    alias='event_aggregations_mv',
    into='event_aggregations',
    pre_hook=[
      "drop view if exists event_aggregations_mv",
      "create stream if not exists event_aggregations (win_start datetime64(3), win_end datetime64(3), user_id string, event_type string, region string, event_count uint64, total_amount float64, avg_amount float64, min_amount float64, max_amount float64, _tp_time datetime64(3) default now64(3) codec(DoubleDelta, LZ4))",
      "drop stream if exists kafka_events_stream",
      "create external stream kafka_events_stream (event_id string, user_id string, event_type string, amount float64, timestamp datetime64(3), metadata__source string, metadata__region string) settings type='kafka', brokers='{{ env_var('KAFKA_BROKERS', 'kafka:29092') }}', topic='{{ env_var('KAFKA_TOPIC', 'e2e_events') }}', data_format='JSONEachRow'"
    ]
) }}

select
  window_start as win_start,
  window_end as win_end,
  user_id,
  event_type,
  metadata__region as region,
  count() as event_count,
  sum(amount) as total_amount,
  avg(amount) as avg_amount,
  min(amount) as min_amount,
  max(amount) as max_amount,
  now64(3) as _tp_time
from tumble(kafka_events_stream, timestamp, interval 10 second)
group by window_start, window_end, user_id, event_type, metadata__region

