{{ config(
    materialized='materialized_view',
    alias='to_clickhouse_mv',
    into='clickhouse_results',
    pre_hook=[
      "drop view if exists to_clickhouse_mv",
      "drop stream if exists clickhouse_results",
      "create external table clickhouse_results settings type='clickhouse', address='{{ env_var('CH_ADDRESS', 'clickhouse:9000') }}', database='{{ env_var('CH_DATABASE', 'default') }}', table='{{ env_var('CH_TABLE', 'e2e_aggregation_results') }}'"
    ]
) }}

select
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
  now64(3) as inserted_at
from event_aggregations
where event_count > 0

