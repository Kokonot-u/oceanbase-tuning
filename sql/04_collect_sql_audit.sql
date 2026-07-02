SELECT
  request_time,
  query_sql,
  elapsed_time,
  execute_time,
  queue_time,
  return_rows,
  affected_rows,
  ret_code
FROM oceanbase.GV$OB_SQL_AUDIT
ORDER BY request_time DESC
LIMIT 100;
