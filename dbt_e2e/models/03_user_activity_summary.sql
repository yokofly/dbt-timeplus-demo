{{ config(materialized='view', alias='user_activity_summary') }}

select
  user_id,
  count(distinct event_type) as unique_event_types,
  sum(event_count) as total_events,
  sum(total_amount) as total_spent,
  avg(avg_amount) as avg_transaction_amount,
  max(max_amount) as highest_transaction,
  count(distinct region) as active_regions,
  max(win_end) as last_activity
from event_aggregations
where win_end >= now() - interval 1 hour
group by user_id
order by total_spent desc

